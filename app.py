from flask import Flask, request
from dotenv import load_dotenv
import os
import threading

from bot_logic import process_signal, iniciar_monitoramento, estado
from telegram_utils import notificar_telegram
from status_scheduler import iniciar_agendador

load_dotenv()

app = Flask(__name__)

# 🔘 Flag de ativação
bot_ativo = {"valor": True}

# ✅ Rota principal
@app.route('/')
def home():
    return "🚀 Bot Plantechon Trader Online!"

# 📩 Rota para sinais do TradingView
@app.route('/webhook', methods=['POST'])
def receber_sinal():
    if not bot_ativo["valor"]:
        notificar_telegram("⚠️ Sinal recebido mas o bot está desligado.")
        return {"status": "desligado", "mensagem": "Bot está inativo"}

    data = request.json
    resposta = process_signal(data)
    return resposta

# 🟢 Comando para ligar o bot
@app.route(f'/bot{os.getenv("BOT_TOKEN")}/ligar', methods=['GET', 'POST'])
def ligar():
    bot_ativo["valor"] = True
    notificar_telegram("✅ Bot ativado via comando.")
    return {"status": "ligado"}

# 🔴 Comando para desligar o bot
@app.route(f'/bot{os.getenv("BOT_TOKEN")}/desligar', methods=['GET', 'POST'])
def desligar():
    bot_ativo["valor"] = False
    notificar_telegram("🛑 Bot desativado via comando.")
    return {"status": "desligado"}

# 🚀 Inicializa agendador e monitoramento
if __name__ == "__main__":
    iniciar_agendador()
    threading.Thread(target=iniciar_monitoramento).start()
    app.run(host="0.0.0.0", port=10000)
