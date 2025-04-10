import asyncio
import ccxt
import json
import websockets
import threading
from telegram_utils import notificar_telegram
from bot_logic import estado, fechar_posicao_real

# 🔄 Flags para controle de alertas
avisado_tp1 = False
avisado_tp2 = False
avisado_tp3 = False
avisado_sl = False

async def monitorar_via_websocket():
    global avisado_tp1, avisado_tp2, avisado_tp3, avisado_sl

    while True:
        try:
            if not estado["em_operacao"]:
                await asyncio.sleep(1)
                continue

            par = estado["par"].lower().replace("/", "")
            url = f"wss://stream.binance.com:9443/ws/{par}@ticker"

            async with websockets.connect(url) as websocket:
                print(f"[WS] WebSocket conectado para {par.upper()}", flush=True)

                async for message in websocket:
                    if not estado["em_operacao"]:
                        break

                    data = json.loads(message)
                    preco_atual = float(data["c"])
                    print(f"[MONITOR] {par.upper()} = {preco_atual}", flush=True)

                    tipo = estado["tipo"]
                    entrada = estado["entrada"]
                    tp1 = estado["tp1"]
                    tp2 = estado["tp2"]
                    tp3 = estado["tp3"]
                    sl = estado["sl"]
                    quantidade = estado["quantidade"]
                    timeframe = estado.get("timeframe", "")

                    # BUY LOGIC
                    if tipo == "buy":
                        if preco_atual >= tp3 and not avisado_tp3:
                            notificar_telegram(
                                f"🎯 TP3 alcançado: *{tp3:.2f}*\n"
                                f"🟢 {par.upper()} encerrando operação.\n"
                                f"⏱️ TF: *{timeframe}*"
                            )
                            fechar_posicao_real(par.upper(), tipo, quantidade)
                            estado["em_operacao"] = False
                            avisado_tp3 = True

                        elif preco_atual >= tp2 and not avisado_tp2:
                            notificar_telegram(
                                f"🎯 TP2 alcançado: *{tp2:.2f}*\n"
                                f"🔁 SL ajustado para TP1: *{tp1:.2f}*"
                            )
                            estado["sl"] = tp1
                            avisado_tp2 = True

                        elif preco_atual >= tp1 and not avisado_tp1:
                            notificar_telegram(
                                f"🎯 TP1 alcançado: *{tp1:.2f}*\n"
                                f"🔁 SL ajustado para entrada: *{entrada:.2f}*"
                            )
                            estado["sl"] = entrada
                            avisado_tp1 = True

                        elif preco_atual <= estado["sl"] and not avisado_sl:
                            notificar_telegram(
                                f"🛑 *STOP atingido*: {estado['sl']:.2f}\n"
                                f"🟢 {par.upper()} finalizando operação."
                            )
                            fechar_posicao_real(par.upper(), tipo, quantidade)
                            estado["em_operacao"] = False
                            avisado_sl = True

                    # SELL LOGIC
                    elif tipo == "sell":
                        if preco_atual <= tp3 and not avisado_tp3:
                            notificar_telegram(
                                f"🎯 TP3 alcançado: *{tp3:.2f}*\n"
                                f"🔴 {par.upper()} encerrando operação.\n"
                                f"⏱️ TF: *{timeframe}*"
                            )
                            fechar_posicao_real(par.upper(), tipo, quantidade)
                            estado["em_operacao"] = False
                            avisado_tp3 = True

                        elif preco_atual <= tp2 and not avisado_tp2:
                            notificar_telegram(
                                f"🎯 TP2 alcançado: *{tp2:.2f}*\n"
                                f"🔁 SL ajustado para TP1: *{tp1:.2f}*"
                            )
                            estado["sl"] = tp1
                            avisado_tp2 = True

                        elif preco_atual <= tp1 and not avisado_tp1:
                            notificar_telegram(
                                f"🎯 TP1 alcançado: *{tp1:.2f}*\n"
                                f"🔁 SL ajustado para entrada: *{entrada:.2f}*"
                            )
                            estado["sl"] = entrada
                            avisado_tp1 = True

                        elif preco_atual >= estado["sl"] and not avisado_sl:
                            notificar_telegram(
                                f"🛑 *STOP atingido*: {estado['sl']:.2f}\n"
                                f"🔴 {par.upper()} finalizando operação."
                            )
                            fechar_posicao_real(par.upper(), tipo, quantidade)
                            estado["em_operacao"] = False
                            avisado_sl = True

        except websockets.ConnectionClosed:
            print("[WS] Conexão perdida. Reconectando em 3s...", flush=True)
            await asyncio.sleep(3)
        except Exception as e:
            print(f"[ERRO] WebSocket: {e}", flush=True)
            await asyncio.sleep(2)

# 🔁 Inicializa o agendador e o loop assíncrono
def iniciar_agendador():
    global avisado_tp1, avisado_tp2, avisado_tp3, avisado_sl
    avisado_tp1 = avisado_tp2 = avisado_tp3 = avisado_sl = False
    print("🟢 Iniciando monitoramento via WebSocket...", flush=True)

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(monitorar_via_websocket())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(monitorar_via_websocket())
        threading.Thread(target=loop.run_forever, daemon=True).start()
