import asyncio
import ccxt
import json
import websockets
from telegram_utils import notificar_telegram
from bot_logic import estado, fechar_posicao_real

# Flags para não repetir alertas
avisado_tp1 = False
avisado_tp2 = False
avisado_tp3 = False
avisado_sl = False

async def monitorar_via_websocket():
    global avisado_tp1, avisado_tp2, avisado_tp3, avisado_sl
    par = estado["par"].lower().replace("/", "")
    url = f"wss://stream.binance.com:9443/ws/{par}@ticker"

    async for websocket in websockets.connect(url):
        try:
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

                if tipo == "buy":
                    if preco_atual >= tp3 and not avisado_tp3:
                        notificar_telegram(f"🎯 Atingido TP3 ({tp3:.2f}) para {par.upper()}! 🤑 Fechando operação.")
                        fechar_posicao_real(par.upper(), tipo, quantidade)
                        estado["em_operacao"] = False
                        avisado_tp3 = True

                    elif preco_atual >= tp2 and not avisado_tp2:
                        notificar_telegram(f"🎯 Atingido TP2 ({tp2:.2f}) para {par.upper()}! SL agora ajustado para TP1 ({tp1:.2f})")
                        estado["sl"] = tp1
                        avisado_tp2 = True

                    elif preco_atual >= tp1 and not avisado_tp1:
                        notificar_telegram(f"🎯 Atingido TP1 ({tp1:.2f}) para {par.upper()}! SL agora ajustado para entrada ({entrada:.2f})")
                        estado["sl"] = entrada
                        avisado_tp1 = True

                    elif preco_atual <= estado["sl"] and not avisado_sl:
                        notificar_telegram(f"🛑 STOP atingido ({estado['sl']:.2f}) para {par.upper()} 😓 Fechando operação.")
                        fechar_posicao_real(par.upper(), tipo, quantidade)
                        estado["em_operacao"] = False
                        avisado_sl = True

                elif tipo == "sell":
                    if preco_atual <= tp3 and not avisado_tp3:
                        notificar_telegram(f"🎯 Atingido TP3 ({tp3:.2f}) para {par.upper()}! 🤑 Fechando operação.")
                        fechar_posicao_real(par.upper(), tipo, quantidade)
                        estado["em_operacao"] = False
                        avisado_tp3 = True

                    elif preco_atual <= tp2 and not avisado_tp2:
                        notificar_telegram(f"🎯 Atingido TP2 ({tp2:.2f}) para {par.upper()}! SL agora ajustado para TP1 ({tp1:.2f})")
                        estado["sl"] = tp1
                        avisado_tp2 = True

                    elif preco_atual <= tp1 and not avisado_tp1:
                        notificar_telegram(f"🎯 Atingido TP1 ({tp1:.2f}) para {par.upper()}! SL agora ajustado para entrada ({entrada:.2f})")
                        estado["sl"] = entrada
                        avisado_tp1 = True

                    elif preco_atual >= estado["sl"] and not avisado_sl:
                        notificar_telegram(f"🛑 STOP atingido ({estado['sl']:.2f}) para {par.upper()} 😓 Fechando operação.")
                        fechar_posicao_real(par.upper(), tipo, quantidade)
                        estado["em_operacao"] = False
                        avisado_sl = True

        except websockets.ConnectionClosed:
            print("[WS] Conexão perdida. Reconectando...", flush=True)
            continue
        except Exception as e:
            print(f"[ERRO] Monitor WS: {e}", flush=True)
            continue

# 🚀 Iniciar o monitoramento WebSocket

def iniciar_agendador():
    global avisado_tp1, avisado_tp2, avisado_tp3, avisado_sl
    avisado_tp1 = avisado_tp2 = avisado_tp3 = avisado_sl = False
    print("🟢 Monitoramento via WebSocket iniciado", flush=True)
    asyncio.get_event_loop().create_task(monitorar_via_websocket())
