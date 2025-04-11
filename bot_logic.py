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

# ✅ Verifica se a posição foi realmente aberta
def verificar_posicao_ativa(par, tipo, tentativas=3):
    for tentativa in range(tentativas):
        try:
            time.sleep(2)  # espera antes de checar
            posicoes = binance.fapiPrivateGetPositionRisk()
            for pos in posicoes:
                if pos['symbol'] == par.replace("/", ""):
                    pos_aberta = float(pos['positionAmt'])
                    if (tipo == "buy" and pos_aberta > 0) or (tipo == "sell" and pos_aberta < 0):
                        return True
        except Exception as e:
            print(f"[ERRO] Verificação de posição: {e}", flush=True)
    return False

# ✅ Executa ordem real com suporte ao modo HEDGE
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

            if verificar_posicao_ativa(par, tipo):
                print("[EXECUÇÃO] Ordem enviada com sucesso!", flush=True)
                return True
            else:
                notificar_telegram("⚠️ Ordem enviada, mas nenhuma posição ativa encontrada na Binance.")
                print("[ERRO] Ordem enviada, mas nenhuma posição ativa encontrada.", flush=True)
                return False

        except ccxt.NetworkError as e:
            if "418" in str(e) or "Too many requests" in str(e):
                notificar_telegram("⚠️ IP banido pela Binance. Aguardando 30s...")
                print("[ERRO] IP banido. Aguardando 30s...", flush=True)
                time.sleep(30)
                continue
        except Exception as e:
            notificar_telegram(f"❌ ERRO ao enviar ordem: {e}")
            print(f"[ERRO] Falha ao enviar ordem: {e}", flush=True)
            return False

    notificar_telegram("❌ Todas as tentativas de enviar ordem falharam.")
    return False

# ❌ Fechar posição real
def fechar_posicao_real(par, tipo, quantidade):
    try:
        lado_oposto = "sell" if tipo == "buy" else "buy"
        position_side = "LONG" if tipo == "buy" else "SHORT"

        binance.create_order(
            symbol=par,
            type="market",
            side=lado_oposto,
            amount=quantidade,
            params={"positionSide": position_side}
        )

        notificar_telegram(f"📉 POSIÇÃO FECHADA: {par} | Lado: {tipo.upper()} | Qtd: {quantidade}")
        print("[FECHAMENTO] Ordem de fechamento enviada com sucesso!", flush=True)
        return True

    except Exception as e:
        notificar_telegram(f"❌ ERRO ao fechar posição: {e}")
        print(f"[ERRO] Falha ao fechar posição: {e}", flush=True)
        return False

# 🧠 Processa sinal recebido
def process_signal(data):
    print("[SINAL] Sinal recebido:")
    print(data, flush=True)

    if not estado.get("ativado"):
        return {"status": "desativado", "mensagem": "Bot desativado"}

    if estado["em_operacao"]:
        return {"status": "em_operacao", "mensagem": "Sinal ignorado pois já está em operação"}

    try:
        par = data["ativo"]
        entrada = float(data["entrada"])
        tipo = data["tipo"].lower()
        timeframe = data.get("timeframe", "")
        risco_percent = float(data.get("risco_percent", 2))
        tp1 = entrada * (1 + float(data.get("tp1_percent", 2)) / 100) if tipo == "buy" else entrada * (1 - float(data.get("tp1_percent", 2)) / 100)
        tp2 = entrada * (1 + float(data.get("tp2_percent", 4)) / 100) if tipo == "buy" else entrada * (1 - float(data.get("tp2_percent", 4)) / 100)
        tp3 = entrada * (1 + float(data.get("tp3_percent", 6)) / 100) if tipo == "buy" else entrada * (1 - float(data.get("tp3_percent", 6)) / 100)
        sl = entrada * (1 - 0.01) if tipo == "buy" else entrada * (1 + 0.01)
        quantidade = calcular_quantidade(par, entrada, risco_percent)

        print(f"[ORDEM] Par: {par} | Entrada: {entrada} | Quantidade: {quantidade}", flush=True)

        if executar_ordem_real(par, tipo, quantidade):
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
                "timeframe": timeframe
            })
            return {"status": "executado", "mensagem": "Sinal processado e ordem executada"}
        else:
            return {"status": "falha", "mensagem": "Ordem não foi confirmada"}

    except Exception as e:
        print(f"[ERRO] Problema ao processar sinal: {e}", flush=True)
        notificar_telegram(f"❌ Erro ao processar sinal: {e}")
        return {"status": "erro", "mensagem": str(e)}

__all__ = ["estado", "process_signal", "fechar_posicao_real"]
