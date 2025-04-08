from apscheduler.schedulers.background import BackgroundScheduler
import time
import ccxt
from telegram_utils import notificar_telegram
import bot_logic

# Conexão com Binance pública (consulta de preço)
binance = ccxt.binance()

# Flags para não repetir alertas
avisado_tp1 = False
avisado_tp2 = False
avisado_tp3 = False
avisado_sl = False

# ⚙️ Função de checagem de status
def checar_status():
    global avisado_tp1, avisado_tp2, avisado_tp3, avisado_sl

    try:
        if not bot_logic.estado["em_operacao"]:
            return

        par = bot_logic.estado["par"]
        tipo = bot_logic.estado["tipo"]
        entrada = bot_logic.estado["entrada"]
        tp1 = bot_logic.estado["tp1"]
        tp2 = bot_logic.estado["tp2"]
        tp3 = bot_logic.estado["tp3"]
        sl = bot_logic.estado["sl"]
        quantidade = bot_logic.estado["quantidade"]

        ticker = binance.fetch_ticker(par.replace("/", ""))
        preco_atual = ticker['last']

        print(f"[MONITOR] Preço atual de {par}: {preco_atual}", flush=True)

        if tipo == "buy":
            if preco_atual >= tp3 and not avisado_tp3:
                notificar_telegram(f"🎯 Atingido TP3 ({tp3:.2f}) para {par}! 🤑 Fechando operação.")
                bot_logic.fechar_posicao_real(par, tipo, quantidade)
                bot_logic.estado["em_operacao"] = False
                avisado_tp3 = True

            elif preco_atual >= tp2 and not avisado_tp2:
                notificar_telegram(f"🎯 Atingido TP2 ({tp2:.2f}) para {par}! SL agora ajustado para TP1 ({tp1:.2f})")
                bot_logic.estado["sl"] = tp1
                avisado_tp2 = True

            elif preco_atual >= tp1 and not avisado_tp1:
                notificar_telegram(f"🎯 Atingido TP1 ({tp1:.2f}) para {par}! SL agora ajustado para entrada ({entrada:.2f})")
                bot_logic.estado["sl"] = entrada
                avisado_tp1 = True

            elif preco_atual <= bot_logic.estado["sl"] and not avisado_sl:
                notificar_telegram(f"🛑 STOP atingido ({bot_logic.estado['sl']:.2f}) para {par} 😓 Fechando operação.")
                bot_logic.fechar_posicao_real(par, tipo, quantidade)
                bot_logic.estado["em_operacao"] = False
                avisado_sl = True

        elif tipo == "sell":
            if preco_atual <= tp3 and not avisado_tp3:
                notificar_telegram(f"🎯 Atingido TP3 ({tp3:.2f}) para {par}! 🤑 Fechando operação.")
                bot_logic.fechar_posicao_real(par, tipo, quantidade)
                bot_logic.estado["em_operacao"] = False
                avisado_tp3 = True

            elif preco_atual <= tp2 and not avisado_tp2:
                notificar_telegram(f"🎯 Atingido TP2 ({tp2:.2f}) para {par}! SL agora ajustado para TP1 ({tp1:.2f})")
                bot_logic.estado["sl"] = tp1
                avisado_tp2 = True

            elif preco_atual <= tp1 and not avisado_tp1:
                notificar_telegram(f"🎯 Atingido TP1 ({tp1:.2f}) para {par}! SL agora ajustado para entrada ({entrada:.2f})")
                bot_logic.estado["sl"] = entrada
                avisado_tp1 = True

            elif preco_atual >= bot_logic.estado["sl"] and not avisado_sl:
                notificar_telegram(f"🛑 STOP atingido ({bot_logic.estado['sl']:.2f}) para {par} 😓 Fechando operação.")
                bot_logic.fechar_posicao_real(par, tipo, quantidade)
                bot_logic.estado["em_operacao"] = False
                avisado_sl = True

    except Exception as e:
        print(f"[ERRO] Falha no monitoramento de status: {e}", flush=True)

# 🚀 Iniciar agendador a cada 10 segundos
def iniciar_agendador():
    global avisado_tp1, avisado_tp2, avisado_tp3, avisado_sl
    avisado_tp1 = avisado_tp2 = avisado_tp3 = avisado_sl = False

    scheduler = BackgroundScheduler()
    scheduler.add_job(checar_status, 'interval', seconds=10)
    scheduler.start()
    print("✅ Agendador de status iniciado", flush=True)
