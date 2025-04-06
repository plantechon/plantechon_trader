from telegram_utils import notificar_telegram

def process_signal(data):
    ativo = data.get("ativo", "BTCUSDT")
    entrada = data.get("entrada", "0.0")
    tipo = data.get("tipo", "buy").upper()

    # Atualiza estado interno (simulação)
    estado["em_operacao"] = True
    estado["par"] = ativo
    estado["entrada"] = entrada
    estado["tipo"] = tipo

    # Monta mensagem Telegram
    msg = f"""
📈 NOVA OPERAÇÃO ({tipo})
Par: {ativo}
Entrada: {entrada}
Alavancagem: 5x
TP1: {data.get("tp1_percent", "2")}% | TP2: {data.get("tp2_percent", "4")}% | TP3: {data.get("tp3_percent", "6")}% 
Timeframe: {data.get("timeframe", "??")}
"""
    notificar_telegram(msg.strip())

    return {"status": "simulado", "mensagem": "Sinal processado e enviado"}
def iniciar_monitoramento():
    print("🟢 Monitoramento iniciado (simulado)")
