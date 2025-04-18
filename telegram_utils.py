import os
import requests
import random

# 🔐 Credenciais do .env
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 📤 Envia mensagem e mostra no terminal
def notificar_telegram(mensagem: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram não configurado corretamente.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem
    }

    try:
        response = requests.post(url, json=payload)
        print("📤 Mensagem enviada ao Telegram:")
        print("───────────────────────────────")
        print(mensagem)
        print("───────────────────────────────")
        print(f"📨 HTTP {response.status_code} | Resposta: {response.text}")
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem pro Telegram: {e}")

# 💬 Mensagens aleatórias quando inativo
mensagens_parado = [
    "📡 Nenhuma operação ativa no momento. Aguardando sinal...",
    "👀 Monitorando o mercado... sem entrada por enquanto.",
    "📈 Bot Plantechon ligado, sem operações abertas.",
    "🟡 Sem sinais ativos. Analisando H1 e H4.",
    "⏳ Esperando oportunidade confirmada para operar."
]

def mensagem_parado_aleatoria():
    return random.choice(mensagens_parado)
