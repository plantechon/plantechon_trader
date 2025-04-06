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
        'defaultType': 'future',
        'defaultMarket': 'futures'
    }
})

# 🔁 Estado da operação
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

# 🔧 Cálculo da quantidade com base no saldo e alavancagem
def calcular_quantidade(ativo, preco_entrada, risco_percent=2, alavancagem=5):
    saldo = 50  # Valor fixo em USDT (ajustável)
    valor_total = saldo * alavancagem
    quantidade = valor_total / float(preco_entrada)
    return round(quantidade, 3)

# ✅ Executa ordem real com logs
def executar_ordem_real(par, tipo, quantidade):
    try:
        print(f"📤 Enviando ordem: {tipo.upper()} {par} - Qtd: {quantidade}")
        if tipo.lower() == "buy":
            ordem = binance.create_market_buy_order(par, quantidade)
        else:
            ordem = binance.create_market_sell_order(par, quantity=quantidade)
        print("✅ Ordem executada com sucesso!")
        notificar_telegram(f"✅ ORDEM REAL ENVIADA\nPar: {par}\nTipo: {tipo.upper()}\nQtd: {quantidade}")
        return ordem
    except Exception as e:
        print(f"❌ Erro na ordem: {e}")
        notificar_telegram(f"❌ ERRO ao enviar ordem: {e}")
        return None

# 🧠 Processamento do sinal recebido
def process_signal(data):
    if estado["em_operacao"]:
        notificar_telegram(f"📨 NOVO SINAL RECEBIDO MAS IGNORADO (Já em operação)\nPar: {data.get('ativo')}\nTipo: {data.get('tipo')}")
        return {"status": "em_operacao", "mensagem": "Sinal ignorado pois já está em operação"}

    # 🔍 Coleta e tratamento dos dados do sinal
    par = data.get("ativo", "BTCUSDT")
    entrada = float(data.get("entrada", "0"))
    tipo = data.get("tipo", "buy").lower()
    tp1_percent = float(data.get("tp1_percent", "2"))
    tp2_percent = float(data.get("tp2_percent", "4"))
    tp3_percent = float(data.get("tp3_percent", "6"))
    risco_percent = float(data.get("risco_percent", "2"))

    # 🎯 Cálculo de alvos e stop
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

    # ✅ Executa ordem real
    executar_ordem_real(par, tipo, quantidade)

    # 📢 Notifica operação no Telegram com mensagem profissional
    msg = f"""
📢 NOVA OPERAÇÃO EXECUTADA

🔹 Par: {par}
📈 Direção: {tipo.upper()}
💰 Entrada: {entrada:,.2f}
📊 Alavancagem: 5x
🔹 Quantidade: {quantidade}

🎯 Take Profits:
• TP1 ➜ {tp1:,.2f}
• TP2 ➜ {tp2:,.2f}
• TP3 ➜ {tp3:,.2f}

🛑 Stop Loss: {sl:,.2f}
🕒 Timeframe: {data.get("timeframe", "??")}min
""".strip()

    notificar_telegram(msg)

    # 🔁 Inicia monitoramento da operação
    threading.Thread(target=acompanhar_preco, args=(par, tipo, tp1, tp2, tp3, sl, entrada)).start()

    return {"status": "ok", "mensagem": "Sinal processado"}

# 📡 Monitoramento de preço com trailing stop
def acompanhar_preco(par, tipo, tp1, tp2, tp3, sl, entrada):
    stop_movel = sl
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
                    notificar_telegram("🟢 Preço passou do TP2. Stop movido para TP1.")
                elif preco_atual >= tp1:
                    stop_movel = entrada
                    notificar_telegram("🟡 TP1 atingido. Stop movido para o ponto de entrada.")
                elif preco_atual <= stop_movel:
                    notificar_telegram("🛑 STOP atingido. Saindo da operação.")
                    break
            else:
                if preco_atual <= tp3:
                    notificar_telegram("🎯 TP3 atingido. Operação finalizada.")
                    break
                elif preco_atual <= tp2:
                    stop_movel = tp1
                    notificar_telegram("🟢 Preço passou do TP2. Stop movido para TP1.")
                elif preco_atual <= tp1:
                    stop_movel = entrada
                    notificar_telegram("🟡 TP1 atingido. Stop movido para o ponto de entrada.")
                elif preco_atual >= stop_movel:
                    notificar_telegram("🛑 STOP atingido. Saindo da operação.")
                    break
    except Exception as e:
        notificar_telegram(f"⚠️ Erro no acompanhamento: {e}")
    finally:
        estado["em_operacao"] = False
        estado["par"] = ""

# 🚦 Inicia o monitoramento do bot
def iniciar_monitoramento():
    print("🟢 Monitoramento iniciado")
