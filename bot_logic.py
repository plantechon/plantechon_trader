import os
import time
import threading
import ccxt
from telegram_utils import notificar_telegram

# 🔐 Conexão com Binance Futuros (modo hedge compatível)
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
    "hora_ultima_checagem": time.time(),
    "ativado": True
}

# 🔧 Cálculo de posição
def calcular_quantidade(ativo, preco_entrada, risco_percent=2, alavancagem=5):
    saldo = 50
    valor_total = saldo * alavancagem
    quantidade = valor_total / float(preco_entrada)
    return round(quantidade, 3)

# ✅ Executa ordem real com suporte ao modo HEDGE
def executar_ordem_real(par, tipo, quantidade):
    try:
        print("[EXECUÇÃO] Enviando ordem real...", flush=True)
        print(f"Par: {par} | Tipo: {tipo.upper()} | Quantidade: {quantidade}", flush=True)

        side = "buy" if tipo == "buy" else "sell"
        position_side = "LONG" if tipo == "buy" else "SHORT"

        ordem = binance.create_order(
            symbol=par,
            type="market",
            side=side,
            amount=quantidade,
            params={"positionSide": position_side}
        )

        notificar_telegram(f"✅ ORDEM REAL ENVIADA\nPar: {par}\nTipo: {tipo.upper()}\nQtd: {quantidade}")
        print("[EXECUÇÃO] Ordem enviada com sucesso!", flush=True)
        return ordem
    except Exception as e:
        notificar_telegram(f"❌ ERRO ao enviar ordem: {e}")
        print(f"[ERRO] Falha ao enviar ordem: {e}", flush=True)
        return None

# 🧠 Processa sinal recebido
def process_signal(data):
    print("[SINAL] Sinal recebido:")
    print(data, flush=True)

    if not estado.get("ativado"):
        print("[STATUS] Bot desativado. Ignorando sinal.", flush=True)
        return {"status": "desativado", "mensagem": "Bot desativado"}

    if estado["em_operacao"]:
        notificar_telegram(
            f"⚠️ SINAL IGNORADO (Já em operação)\n"
            f"📡 Novo sinal recebido:\n"
            f"Par: {data.get('ativo')}\n"
            f"Tipo: {data.get('tipo').upper()}\n"
            f"⏳ Aguarde o fim da operação atual."
        )
        print("[SINAL] Ignorado: já em operação.", flush=True)
        return {"status": "em_operacao", "mensagem": "Sinal ignorado pois já está em operação"}

    # Dados do sinal
    try:
        par = data["ativo"]
        entrada = float(data["entrada"])
        tipo = data["tipo"].lower()
        risco_percent = float(data.get("risco_percent", 2))
        tp1 = entrada * (1 + float(data.get("tp1_percent", 2)) / 100) if tipo == "buy" else entrada * (1 - float(data.get("tp1_percent", 2)) / 100)
        tp2 = entrada * (1 + float(data.get("tp2_percent", 4)) / 100) if tipo == "buy" else entrada * (1 - float(data.get("tp2_percent", 4)) / 100)
        tp3 = entrada * (1 + float(data.get("tp3_percent", 6)) / 100) if tipo == "buy" else entrada * (1 - float(data.get("tp3_percent", 6)) / 100)
        sl = entrada * (1 - 0.01) if tipo == "buy" else entrada * (1 + 0.01)
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
            "quantidade": quantidade
        })

        print("[ORDEM] Par: {} | Entrada: {} | Quantidade: {}".format(par, entrada, quantidade), flush=True)
        executar_ordem_real(par, tipo, quantidade)

        return {"status": "executado", "mensagem": "Sinal processado e ordem executada"}
    except Exception as e:
        print(f"[ERRO] Problema ao processar sinal: {e}", flush=True)
        notificar_telegram(f"❌ Erro ao processar sinal: {e}")
        return {"status": "erro", "mensagem": str(e)}
