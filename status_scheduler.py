import asyncio
import ccxt
import json
import websockets
from telegram_utils import notificar_telegram
from bot_logic import estado, fechar_posicao_real
import threading
import time

# Flags para não repetir alertas
avisado_tp1 = False
avisado_tp2 = False
avisado_tp3 = False
avisado_sl = False

binance = ccxt.binance({
    'apiKey': os.getenv("BINANCE_API_KEY"),
    'secret': os.getenv("BINANCE_API_SECRET"),
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

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

                    if tipo == "buy":
                        if preco_atual >= tp3 and not avisado_tp3:
                            notificar_telegram(f"🎯 TP3 atingido ({tp3:.2f}) em {par.upper()} — encerrando operação.")
                            fechar_posicao_real(par.upper(), tipo, quantidade)
                            estado["em_operacao"] = False
                            avisado_tp3 = True

                        elif preco_atual >= tp2 and not avisado_tp2:
                            notificar_telegram(f"🎯 TP2 atingido ({tp2:.2f}) em {par.upper()} — SL ajustado para TP1 ({tp1:.2f})")
                            estado["sl"] = tp1
                            avisado_tp2 = True

                        elif preco_atual >= tp1 and not avisado_tp1:
                            notificar_telegram(f"🎯 TP1 atingido ({tp1:.2f}) em {par.upper()} — SL ajustado para entrada ({entrada:.2f})")
                            estado["sl"] = entrada
                            avisado_tp1 = True

                        elif preco_atual <= estado["sl"] and not avisado_sl:
                            notificar_telegram(f"🛑 SL atingido ({estado['sl']:.2f}) em {par.upper()} — encerrando operação.")
                            fechar_posicao_real(par.upper(), tipo, quantidade)
                            estado["em_operacao"] = False
                            avisado_sl = True

                    elif tipo == "sell":
                        if preco_atual <= tp3 and not avisado_tp3:
                            notificar_telegram(f"🎯 TP3 atingido ({tp3:.2f}) em {par.upper()} — encerrando operação.")
                            fechar_posicao_real(par.upper(), tipo, quantidade)
                            estado["em_operacao"] = False
                            avisado_tp3 = True

                        elif preco_atual <= tp2 and not avisado_tp2:
                            notificar_telegram(f"🎯 TP2 atingido ({tp2:.2f}) em {par.upper()} — SL ajustado para TP1 ({tp1:.2f})")
                            estado["sl"] = tp1
                            avisado_tp2 = True

                        elif preco_atual <= tp1 and not avisado_tp1:
                            notificar_telegram(f"🎯 TP1 atingido ({tp1:.2f}) em {par.upper()} — SL ajustado para entrada ({entrada:.2f})")
                            estado["sl"] = entrada
                            avisado_tp1 = True

                        elif preco_atual >= estado["sl"] and not avisado_sl:
                            notificar_telegram(f"🛑 SL atingido ({estado['sl']:.2f}) em {par.upper()} — encerrando operação.")
                            fechar_posicao_real(par.upper(), tipo, quantidade)
                            estado["em_operacao"] = False
                            avisado_sl = True

        except websockets.ConnectionClosed:
            print("[WS] Conexão perdida. Recomeçando em 2s...", flush=True)
            await asyncio.sleep(2)
        except Exception as e:
            print(f"[ERRO] WebSocket: {e}", flush=True)
            await asyncio.sleep(2)

# 🔄 Verifica posição na Binance a cada 60s e reseta se não houver operação
def verificar_posicao_binance():
    while True:
        try:
            if estado["em_operacao"]:
                symbol = estado["par"]
                side = "LONG" if estado["tipo"] == "buy" else "SHORT"
                posicoes = binance.fapiPrivateGetPositionRisk()
                posicao = next((p for p in posicoes if p["symbol"] == symbol.replace("/", "").upper()), None)

                if posicao and float(posicao["positionAmt"]) == 0:
                    print("[RESET] Posição zerada na Binance. Resetando estado local.", flush=True)
                    notificar_telegram(f"ℹ️ Posição encerrada manualmente no par {symbol}. Bot pronto para novo sinal.")
                    estado["em_operacao"] = False

        except Exception as e:
            print(f"[ERRO] Verificação de posição: {e}", flush=True)

        time.sleep(60)

# 🚀 Iniciar monitoramento e verificação de posição
def iniciar_agendador():
    global avisado_tp1, avisado_tp2, avisado_tp3, avisado_sl
    avisado_tp1 = avisado_tp2 = avisado_tp3 = avisado_sl = False
    print("🟢 WebSocket e verificação de posição iniciados", flush=True)

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(monitorar_via_websocket())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(monitorar_via_websocket())
        threading.Thread(target=loop.run_forever, daemon=True).start()

    threading.Thread(target=verificar_posicao_binance, daemon=True).start()
