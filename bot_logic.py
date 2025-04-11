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
    "ativado": True,
    "timeframe": ""
}

# 🔧 Cálculo de posição
def calcular_quantidade(ativo, preco_entrada, risco_percent=2, alavancagem=5):
    saldo = 50
    valor_total = saldo * alavancagem
    quantidade = valor_total / float(preco_entrada)
    return round(quantidade, 3)

# ✅ Executa ordem real com verificação
def executar_ordem_real(par, tipo, quantidade, tentativas=3):
    for tentativa in range(1, tentativas + 1):
        try:
            print(f"[EXECUÇÃO] Tentativa {tentativa} - Enviando ordem real...")
            print(f"Par: {par} | Tipo: {tipo.upper()} | Quantidade: {quantidade}")

            side = "buy" if tipo == "buy" else "sell"
            position_side = "LONG" if tipo == "buy" else "SHORT"

            ordem = binance.create_order(
                symbol=par,
                type="market",
                side=side,
                amount=quantidade,
                params={"positionSide": position_side}
            )

            # Verifica posição na Binance Futures após a execução
            try:
                posicoes = binance.fapiPrivateGetPositionRisk()
                ativo_formatado = par.replace("/", "")
                ativos_com_posicao = [
                    p for p in posicoes if float(p['positionAmt']) != 0 and p['symbol'] == ativo_formatado
                ]
                if not ativos_com_posicao:
                    notificar_telegram("⚠️ Ordem enviada, mas nenhuma posição ativa encontrada na Binance Futures.")
                    print("[ERRO] Ordem enviada, mas nenhuma posição ativa encontrada.")
                else:
                    print("[✅] Posição confirmada com sucesso.")
            except Exception as e:
                notificar_telegram(f"⚠️ Erro ao verificar posição: {e}")
                print(f"[ERRO] Verificação de posição: {e}")

            return ordem

        except ccxt.NetworkError as e:
            if "418" in str(e) or "Too many requests" in str(e):
                print("[ERRO] IP banido temporariamente (418). Aguardando 30s...")
                notificar_telegram("⚠️ IP banido pela Binance. Aguardando 30s...")
                time.sleep(30)
                continue

        except Exception as e:
            notificar_telegram(f"❌ ERRO ao enviar ordem: {e}")
            print(f"[ERRO] Falha ao enviar ordem: {e}")
            return None

    notificar_telegram("❌ Todas as tentativas de envio de ordem falharam.")
    return None

# ❌ Fechar posição real
def fechar_posicao_real(par, tipo, quantidade):
    try:
        lado_oposto = "sell" if tipo == "buy" else "buy"
        position_side = "LONG" if tipo == "buy" else "SHORT"

        print(f"[FECHAMENTO] Fechando {position_side} de {quantidade} {par}")
        ordem = binance.create_order(
            symbol=par,
            type="market",
            side=lado_oposto,
            amount=quantidade,
            params={"positionSide": position_side}
        )

        notificar_telegram(f"📉 POSIÇÃO FECHADA: {par} | Lado: {tipo.upper()} | Qtd: {quantidade}")
        return ordem

    except Exception as e:
        notificar_telegram(f"❌ ERRO ao fechar posição: {e}")
        print(f"[ERRO] Fechamento falhou: {e}")
        return None

# 🧠 Processa sinal
def process_signal(data):
    print("[SINAL] Sinal recebido:")
    print(data)

    if not estado.get("ativado"):
        return {"status": "desativado", "mensagem": "Bot desativado"}

    if estado["em_operacao"]:
        return {"status": "em_operacao", "mensagem": "Sinal ignorado (já em operação)"}

    try:
        par = data["ativo"]
        entrada = float(data["entrada"])
        tipo = data["tipo"].lower()
        risco_percent = float(data.get("risco_percent", 2))
        timeframe = data.get("timeframe", "")

        tp1 = entrada * (1 + 0.02) if tipo == "buy" else entrada * (1 - 0.02)
        tp2 = entrada * (1 + 0.04) if tipo == "buy" else entrada * (1 - 0.04)
        tp3 = entrada * (1 + 0.06) if tipo == "buy" else entrada * (1 - 0.06)
        sl = entrada * (1 - 0.01) if tipo == "buy" else entrada * (1 + 0.01)

        quantidade = calcular_quantidade(par, entrada, risco_percent)

        resultado = executar_ordem_real(par, tipo, quantidade)
        if resultado:
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

            emoji_tipo = "🟢" if tipo == "buy" else "🔴"
            msg = (
                f"{emoji_tipo} *ORDEM EXECUTADA!*\n"
                f"📊 Par: *{par}*\n"
                f"{emoji_tipo} Tipo: *{tipo.upper()}*\n"
                f"💰 Qtd: *{quantidade}*\n"
                f"🎯 Entrada: *{entrada:.2f}*\n"
                f"📈 TP1: *{tp1:.2f}* | TP2: *{tp2:.2f}* | TP3: *{tp3:.2f}*\n"
                f"🛑 SL: *{sl:.2f}*\n"
                f"⏱️ Timeframe: *{timeframe.upper()}*"
            )
            notificar_telegram(msg)
            return {"status": "executado", "mensagem": "Sinal processado e ordem executada"}

        return {"status": "falha", "mensagem": "Ordem não foi executada"}

    except Exception as e:
        print(f"[ERRO] Falha ao processar sinal: {e}")
        notificar_telegram(f"❌ Erro ao processar sinal: {e}")
        return {"status": "erro", "mensagem": str(e)}

__all__ = ["estado", "process_signal", "fechar_posicao_real"]
