import os
import time
import logging
import math
import pandas as pd
from binance.client import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException
from decimal import Decimal, ROUND_DOWN

# Configuração do logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuração da API
api_key = os.getenv("KEY_BINANCE")
secret_key = os.getenv("SECRET_BINANCE")

try:
    cliente_binance = Client(api_key, secret_key)
    logging.info("Cliente Binance configurado com sucesso.")
except Exception as e:
    logging.error(f"Erro ao configurar cliente Binance: {e}")
    raise

# Configurações gerais
MA_WINDOW_IN = 7  # Média móvel curta para sinais rápidos
MA_WINDOW_OUT = 20  # Média móvel mais longa para confirmar tendências
CANDLE_LIMIT = 150  # Capturar histórico para as médias móveis
CODIGO_OPERADO = "LISTABRL"
ATIVO_OPERADO = "LISTA"
INTERVALO = Client.KLINE_INTERVAL_1HOUR


# Função para transformar um Kline_Interval em segundos
def intervalo_para_segundos(intervalo):
    """
    Converte o valor do INTERVALO (KLINE_INTERVAL) para o número de segundos.
    
    Parâmetros:
        intervalo (str): O intervalo da Binance, ex.: "5m", "1h".
    
    Retorna:
        int: Número de segundos correspondente ao intervalo.
    """
    if intervalo.endswith('m'):  # Minutos
        return int(intervalo[:-1]) * 60
    elif intervalo.endswith('h'):  # Horas
        return int(intervalo[:-1]) * 60 * 60
    elif intervalo.endswith('d'):  # Dias
        return int(intervalo[:-1]) * 24 * 60 * 60
    elif intervalo.endswith('w'):  # Semanas
        return int(intervalo[:-1]) * 7 * 24 * 60 * 60
    else:
        raise ValueError(f"Intervalo desconhecido: {intervalo}")
    
    
# Função para carregar informações do símbolo
def carregar_informacoes_simbolo(codigo):
    try:
        symbol_info = cliente_binance.get_symbol_info(codigo)
        if not symbol_info or 'filters' not in symbol_info:
            raise ValueError("Informações do símbolo não disponíveis ou inválidas.")

        filters = symbol_info['filters']
        lot_size_filter = next(f for f in filters if f['filterType'] == 'LOT_SIZE')
        price_filter = next(f for f in filters if f['filterType'] == 'PRICE_FILTER')
        min_notional_filter = next(f for f in filters if f['filterType'] == 'NOTIONAL')

        min_qty = float(lot_size_filter['minQty'])
        step_size = float(lot_size_filter['stepSize'])
        tick_size = float(price_filter['tickSize'])
        min_notional = float(min_notional_filter['minNotional'])

        logging.info(f"Informações do símbolo carregadas: {codigo}")
        return min_qty, step_size, tick_size, min_notional
    except Exception as e:
        logging.error(f"Erro ao carregar informações do símbolo: {e}")
        raise



# Função para calcular o valor de compra
def calcular_valor_compra(saldo_brl, preco_atual, step_size, min_notional):
    saldo_brl_dec = Decimal(str(saldo_brl)) / Decimal('4')  # Usar 25% do saldo em BRL
    step_size_dec = Decimal(str(step_size))
    preco_atual_dec = Decimal(str(preco_atual))
    min_notional_dec = Decimal(str(min_notional))
    
    # Calcular a quantidade bruta a ser comprada
    quantidade_bruta = saldo_brl_dec / preco_atual_dec
    
    # Ajustar a quantidade para o step_size permitido
    quantidade_compra = (quantidade_bruta / step_size_dec).quantize(Decimal('1'), rounding=ROUND_DOWN) * step_size_dec
    
    # Verificar se o valor total da ordem atende ao min_notional
    valor_total = quantidade_compra * preco_atual_dec
    if valor_total < min_notional_dec:
        return 0.0  # Retorna 0.0 se não atender ao valor mínimo permitido
    
    return float(quantidade_compra)



# Função para calcular o valor de venda
def calcular_valor_venda(saldo_ativo, step_size, min_notional, preco_atual):
    saldo_ativo_dec = Decimal(str(saldo_ativo))
    step_size_dec = Decimal(str(step_size))
    preco_atual_dec = Decimal(str(preco_atual))
    min_notional_dec = Decimal(str(min_notional))
    
    # Ajustar a quantidade com base no step_size
    quantidade_venda = (saldo_ativo_dec / step_size_dec).quantize(Decimal('1'), rounding=ROUND_DOWN) * step_size_dec
    
    # Verificar se o valor total atende ao min_notional
    valor_total = quantidade_venda * preco_atual_dec
    if valor_total < min_notional_dec:
        return 0.0  # Retorna 0.0 se não atender ao valor mínimo permitido
    
    return float(quantidade_venda)



