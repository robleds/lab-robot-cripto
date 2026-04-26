import pandas as pd
import os 
import time
from binance.client import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException

# SETUP API
api_key = os.getenv("KEY_BINANCE")
secret_key = os.getenv("SECRET_BINANCE")
cliente_binance = Client(api_key, secret_key)

# LISTAR TODAS AS MOEDAS
# exchange_info = cliente_binance.get_exchange_info()
# for s in exchange_info['symbols']:
#     print(s['symbol'])

# SETUP DA MOEDA
codigo_operado = "SOLBRL"
ativo_operado = "SOL"
periodo_candle = Client.KLINE_INTERVAL_5MINUTE
quantidade = 0.015

# DESCOBRIR O MINIMO A SER COMPRADO PELA MOEDA
symbol_info = cliente_binance.get_symbol_info(codigo_operado)
lot_size_filter = next(f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE')
min_qty = float(lot_size_filter['minQty'])
max_qty = float(lot_size_filter['maxQty'])
step_size = float(lot_size_filter['stepSize'])
# print(lot_size_filter, min_qty, max_qty, step_size)

# CARREGAM OS DADOS HISTÓRICOS DA MOEDA
def pegando_dados(codigo, intervalo):

    candles = cliente_binance.get_klines(symbol = codigo, interval = intervalo, limit = 1000)
    precos = pd.DataFrame(candles)
    precos.columns = ["tempo_abertura", "abertura", "maxima", "minima", "fechamento", "volume", "tempo_fechamento", "moedas_negociadas", "numero_trades", "volume_ativo_base_compra", "volume_ativo_cotação", "-"]
    precos = precos[["fechamento", "tempo_fechamento"]]
    precos["tempo_fechamento"] = pd.to_datetime(precos["tempo_fechamento"], unit="ms").dt.tz_localize("UTC")
    precos["tempo_fechamento"] = precos["tempo_fechamento"].dt.tz_convert("America/Sao_Paulo")

    return precos

# EXECUTA O TRADE
def estrategia_trade(dados, codigo_ativo, ativo_operado, quantidade, posicao):

    # DEFINIÇÃO DOS INDICADORES / REGRAS
    
    # média rápida de 7 dias
    dados["media_rapida"] = dados["fechamento"].rolling(window = 7).mean()

    # média lenta de 40 dias
    dados["media_devagar"] = dados["fechamento"].rolling(window = 40).mean()

    ultima_media_rapida = dados["media_rapida"].iloc[-1]
    ultima_media_devagar = dados["media_devagar"].iloc[-1]

    print(f"Última Média Rápida: {ultima_media_rapida} | Última Média Devagar: {ultima_media_devagar}")

    conta = cliente_binance.get_account()

    for ativo in conta["balances"]:

        # IMPRIMIR A LISTA DE ATIVOS
        # print(ativo)

        if float(ativo["free"]) > 0:
            print(f"Disponível na Carteira: {ativo["asset"]}: {ativo["free"]}")

        if ativo["asset"] == ativo_operado:

            quantidade_atual = float(ativo["free"])
            print(f"Quantidade atual: {quantidade_atual}")

    if ultima_media_rapida > ultima_media_devagar:

        if posicao == False:

            order = cliente_binance.create_order(
                symbol = codigo_ativo,
                side = SIDE_BUY,
                type = ORDER_TYPE_MARKET,
                quantity = quantidade
            )
            
            print("COMPROU ATIVO")

            posicao = True

    elif ultima_media_rapida < ultima_media_devagar:

        if posicao == True:

            order = cliente_binance.create_order(
                symbol = codigo_ativo,
                side = SIDE_SELL,
                type = ORDER_TYPE_MARKET,
                # Utilizar função para descobrir o minimo possível
                # quantity = quantidade_atual
                quantity = int(quantidade_atual * 1000)/1000
            )
            
            print("VENDEU ATIVO")

            posicao = False

    return posicao

posicao_atual = False

# LOOP DE EXECUÇÃO
while True:

    dados_atualizados = pegando_dados(codigo=codigo_operado, intervalo=periodo_candle)
    posicao_atual = estrategia_trade(dados_atualizados, codigo_ativo=codigo_operado, ativo_operado=ativo_operado, quantidade=quantidade, posicao=posicao_atual)
    time.sleep(5 * 60)

# order = cliente_binance.create_order(
#     symbol = codigo_operado,
#     side = SIDE_BUY,
#     type = ORDER_TYPE_MARKET,
#     quantity = quantidade
# )
# print(f"COMPROU ATIVO: {order}")
# dados_atualizados = pegando_dados(codigo=codigo_operado, intervalo=periodo_candle)
# posicao_atual = estrategia_trade(dados_atualizados, codigo_ativo=codigo_operado, ativo_operado=ativo_operado, quantidade=quantidade, posicao=posicao_atual)