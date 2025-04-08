from apscheduler.schedulers.background import BackgroundScheduler
import time
import ccxt
from telegram_utils import notificar_telegram
from bot_logic import estado

# Conexão com Binance pública (somente para consulta de preço)
binance = ccxt.binance()

# ⚙️ Função de checagem de status
def checar_status():
    try:
        if not estado["em_operacao"]:
            return

        par = estado["par"]
        tipo = estado["tipo"]
        entrada = estado["entrada"]
        tp1 = estado["tp1"]
        tp2 = estado["tp2"]
        tp3 = estado["tp3"]
        sl = estado["sl"]

        ticker = binance.fetch_ticker(par.replace("/", ""))
        preco_atual = ticker['last']

        print(f"[MONITOR] Preço atual de {par}: {preco_atual}", flush=True)

        # Verifica targets para BUY
        if tipo == "buy":
            if preco_atual >= tp3:
                notificar_telegram(f"🎯 Atingido TP3 ({tp3:.2f}) para {par}! 🤑")
                estado["em_operacao"] = False
            elif preco_atual >= tp2:
                notificar_telegram(f"🎯 Atingido TP2 ({tp2:.2f}) para {par}!")
            elif preco_atual >= tp1:
                notificar_telegram(f"🎯 Atingido TP1 ({tp1:.2f}) para {par}!")
            elif preco_atual <= sl:
                notificar_telegram(f"🛑 STOP atingido ({sl:.2f}) para {par} 😓")
                estado["em_operacao"] = False

        # Verifica targets para SELL
        if tipo == "sell":
            if preco_atual <= tp3:
                notificar_telegram(f"🎯 Atingido TP3 ({tp3:.2f}) para {par}! 🤑")
                estado["em_operacao"] = False
            elif preco_atual <= tp2:
                notificar_telegram(f"🎯 Atingido TP2 ({tp2:.2f}) para {par}!")
            elif preco_atual <= tp1:
                notificar_telegram(f"🎯 Atingido TP1 ({tp1:.2f}) para {par}!")
            elif preco_atual >= sl:
                notificar_telegram(f"🛑 STOP atingido ({sl:.2f}) para {par} 😓")
                estado["em_operacao"] = False

    except Exception as e:
        print(f"[ERRO] Falha no monitoramento de status: {e}", flush=True)

# 🚀 Iniciar agendador a cada 10 segundos
def iniciar_agendador():
    scheduler = BackgroundScheduler()
    scheduler.add_job(checar_status, 'interval', seconds=10)
    scheduler.start()
    print("✅ Agendador de status iniciado", flush=True)