# Função para executar ordens de mercado
def executar_ordem(codigo, lado, quantidade):
    try:
        ordem = cliente_binance.create_order(
            symbol=codigo,
            side=lado,
            type=ORDER_TYPE_MARKET,
            quantity=quantidade
        )
        logging.info(f"Ordem de {lado} executada: {ordem}")
        return ordem
    except BinanceAPIException as e:
        logging.error(f"Erro ao executar ordem: {e}")
        return None



# Função para carregar dados históricos
def pegando_dados(codigo, intervalo):
    try:
        candles = cliente_binance.get_klines(symbol=codigo, interval=intervalo, limit=CANDLE_LIMIT)
        precos = pd.DataFrame(candles)
        precos.columns = ["tempo_abertura", "abertura", "maxima", "minima", "fechamento", "volume", "tempo_fechamento",
                          "moedas_negociadas", "numero_trades", "volume_ativo_base_compra", "volume_ativo_cotação", "-"]
        precos = precos[["fechamento", "tempo_fechamento"]]
        precos["fechamento"] = pd.to_numeric(precos["fechamento"])
        precos["tempo_fechamento"] = pd.to_datetime(precos["tempo_fechamento"], unit="ms").dt.tz_localize("UTC")
        precos["tempo_fechamento"] = precos["tempo_fechamento"].dt.tz_convert("America/Sao_Paulo")
        logging.info(f"Dados históricos carregados para {codigo}")
        # logging.info(f"Preços: {precos}")
        return precos
    except Exception as e:
        logging.error(f"Erro ao carregar dados históricos: {e}")
        raise



# Estratégia de trade
def estrategia_trade(dados, codigo_ativo, ativo_operado, posicao, step_size, min_notional, tick_size):
    try:
        dados["media_rapida"] = dados["fechamento"].rolling(window=MA_WINDOW_IN).mean()
        dados["media_devagar"] = dados["fechamento"].rolling(window=MA_WINDOW_OUT).mean()

        ultima_media_rapida = dados["media_rapida"].iloc[-1]
        ultima_media_devagar = dados["media_devagar"].iloc[-1]

        logging.info(f"Média rápida: {ultima_media_rapida} | Média devagar: {ultima_media_devagar} | Posicionado? {posicao}")

        saldo_brl = float(next(item['free'] for item in cliente_binance.get_account()["balances"] if item['asset'] == "BRL"))
        saldo_ativo = float(next((item['free'] for item in cliente_binance.get_account()["balances"] if item['asset'] == ativo_operado), 0.0))
        preco_atual = float(cliente_binance.get_symbol_ticker(symbol=codigo_ativo).get("price", 0.0))
        logging.info(f"Saldo em BRL: {saldo_brl}")
        logging.info(f"Saldo de {codigo_ativo}: {saldo_ativo} (Preço atual: {preco_atual})")

        if ultima_media_rapida > ultima_media_devagar and not posicao:
            quantidade_compra = calcular_valor_compra(saldo_brl, preco_atual, step_size, min_notional)
            if quantidade_compra > 0:
                logging.info(f"Iniciando execução de ordem de compra: {quantidade_compra}")
                executar_ordem(codigo_ativo, SIDE_BUY, quantidade_compra)
                posicao = True

        elif ultima_media_rapida < ultima_media_devagar and posicao:
            quantidade_venda = calcular_valor_venda(saldo_ativo, step_size, min_notional, preco_atual)
            if quantidade_venda > 0:
                logging.info(f"Iniciando execução de ordem de venda: {quantidade_venda}")
                executar_ordem(codigo_ativo, SIDE_SELL, quantidade_venda)
                posicao = False

        return posicao

    except Exception as e:
        logging.error(f"Erro ao executar estratégia: {e}")
        return posicao



# Loop principal
if __name__ == "__main__":
    min_qty, step_size, tick_size, min_notional = carregar_informacoes_simbolo(CODIGO_OPERADO)
    posicao_atual = False

    while True:
        try:
            dados_atualizados = pegando_dados(codigo=CODIGO_OPERADO, intervalo=INTERVALO)
            posicao_atual = estrategia_trade(
                dados=dados_atualizados,
                codigo_ativo=CODIGO_OPERADO,
                ativo_operado=ATIVO_OPERADO,
                posicao=posicao_atual,
                step_size=step_size,
                min_notional=min_notional,
                tick_size=tick_size
            )
            time.sleep(intervalo_para_segundos(INTERVALO))
        except KeyboardInterrupt:
            logging.info("Execução interrompida pelo usuário.")
            break
        except Exception as e:
            logging.error(f"Erro no loop principal: {e}")
