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
        'positionSide': 'BOTH'
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
    "hora_ultima_checagem": time.time(),
    "bot_ativo": True
}

# 🔧 Cálculo de posição
def calcular_quantidade(ativo, preco_entrada, risco_percent=2, alavancagem=5):
    saldo = 50
    valor_total = saldo * alavancagem
    quantidade = valor_total / float(preco_entrada)
    return round(quantidade, 3)

# ✅ Executa ordem real
def executar_ordem_real(par, tipo, quantidade):
    try:
        print(f"🔽 Enviando ordem real...\nPar: {par} | Tipo: {tipo.upper()} | Qtd: {quantidade}")
        if tipo == "buy":
            ordem = binance.create_market_buy_order(par, quantidade)
        else:
            ordem = binance.create_market_sell_order(par, quantidade)
        notificar_telegram(f"✅ ORDEM REAL ENVIADA\nPar: {par}\nTipo: {tipo.upper()}\nQtd: {quantidade}")
        print("✅ Ordem enviada com sucesso!")
        return ordem
    except Exception as e:
        notificar_telegram(f"❌ ERRO ao enviar ordem: {e}")
        print(f"❌ ERRO ao enviar ordem: {e}")
        return None

# 🧠 Processa sinal recebido
def process_signal(data):
    if not estado["bot_ativo"]:
        notificar_telegram("⚠️ Bot está DESATIVADO. Comando ignorado.")
        return {"status": "inativo", "mensagem": "Bot desligado"}

    if estado["em_operacao"]:
        notificar_telegram(f"""
⚠️ SINAL IGNORADO (Já em operação)

📡 Novo sinal recebido, mas o bot está em operação.

🔁 Sinal:
• Par: {data.get('ativo')}
• Tipo: {data.get('tipo').upper()}

⏳ Aguarde o encerramento da operação atual.
""".strip())
        return {"status": "em_operacao", "mensagem": "Sinal ignorado pois já está em operação"}

    # 📥 Dados do sinal
    par = data.get("ativo", "BTCUSDT")
    entrada = float(data.get("entrada", "0"))
    tipo = data.get("tipo", "buy").lower()
    tp1_percent = float(data.get("tp1_percent", "2"))
    tp2_percent = float(data.get("tp2_percent", "4"))
    tp3_percent = float(data.get("tp3_percent", "6"))
    risco_percent = float(data.get("risco_percent", "2"))

    # 🎯 Alvos e SL
    tp1 = entrada * (1 + tp1_percent / 100) if tipo == "buy" else entrada * (1 - tp1_percent / 100)
    tp2 = entrada * (1 + tp2_percent / 100) if tipo == "buy" else entrada * (1 - tp2_percent / 100)
    tp3 = entrada * (1 + tp3_percent / 100) if tipo == "buy" else entrada * (1 - tp3_percent / 100)
    sl = entrada * (1 - 0.03) if tipo == "buy" else entrada * (1 + 0.03)

    # ⚙️ Atualiza estado
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

    # 🚀 Envia ordem
    executar_ordem_real(par, tipo, quantidade)

    # 📢 Alerta entrada
    msg = f"""
📈 NOVA OPERAÇÃO ({tipo.upper()})
────────────────────────────
🪙 Par: {par}
🎯 Entrada: {entrada}
⚖️ Alavancagem: 5x
🔹 TP1: {round(tp1, 2)}
🔹 TP2: {round(tp2, 2)}
🔹 TP3: {round(tp3, 2)}
❌ SL: {round(sl, 2)}
📦 Quantidade: {quantidade}
"""
    notificar_telegram(msg.strip())

    # 📊 Inicia acompanhamento
    threading.Thread(target=acompanhar_preco, args=(par, tipo, tp1, tp2, tp3, sl)).start()
    return {"status": "ok", "mensagem": "Sinal processado"}

# 👁️ Acompanhamento de operação
def acompanhar_preco(par, tipo, tp1, tp2, tp3, sl):
    stop_movel = sl
    try:
        while True:
            time.sleep(60)  # aumentado para evitar ban por excesso de requisição
            preco_atual = binance.fetch_ticker(par)['last']

            if tipo == "buy":
                if preco_atual >= tp3:
                    notificar_telegram("🎯 TP3 atingido. Operação finalizada.")
                    break
                elif preco_atual >= tp2:
                    stop_movel = tp1
                    notificar_telegram("🟢 TP2 atingido. Stop movido para TP1.")
                elif preco_atual >= tp1:
                    stop_movel = estado["entrada"]
                    notificar_telegram("🟡 TP1 atingido. Stop no ponto de entrada.")
                elif preco_atual <= stop_movel:
                    notificar_telegram("🛑 STOP atingido. Encerrando operação.")
                    break
            else:
                if preco_atual <= tp3:
                    notificar_telegram("🎯 TP3 atingido. Operação finalizada.")
                    break
                elif preco_atual <= tp2:
                    stop_movel = tp1
                    notificar_telegram("🟢 TP2 atingido. Stop movido para TP1.")
                elif preco_atual <= tp1:
                    stop_movel = estado["entrada"]
                    notificar_telegram("🟡 TP1 atingido. Stop no ponto de entrada.")
                elif preco_atual >= stop_movel:
                    notificar_telegram("🛑 STOP atingido. Encerrando operação.")
                    break
    except Exception as e:
        notificar_telegram(f"⚠️ Erro no acompanhamento: {e}")
    finally:
        estado["em_operacao"] = False
        estado["par"] = ""

# 🟢 Inicializa o monitoramento geral
def iniciar_monitoramento():
    print("🟢 Monitoramento iniciado")
