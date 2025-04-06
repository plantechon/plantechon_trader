import time

# Estado de operação
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

def process_signal(data):
    # Apenas imprime para teste — mais tarde conectamos à Binance
    print(f"Sinal recebido: {data}")
    estado["em_operacao"] = True
    estado["par"] = data.get("ativo", "BTCUSDT")
    return {"status": "simulado", "mensagem": "Sinal processado"}

def iniciar_monitoramento():
    print("🟢 Monitoramento iniciado (simulado)")
