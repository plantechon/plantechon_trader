import os
import ccxt

binance = ccxt.binance({
    'apiKey': os.getenv("BINANCE_API_KEY"),
    'secret': os.getenv("BINANCE_API_SECRET"),
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future'  # Isso é para operar no mercado de Futuros
    }
})
import time

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
from telegram_utils import notificar_telegram

def process_signal(data):
    ativo = data.get("ativo", "BTCUSDT")
    entrada = data.get("entrada", "0.0")
    tipo = data.get("tipo", "buy").upper()

    estado["em_operacao"] = True
    estado["par"] = ativo
    estado["entrada"] = entrada
    estado["tipo"] = tipo

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
from telegram_utils import notificar_telegram

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
