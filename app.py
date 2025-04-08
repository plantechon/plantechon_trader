from flask import Flask, request
import os
import threading
import time
import requests

from dotenv import load_dotenv
load_dotenv()

from bot_logic import process_signal, iniciar_monitoramento, estado
from telegram_utils import notificar_telegram
from status_scheduler import iniciar_agendador

app = Flask(__name__)

# 🌐 Webhook do TradingView
@app.route("/webhook", methods=["POST"])
def webhook():
    print("🔥 SINAL ACIONADO! (SEGUNDO BOT)", flush=True)
    if not estado["ativado"]:
        notificar_telegram("⚠️ Sinal recebido, mas o bot está DESLIGADO.")
        return {"status": "desligado", "mensagem": "Bot desligado"}
    
    data = request.json
    result = process_signal(data)
    return result

# ✅ Inicializa monitoramento e agendador
iniciar_monitoramento()
iniciar_agendador()

# 📡 Bot de comandos do Telegram
def verificar_comandos_telegram():
    print("🤖 Monitorando comandos do Telegram...")

    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    last_update_id = None

    while True:
        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates"
            if last_update_id:
                url += f"?offset={last_update_id + 1}"

            response = requests.get(url)
            updates = response.json().get("result", [])

            for update in updates:
                last_update_id = update["update_id"]
                message = update.get("message", {})
                text = message.get("text", "").lower()
                user = message.get("from", {}).get("first_name", "Usuário")

                if "/ligar" in text:
                    estado["ativado"] = True
                    notificar_telegram(f"✅ Bot ativado por {user}")
                elif "/desligar" in text:
                    estado["ativado"] = False
                    notificar_telegram(f"⛔ Bot desligado por {user}")
                elif "/status" in text:
                    status = "🟢 LIGADO" if estado["ativado"] else "🔴 DESLIGADO"
                    operando = f"⏳ Operando {estado['par']}" if estado["em_operacao"] else "📭 Sem operação no momento"
                    notificar_telegram(f"📊 Status do Bot:\nStatus: {status}\n{operando}")
        except Exception as e:
            print(f"Erro ao verificar comandos: {e}")
        
        time.sleep(5)  # Verifica a cada 5 segundos

# ▶️ Inicia o monitoramento de comandos em thread separada
threading.Thread(target=verificar_comandos_telegram).start()

# 🚀 Inicia servidor Flask
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
