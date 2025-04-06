import os
import time
import threading
import ccxt
from telegram_utils import notificar_telegram

# 🔐 Conexão com a Binance Futuros
binance = ccxt.binance({
    'apiKey': os.getenv("BINANCE_API_KEY"),
    'secret': os.getenv("BINANCE_API_SECRET"),
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future'
    }
})

# 🧠 Estado global do bot
estado = {
    "em_operacao": False,
    "par": "",
    "entrada": 0.0,
    "tp1": 0.0,
    "tp2": 0.0,
    "tp3": 0.0,
    "sl": 0.0,
    "tipo": "",
    "quantidade": 0.0,
    "hora_ultima_checagem": time.time()
}

# 🚀 Processa sinal e executa operação real

def process_signal(data):
    ativo = data.get("ativo", "BTCUSDT")
    entrada = float(data.get("entrada", "0.0"))
    tipo = data.get("tipo", "buy").upper()

    estado["em_operacao"] = True
    estado["par"] = ativo
    estado["entrada"] = entrada
    estado["tipo"] = tipo

    # 📈 Cálculo de alvos e stop
    rr1 = float(data.get("tp1_percent", 2)) / 100
    rr2 = float(data.get("tp2_percent", 4)) / 100
    rr3 = float(data.get("tp3_percent", 6)) / 100
    sl_percent = 0.03  # 3% de stop

    if tipo == "BUY":
        estado["sl"] = round(entrada * (1 - sl_percent), 2)
        estado["tp1"] = round(entrada * (1 + rr1), 2)
        estado["tp2"] = round(entrada * (1 + rr2), 2)
        estado["tp3"] = round(entrada * (1 + rr3), 2)
    else:
        estado["sl"] = round(entrada * (1 + sl_percent), 2)
        estado["tp1"] = round(entrada * (1 - rr1), 2)
        estado["tp2"] = round(entrada * (1 - rr2), 2)
        estado["tp3"] = round(entrada * (1 - rr3), 2)

    # 💰 Cálculo de tamanho da posição
    capital_total = 50
    risco_percent = float(data.get("risco_percent", 2))
    alavancagem = 5
    risco_usdt = (capital_total * risco_percent) / 100
    valor_operacao = risco_usdt * alavancagem
    quantidade = round(valor_operacao / entrada, 3)
    estado["quantidade"] = quantidade

    # 🔔 Alerta no Telegram
    msg = f"""
📈 NOVA OPERAÇÃO ({tipo})
Par: {ativo}
Entrada: {entrada}
Alavancagem: {alavancagem}x
TP1: {estado['tp1']} | TP2: {estado['tp2']} | TP3: {estado['tp3']}
SL: {estado['sl']}
Qtd estimada: {quantidade}
"""
    notificar_telegram(msg.strip())

    # 📤 Ordem real
    executar_ordem_real(ativo, tipo, quantidade)

    # 👁️ Inicia monitoramento para trailing stop
    threading.Thread(target=monitorar_trailing_stop, daemon=True).start()

    return {"status": "real", "mensagem": "Ordem real executada"}

# 🛒 Cria ordem de mercado

def executar_ordem_real(par, tipo, quantidade):
    try:
        if tipo.lower() == "buy":
            ordem = binance.create_market_buy_order(par, quantidade)
        else:
            ordem = binance.create_market_sell_order(par, quantidade)
        notificar_telegram(f"✅ Ordem REAL enviada: {tipo.upper()} {par} - Qtd: {quantidade}")
        return ordem
    except Exception as e:
        notificar_telegram(f"❌ Erro na ordem real: {e}")
        print(f"Erro: {e}")
        return None

# 📡 Função que monitora trailing stop e TPs

def monitorar_trailing_stop():
    par = estado["par"]
    tipo = estado["tipo"].lower()
    tp1, tp2, tp3, sl = estado["tp1"], estado["tp2"], estado["tp3"], estado["sl"]
    entrada = estado["entrada"]
    stop_atual = sl

    while estado["em_operacao"]:
        try:
            ticker = binance.fetch_ticker(par)
            preco_atual = ticker['last']

            # Verifica STOP
            if (tipo == "buy" and preco_atual <= stop_atual) or (tipo == "sell" and preco_atual >= stop_atual):
                notificar_telegram(f"🔴 STOP atingido em {preco_atual}")
                estado["em_operacao"] = False
                break

            # TP1 atingido
            if tipo == "buy" and preco_atual >= tp1 and stop_atual < entrada:
                stop_atual = entrada
                notificar_telegram(f"🟡 TP1 atingido! Stop movido para entrada ({entrada})")
            elif tipo == "sell" and preco_atual <= tp1 and stop_atual > entrada:
                stop_atual = entrada
                notificar_telegram(f"🟡 TP1 atingido! Stop movido para entrada ({entrada})")

            # TP2 atingido
            if tipo == "buy" and preco_atual >= tp2 and stop_atual < tp1:
                stop_atual = tp1
                notificar_telegram(f"🟠 TP2 atingido! Stop movido para TP1 ({tp1})")
            elif tipo == "sell" and preco_atual <= tp2 and stop_atual > tp1:
                stop_atual = tp1
                notificar_telegram(f"🟠 TP2 atingido! Stop movido para TP1 ({tp1})")

            # TP3 atingido
            if (tipo == "buy" and preco_atual >= tp3) or (tipo == "sell" and preco_atual <= tp3):
                notificar_telegram(f"✅ TP3 atingido! Operação encerrada com sucesso.")
                estado["em_operacao"] = False
                break

            time.sleep(30)  # intervalo de checagem

        except Exception as e:
            notificar_telegram(f"⚠️ Erro no monitoramento: {e}")
            time.sleep(30)

# 🔄 Monitoramento (placeholder)
def iniciar_monitoramento():
    print("🟢 Monitoramento iniciado (simulado)")
