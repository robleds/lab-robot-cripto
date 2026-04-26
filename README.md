# Robo-Cripto 🤖📈

Bot de trading automatizado para criptomoedas na Binance, usando estratégia de cruzamento de médias móveis (Moving Average Crossover).

## Como funciona

O bot monitora o preço de uma criptomoeda em intervalos regulares e executa ordens de compra/venda com base no cruzamento de duas médias móveis:

- **Média rápida (curta):** detecta mudanças de tendência recentes
- **Média devagar (longa):** confirma a direção da tendência

| Sinal | Condição | Ação |
|-------|----------|------|
| Compra | Média rápida cruza **acima** da média devagar | Abre posição |
| Venda  | Média rápida cruza **abaixo** da média devagar | Fecha posição |

## Bots disponíveis

| Arquivo | Par | Intervalo | MA Rápida | MA Devagar |
|---------|-----|-----------|-----------|------------|
| `robo_crypto_btc.py` | BTC/BRL | 5 minutos | 7 | 40 |
| `robo_crypto_eth.py` | ETH/BRL | configurável | configurável | configurável |
| `robo_crypto_sol.py` | SOL/BRL | configurável | configurável | configurável |
| `robo_crypto_gala.py` | GALA/BRL | 1 hora | 7 | 20 |
| `robo_crypto_lista.py` | LISTA/BRL | 1 hora | 7 | 20 |

## Pré-requisitos

- Python 3.8+
- Conta na [Binance](https://www.binance.com) com API habilitada
- Chave de API com permissão de **leitura** e **trading** (nunca habilite saque!)

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/Robo-Cripto.git
cd Robo-Cripto

# 2. Crie e ative um ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite o arquivo .env com suas chaves reais da Binance
```

## Configuração

Edite o arquivo `.env` com suas chaves da Binance:

```
KEY_BINANCE=sua_api_key_aqui
SECRET_BINANCE=seu_secret_key_aqui
```

> ⚠️ **NUNCA** commite o arquivo `.env` com chaves reais. Ele já está no `.gitignore`.

## Uso

```bash
# Carregar variáveis de ambiente e executar o bot desejado
source .env  # Linux/Mac
# ou use python-dotenv (já incluído no requirements.txt)

python robo_crypto_btc.py    # Bot BTC
python robo_crypto_lista.py  # Bot LISTA (mais completo, com logging)
```

Para rodar em background (servidor Linux):

```bash
nohup python robo_crypto_lista.py > bot.log 2>&1 &
```

## Segurança

- As chaves da API são carregadas via variáveis de ambiente (`os.getenv()`), nunca hardcoded
- Crie chaves de API com permissão **apenas de trading** (sem saque)
- Restrinja o IP da chave de API quando possível
- Nunca compartilhe seu arquivo `.env`

## Aviso de risco

> **Este projeto é educacional.** Trading de criptomoedas envolve risco significativo de perda financeira. Use por sua conta e risco. Teste sempre com valores pequenos antes de operar com volumes maiores.

## Licença

MIT
