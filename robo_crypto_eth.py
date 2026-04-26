import pandas as pd
import os
import time
import logging
from binance.client import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException, BinanceRequestException
from decimal import Decimal, ROUND_DOWN

# Configuração do logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Setup API
api_key = os.getenv("KEY_BINANCE")
secret_key = os.getenv("SECRET_BINANCE")
try:
    cliente_binance = Client(api_key, secret_key)
    logging.info("Cliente Binance configurado com sucesso.")
except Exception as e:
    logging.error(f"Erro ao configurar cliente Binance: {e}")
    raise

# Setup da moeda
CODIGO_OPERADO = "ETHBRL"
ATIVO_OPERADO = "ETH"
PERIODO_CANDLE = Client.KLINE_INTERVAL_5MINUTE
QUANTIDADE = 0.0021

# Função para carregar informações do símbolo
def carregar_informacoes_simbolo(codigo):
    try:
        symbol_info = cliente_binance.get_symbol_info(codigo)
        lot_size_filter = next(f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE')
        min_qty = float(lot_size_filter['minQty'])
        max_qty = float(lot_size_filter['maxQty'])
        step_size = float(lot_size_filter['stepSize'])
        logging.info(f"Informações do símbolo carregadas: {codigo}")
        return min_qty, max_qty, step_size
    except BinanceAPIException as e:
        logging.error(f"Erro na API da Binance ao carregar informações do símbolo: {e}")
        raise
    except Exception as e:
        logging.error(f"Erro inesperado ao carregar informações do símbolo: {e}")
        raise

# Função para pegar dados históricos
def pegando_dados(codigo, intervalo):
    try:
        candles = cliente_binance.get_klines(symbol=codigo, interval=intervalo, limit=1000)
        precos = pd.DataFrame(candles)
        precos.columns = ["tempo_abertura", "abertura", "maxima", "minima", "fechamento", "volume", "tempo_fechamento",
                          "moedas_negociadas", "numero_trades", "volume_ativo_base_compra", "volume_ativo_cotação", "-"]
        precos = precos[["fechamento", "tempo_fechamento"]]
        precos["fechamento"] = pd.to_numeric(precos["fechamento"])
        precos["tempo_fechamento"] = pd.to_datetime(precos["tempo_fechamento"], unit="ms").dt.tz_localize("UTC")
        precos["tempo_fechamento"] = precos["tempo_fechamento"].dt.tz_convert("America/Sao_Paulo")
        logging.info(f"Dados históricos carregados para {codigo}")
        return precos
    except BinanceAPIException as e:
        logging.error(f"Erro na API da Binance ao carregar dados históricos: {e}")
        raise
    except Exception as e:
        logging.error(f"Erro inesperado ao carregar dados históricos: {e}")
        raise

# Função para executar estratégia de trade
def estrategia_trade(dados, codigo_ativo, ativo_operado, quantidade, posicao):
    try:
        dados["media_rapida"] = dados["fechamento"].rolling(window=7).mean()
        dados["media_devagar"] = dados["fechamento"].rolling(window=40).mean()

        ultima_media_rapida = dados["media_rapida"].iloc[-1]
        ultima_media_devagar = dados["media_devagar"].iloc[-1]

        logging.info(f"Média rápida: {ultima_media_rapida:.2f} | Média devagar: {ultima_media_devagar:.2f} | Posicionado? {posicao}")

        conta = cliente_binance.get_account()
        quantidade_atual = 0.0

        for ativo in conta["balances"]:
            if float(ativo["free"]) > 0:
                logging.info(f"Disponível na Carteira: {ativo["asset"]}: {ativo["free"]}")

        for ativo in conta["balances"]:
            if ativo["asset"] == ativo_operado:
                quantidade_atual = float(ativo["free"])
                logging.info(f"Quantidade atual de {ativo_operado}: {quantidade_atual}")
                break

        if ultima_media_rapida > ultima_media_devagar and not posicao:
            logging.info(f"Iniciando execução de ordem de compra.")
            order = cliente_binance.create_order(
                symbol=codigo_ativo,
                side=SIDE_BUY,
                type=ORDER_TYPE_MARKET,
                quantity=quantidade
            )
            logging.info(f"Ordem de compra executada: {order}")
            posicao = True

        elif ultima_media_rapida < ultima_media_devagar and posicao:
            # quantidade_venda = float(quantidade_atual) #max(min_qty, float(quantidade_atual))
            quantidade_venda = Decimal(quantidade_atual).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)
            logging.info(f"Iniciando execução de ordem de venda: {quantidade_venda}")
            order = cliente_binance.create_order(
                symbol=codigo_ativo,
                side=SIDE_SELL,
                type=ORDER_TYPE_MARKET,
                quantity=quantidade_venda
            )
            logging.info(f"Ordem de venda executada: {order}")
            posicao = False

        return posicao

    except BinanceAPIException as e:
        logging.error(f"Erro na API da Binance ao executar estratégia de trade: {e}")
    except Exception as e:
        logging.error(f"Erro inesperado ao executar estratégia de trade: {e}")
        return posicao

# Loop principal
if __name__ == "__main__":
    min_qty, max_qty, step_size = carregar_informacoes_simbolo(CODIGO_OPERADO)
    posicao_atual = False

    while True:
        try:
            dados_atualizados = pegando_dados(codigo=CODIGO_OPERADO, intervalo=PERIODO_CANDLE)
            posicao_atual = estrategia_trade(dados=dados_atualizados, codigo_ativo=CODIGO_OPERADO,
                                             ativo_operado=ATIVO_OPERADO, quantidade=QUANTIDADE, posicao=posicao_atual)
            time.sleep(5 * 60)
        except KeyboardInterrupt:
            logging.info("Execução interrompida pelo usuário.")
            break
        except Exception as e:
            logging.error(f"Erro no loop principal: {e}")
