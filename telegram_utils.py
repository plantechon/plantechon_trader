import os
import requests
import random

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def notificar_telegram(mensagem: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram não configurado corretamente.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erro ao enviar mensagem pro Telegram: {e}")

mensagens_parado = [
    "📡 Nenhuma operação ativa no momento. Aguardando sinal...",
    "👀 Monitorando o mercado... sem entrada por enquanto.",
    "📈 Bot Plantechon ligado, sem operações abertas.",
    "🟡 Sem sinais ativos. Analisando H1 e H4.",
    "⏳ Esperando oportunidade confirmada para operar."
]

def mensagem_parado_aleatoria():
    return random.choice(mensagens_parado)
