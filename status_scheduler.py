import asyncio
import ccxt
import json
import websockets
from telegram_utils import notificar_telegram
from bot_logic import estado, fechar_posicao_real, atualizar_trailing_stop
import threading
import time
from datetime import datetime

# Flags para alertas únicos
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
                print(f"[WS] Conectado ao WebSocket para {par.upper()}", flush=True)

                async for message in websocket:
                    if not estado["em_operacao"]:
                        continue

                    data = json.loads(message)
                    preco_atual = float(data["c"])
                    print(f"[MONITOR] Preço atual de {par.upper()}: {preco_atual}", flush=True)

                    tipo = estado["tipo"]
                    entrada = estado["entrada"]
                    tp1 = estado["tp1"]
                    tp2 = estado["tp2"]
                    tp3 = estado["tp3"]
                    sl = estado["sl"]
                    quantidade = estado["quantidade"]

                    # 📉 Atualiza SL com trailing stop
                    atualizar_trailing_stop(preco_atual)

                    hora = datetime.now().strftime("%H:%M:%S")

                    if tipo == "buy":
                        if preco_atual >= tp3 and not avisado_tp3:
                            notificar_telegram(f"🎯 TP3 atingido ({tp3:.2f}) às {hora} | {par.upper()} | Fechando operação.")
                            fechar_posicao_real(par.upper(), tipo, quantidade)
                            estado["em_operacao"] = False
                            avisado_tp3 = True

                        elif preco_atual >= tp2 and not avisado_tp2:
                            notificar_telegram(f"🎯 TP2 atingido ({tp2:.2f}) às {hora} | SL movido para TP1 ({tp1:.2f})")
                            estado["sl"] = tp1
                            avisado_tp2 = True

                        elif preco_atual >= tp1 and not avisado_tp1:
                            notificar_telegram(f"🎯 TP1 atingido ({tp1:.2f}) às {hora} | SL movido para entrada ({entrada:.2f})")
                            estado["sl"] = entrada
                            avisado_tp1 = True

                        elif preco_atual <= estado["sl"] and not avisado_sl:
                            notificar_telegram(f"🛑 STOP atingido ({estado['sl']:.2f}) às {hora} | {par.upper()} | Fechando operação.")
                            fechar_posicao_real(par.upper(), tipo, quantidade)
                            estado["em_operacao"] = False
                            avisado_sl = True

                    elif tipo == "sell":
                        if preco_atual <= tp3 and not avisado_tp3:
                            notificar_telegram(f"🎯 TP3 atingido ({tp3:.2f}) às {hora} | {par.upper()} | Fechando operação.")
                            fechar_posicao_real(par.upper(), tipo, quantidade)
                            estado["em_operacao"] = False
                            avisado_tp3 = True

                        elif preco_atual <= tp2 and not avisado_tp2:
                            notificar_telegram(f"🎯 TP2 atingido ({tp2:.2f}) às {hora} | SL movido para TP1 ({tp1:.2f})")
                            estado["sl"] = tp1
                            avisado_tp2 = True

                        elif preco_atual <= tp1 and not avisado_tp1:
                            notificar_telegram(f"🎯 TP1 atingido ({tp1:.2f}) às {hora} | SL movido para entrada ({entrada:.2f})")
                            estado["sl"] = entrada
                            avisado_tp1 = True

                        elif preco_atual >= estado["sl"] and not avisado_sl:
                            notificar_telegram(f"🛑 STOP atingido ({estado['sl']:.2f}) às {hora} | {par.upper()} | Fechando operação.")
                            fechar_posicao_real(par.upper(), tipo, quantidade)
                            estado["em_operacao"] = False
                            avisado_sl = True

        except Exception as e:
            print(f"[ERRO] WebSocket: {e}", flush=True)
            await asyncio.sleep(5)

# 🔄 Iniciador do agendador
def iniciar_agendador():
    thread = threading.Thread(target=lambda: asyncio.run(monitorar_via_websocket()))
    thread.start()
