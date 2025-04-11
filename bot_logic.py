import os
import time
import ccxt
from telegram_utils import notificar_telegram

# 🔐 Conexão com Binance Futuros (modo hedge compatível)
binance = ccxt.binance({
    'apiKey': os.getenv("BINANCE_API_KEY"),
    'secret': os.getenv("BINANCE_API_SECRET"),
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
        'hedgeMode': True
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
    "ativado": True,
    "timeframe": ""
}

# 🔧 Cálculo de posição
def calcular_quantidade(ativo, preco_entrada, risco_percent=2, alavancagem=5):
    saldo = 50
    valor_total = saldo * alavancagem
    quantidade = valor_total / float(preco_entrada)
    return round(quantidade, 3)

# ✅ Executa ordem real com verificação de posição
def executar_ordem_real(par, tipo, quantidade, tentativas=3):
    for tentativa in range(1, tentativas + 1):
        try:
            print(f"[EXECUÇÃO] Tentativa {tentativa} - Enviando ordem real...", flush=True)
            print(f"Par: {par} | Tipo: {tipo.upper()} | Quantidade: {quantidade}", flush=True)

            side = "buy" if tipo == "buy" else "sell"
            position_side = "LONG" if tipo == "buy" else "SHORT"

            binance.create_order(
                symbol=par,
                type="market",
                side=side,
                amount=quantidade,
                params={"positionSide": position_side}
            )

            time.sleep(2)

            # Verifica se a posição está ativa
            posicoes = binance.fetch_positions([par])
            encontrou = any(
                p["symbol"] == par and float(p["contracts"]) > 0 and p["side"].upper() == position_side
                for p in posicoes
            )

            if encontrou:
                notificar_telegram(
                    f"🟢 *ORDEM EXECUTADA!*\n"
                    f"📊 Par: *{par}*\n"
                    f"{'🟢' if tipo == 'buy' else '🔴'} Tipo: *{tipo.upper()}*\n"
                    f"💰 Qtd: *{quantidade}*\n"
                    f"🎯 Entrada: *{estado['entrada']:.2f}*\n"
                    f"📈 TP1: *{estado['tp1']:.2f}* | TP2: *{estado['tp2']:.2f}* | TP3: *{estado['tp3']:.2f}*\n"
                    f"🛑 SL: *{estado['sl']:.2f}*\n"
                    f"⏱️ Timeframe: *{estado.get('timeframe', '')}*"
                )
                print("[EXECUÇÃO] Ordem confirmada com posição ativa!", flush=True)
                return True
            else:
                notificar_telegram("⚠️ Ordem enviada, mas nenhuma posição ativa encontrada na Binance.")
                print("[ERRO] Ordem enviada, mas nenhuma posição ativa encontrada.", flush=True)
                return False

        except Exception as e:
            notificar_telegram(f"❌ Erro ao enviar/verificar ordem: {e}")
            print(f"[ERRO] Verificação de posição: {e}", flush=True)
            return False

    return False

# ❌ Fecha posição real
def fechar_posicao_real(par, tipo, quantidade):
    try:
        lado_oposto = "sell" if tipo == "buy" else "buy"
        position_side = "LONG" if tipo == "buy" else "SHORT"

        print(f"[FECHAMENTO] Enviando ordem para fechar {position_side} de {quantidade} {par}", flush=True)

        binance.create_order(
            symbol=par,
            type="market",
            side=lado_oposto,
            amount=quantidade,
            params={"positionSide": position_side}
        )

        notificar_telegram(f"📉 POSIÇÃO FECHADA: {par} | Lado: {tipo.upper()} | Qtd: {quantidade}")
        print("[FECHAMENTO] Ordem de fechamento enviada com sucesso!", flush=True)

    except Exception as e:
        notificar_telegram(f"❌ ERRO ao fechar posição: {e}")
        print(f"[ERRO] Falha ao fechar posição: {e}", flush=True)

# 🧠 Processa o sinal recebido
def process_signal(data):
    print("[SINAL] Sinal recebido:")
    print(data, flush=True)

    if not estado.get("ativado"):
        return {"status": "desativado", "mensagem": "Bot desativado"}

    if estado["em_operacao"]:
        notificar_telegram(
            f"⚠️ SINAL IGNORADO (Já em operação)\n"
            f"📡 Par: {data.get('ativo')}\n"
            f"🟢 Tipo: {data.get('tipo').upper()}"
        )
        return {"status": "em_operacao", "mensagem": "Sinal ignorado pois já está em operação"}

    try:
        par = data["ativo"]
        entrada = float(data["entrada"])
        tipo = data["tipo"].lower()
        risco_percent = float(data.get("risco_percent", 2))
        tp1 = entrada * (1 + float(data.get("tp1_percent", 2)) / 100) if tipo == "buy" else entrada * (1 - float(data.get("tp1_percent", 2)) / 100)
        tp2 = entrada * (1 + float(data.get("tp2_percent", 4)) / 100) if tipo == "buy" else entrada * (1 - float(data.get("tp2_percent", 4)) / 100)
        tp3 = entrada * (1 + float(data.get("tp3_percent", 6)) / 100) if tipo == "buy" else entrada * (1 - float(data.get("tp3_percent", 6)) / 100)
        sl = entrada * (1 - 0.01) if tipo == "buy" else entrada * (1 + 0.01)
        timeframe = data.get("timeframe", "")
        quantidade = calcular_quantidade(par, entrada, risco_percent)

        estado.update({
            "em_operacao": False,  # Só vai mudar para True após confirmar a posição
            "par": par,
            "entrada": entrada,
            "tp1": tp1,
            "tp2": tp2,
            "tp3": tp3,
            "sl": sl,
            "tipo": tipo,
            "quantidade": quantidade,
            "timeframe": timeframe
        })

        if executar_ordem_real(par, tipo, quantidade):
            estado["em_operacao"] = True
            return {"status": "executado", "mensagem": "Ordem executada e posição confirmada"}
        else:
            return {"status": "erro", "mensagem": "Ordem não confirmada"}

    except Exception as e:
        notificar_telegram(f"❌ Erro ao processar sinal: {e}")
        print(f"[ERRO] Problema ao processar sinal: {e}", flush=True)
        return {"status": "erro", "mensagem": str(e)}

__all__ = ["estado", "process_signal", "fechar_posicao_real"]
