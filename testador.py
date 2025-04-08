from dotenv import load_dotenv
load_dotenv()
import os
import ccxt

def testar_binance_futuros():
    try:
        binance = ccxt.binance({
            'apiKey': os.getenv("BINANCE_API_KEY"),
            'secret': os.getenv("BINANCE_API_SECRET"),
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })

        balance = binance.fetch_balance()
        usdt = balance['total']['USDT']
        print(f"✅ Conexão OK! Saldo em USDT (Futuros): {usdt}")
    except Exception as e:
        print(f"❌ Erro ao conectar com a Binance Futures: {e}")

if __name__ == "__main__":
    testar_binance_futuros()
from telegram_utils import notificar_telegram

if __name__ == "__main__":
    notificar_telegram("✅ Teste do novo bot: integração funcionando!")
