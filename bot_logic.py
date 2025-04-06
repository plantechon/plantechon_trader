import os
import time
import threading
import ccxt
from telegram_utils import notificar_telegram

# 🔐 Conexão com Binance Futuros
binance = ccxt.binance({
    'apiKey': os.getenv("BINANCE_API_KEY"),
    'secret': os.getenv("BINANCE_API_SECRET"),
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future'
    }
})

# 🔁 Estado de operação
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

# 🔧 Calcula o tamanho da posição com base no saldo
def calcular_quantidade(ativo, preco_entrada, risco_percent=2, alavancagem=5):
    saldo = 50  # USDT fixo
    valor_total = saldo * alavancagem
    quantidade = valor_total / float(preco_entrada)
    return round(quantidade, 3)

# ✅ Envia ordem real com positionSide
def executar_ordem_real(par, tipo, quantidade):
    try:
        print(f"📤 ENVIANDO ORDEM REAL: {tipo.upper()} {par} | Quantidade: {quantidade}")
        side = "buy" if tipo == "buy" else "sell"
        position_side = "LONG" if tipo == "buy" else "SHORT"

        ordem = binance.create_order(
            symbol=par,
            type="market",
            side=side,
            amount=quantidade,
            params={
                "positionSide": position_side
            }
        )

        print(f"✅ ORDEM EXECUTADA COM SUCESSO: {ordem}")
        notificar_telegram(f"✅ ORDEM REAL ENVIADA\nPar: {par}\nTipo: {tipo.upper()}\nQtd: {quantidade}")
        return ordem

    except Exception as e:
        print(f"❌ ERRO AO ENVIAR ORDEM: {e}")
        notificar_telegram(f"❌ ERRO ao enviar ordem: {e}")
        return None

# 🧠 Processa o sinal recebido
def process_signal(data):
    if estado["em_operacao"]:
        notificar_telegram(f"📨 NOVO SINAL RECEBIDO MAS IGNORADO (Já em operação)\nPar: {data.get('ativo')}\nTipo: {data.get('tipo')}")
        return {"status": "em_operacao", "mensagem": "Sinal ignorado pois já está em operação"}

    par = data.get("ativo", "BTCUSDT")
    entrada = float(data.get("entrada", "0"))
    tipo = data.get("tipo", "buy").lower()
    tp1_percent = float(data.get("tp1_percent", "2"))
    tp2_percent = float(data.get("tp2_percent", "4"))
    tp3_percent = float(data.get("tp3_percent", "6"))
    risco_percent = float(data.get("risco_percent", "2"))

    tp1 = entrada * (1 + tp1_percent / 100) if tipo == "buy" else entrada * (1 - tp1_percent / 100)
    tp2 = entrada * (1 + tp2_percent / 100) if tipo == "buy" else entrada * (1 - tp2_percent / 100)
    tp3 = entrada * (1 + tp3_percent / 100) if tipo == "buy" else entrada * (1 - tp3_percent / 100)
    sl = entrada * (1 - 0.03) if tipo == "buy" else entrada * (1 + 0.03)

    quantidade = calcular_quantidade(par, entrada, risco_percent)

    estado.update({
        "em_operacao": True,
        "par": par,
        "entrada": entrada,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "sl": sl,
        "tipo": tipo,
        "quantidade": quantidade,
        "hora_ultima_checagem": time.time()
    })

    executar_ordem_real(par, tipo, quantidade)

    msg = f"""
📈 NOVA OPERAÇÃO ({tipo.upper()})
Par: {par}
Entrada: {entrada}
Alavancagem: 5x
TP1: {round(tp1, 2)} | TP2: {round(tp2, 2)} | TP3: {round(tp3, 2)}
SL: {round(sl, 2)}
Qtd: {quantidade}
"""
    notificar_telegram(msg.strip())

    threading.Thread(target=acompanhar_preco, args=(par, tipo, tp1, tp2, tp3, sl)).start()

    return {"status": "ok", "mensagem": "Sinal processado"}

# 🔁 Monitoramento de preço para SL / TPs
def acompanhar_preco(par, tipo, tp1, tp2, tp3, sl):
    stop_movel = sl
    entrada = estado["entrada"]

    try:
        while True:
            time.sleep(30)
            ticker = binance.fetch_ticker(par)
            preco_atual = ticker['last']

            if tipo == "buy":
                if preco_atual >= tp3:
                    notificar_telegram("🎯 TP3 atingido. Operação finalizada.")
                    break
                elif preco_atual >= tp2:
                    stop_movel = tp1
                    notificar_telegram("🟢 TP2 atingido. Stop movido para TP1.")
                elif preco_atual >= tp1:
                    stop_movel = entrada
                    notificar_telegram("🟡 TP1 atingido. Stop no ponto de entrada.")
                elif preco_atual <= stop_movel:
                    notificar_telegram("🛑 STOP atingido. Operação encerrada.")
                    break
            else:
                if preco_atual <= tp3:
                    notificar_telegram("🎯 TP3 atingido. Operação finalizada.")
                    break
                elif preco_atual <= tp2:
                    stop_movel = tp1
                    notificar_telegram("🟢 TP2 atingido. Stop movido para TP1.")
                elif preco_atual <= tp1:
                    stop_movel = entrada
                    notificar_telegram("🟡 TP1 atingido. Stop no ponto de entrada.")
                elif preco_atual >= stop_movel:
                    notificar_telegram("🛑 STOP atingido. Operação encerrada.")
                    break

    except Exception as e:
        notificar_telegram(f"⚠️ Erro no monitoramento: {e}")
    finally:
        estado["em_operacao"] = False
        estado["par"] = ""

# 🚀 Inicia o monitoramento simulado
def iniciar_monitoramento():
    print("🟢 Monitoramento iniciado")
