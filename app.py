from flask import Flask, request, jsonify
from bot_logic import process_signal, iniciar_monitoramento
from telegram_utils import notificar_telegram
from status_scheduler import iniciar_agendador

app = Flask(__name__)

# Inicia os schedulers
iniciar_agendador()
iniciar_monitoramento()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    timeframe = data.get("timeframe")
    if timeframe not in ["60", "240"]:
        return jsonify({"status": "ignorado", "motivo": "Timeframe nao permitido"}), 200

    try:
        resultado = process_signal(data)
        return jsonify(resultado)
    except Exception as e:
        notificar_telegram(f"⚠️ Erro no bot: {str(e)}")
        return jsonify({"erro": str(e)}), 400

# ESSA PARTE AQUI É FUNDAMENTAL
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
