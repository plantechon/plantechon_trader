from apscheduler.schedulers.background import BackgroundScheduler
from telegram_utils import notificar_telegram, mensagem_parado_aleatoria
from bot_logic import estado

def enviar_status():
    if estado["em_operacao"]:
        msg = f"⏳ Operando {estado['par']} no momento. Entrada: {estado['entrada']}"
    else:
        msg = mensagem_parado_aleatoria()
    notificar_telegram(msg)

def iniciar_agendador():
    scheduler = BackgroundScheduler()
    scheduler.add_job(enviar_status, 'interval', hours=1)
    scheduler.start()
    print("✅ Agendador de status iniciado")
