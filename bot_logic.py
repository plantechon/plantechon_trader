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

# 📊 Verifica se há posição real na Binance Futures
def ha_posicao_aberta(par):
    try:
        posicoes = binance.fapiPrivateGetPositionRisk()
        for p in posicoes:
            if p["symbol"] == par.replace("/", "") and abs(float(p["positionAmt"])) > 0:
                return True
        return False
    except Exception as e:
        print(f"[ERRO] Verificação de posição: {e}", flush=True)
        return estado["em_operacao"]  # fallback conservador

# ✅ Executa ordem real
def executar_ordem_real(par, tipo, quantidade, tentativas=3):
    for tentativa in range(1, tentativas + 1):
        try:
            print(f"[EXECUÇÃO] Tentativa {tentativa} - Enviando ordem real...", flush=True)
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

        except ccxt.NetworkError as e:
            if "418" in str(e) or "Too many requests" in str(e):
                print("[ERRO] IP banido temporariamente (418). Aguardando 30s antes de tentar novamente...", flush=True)
                notificar_telegram("⚠️ IP banido pela Binance. Aguardando 30s e tentando novamente...")
                time.sleep(30)
                continue

        except Exception as e:
            notificar_telegram(f"❌ ERRO ao enviar ordem: {e}")
            print(f"[ERRO] Falha ao enviar ordem: {e}", flush=True)
            return None

    notificar_telegram("❌ Todas as tentativas de enviar ordem falharam.")
    print("[ERRO] Falha definitiva ao enviar ordem após várias tentativas.", flush=True)
    return None

# ❌ Fecha posição real
def fechar_posicao_real(par, tipo, quantidade):
    try:
        lado_oposto = "sell" if tipo == "buy" else "buy"
        position_side = "LONG" if tipo == "buy" else "SHORT"

        print(f"[FECHAMENTO] Enviando ordem para fechar {position_side} de {quantidade} {par}", flush=True)

        ordem = binance.create_order(
            symbol=par,
            type="market",
            side=lado_oposto,
            amount=quantidade,
            params={"positionSide": position_side}
        )

        notificar_telegram(f"📉 POSIÇÃO FECHADA: {par} | Lado: {tipo.upper()} | Qtd: {quantidade}")
        print("[FECHAMENTO] Ordem de fechamento enviada com sucesso!", flush=True)
        return ordem

    except Exception as e:
        notificar_telegram(f"❌ ERRO ao fechar posição: {e}")
        print(f"[ERRO] Falha ao fechar posição: {e}", flush=True)
        return None

# 🧠 Processa sinal recebido
def process_signal(data):
    print("[SINAL] Sinal recebido:")
    print(data, flush=True)

    if not estado.get("ativado"):
        print("[STATUS] Bot desativado. Ignorando sinal.", flush=True)
        return {"status": "desativado", "mensagem": "Bot desativado"}

    par = data.get("ativo", "")
    tipo = data.get("tipo", "buy").lower()

    # 🚫 Verificação real de posição na Binance
    if estado["em_operacao"]:
        if not ha_posicao_aberta(par):
            print("[VERIFICAÇÃO] Nenhuma posição real aberta encontrada. Resetando estado.", flush=True)
            estado["em_operacao"] = False
        else:
            notificar_telegram(
                f"⚠️ SINAL IGNORADO (Já em operação)\n📱 Par: {par}\nTipo: {tipo.upper()}"
            )
            return {"status": "em_operacao", "mensagem": "Sinal ignorado pois já está em operação"}

    try:
        entrada = float(data["entrada"])
        risco_percent = float(data.get("risco_percent", 2))
        tp1 = entrada * (1 + float(data.get("tp1_percent", 2)) / 100) if tipo == "buy" else entrada * (1 - float(data.get("tp1_percent", 2)) / 100)
        tp2 = entrada * (1 + float(data.get("tp2_percent", 4)) / 100) if tipo == "buy" else entrada * (1 - float(data.get("tp2_percent", 4)) / 100)
        tp3 = entrada * (1 + float(data.get("tp3_percent", 6)) / 100) if tipo == "buy" else entrada * (1 - float(data.get("tp3_percent", 6)) / 100)
        sl = entrada * (1 - 0.01) if tipo == "buy" else entrada * (1 + 0.01)
        quantidade = calcular_quantidade(par, entrada, risco_percent)

        print("[ORDEM] Par: {} | Entrada: {} | Quantidade: {}".format(par, entrada, quantidade), flush=True)

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
                "quantidade": quantidade
            })
            return {"status": "executado", "mensagem": "Sinal processado e ordem executada"}
        else:
            return {"status": "falha", "mensagem": "Ordem não foi executada"}

    except Exception as e:
        print(f"[ERRO] Problema ao processar sinal: {e}", flush=True)
        notificar_telegram(f"❌ Erro ao processar sinal: {e}")
        return {"status": "erro", "mensagem": str(e)}

__all__ = ["estado", "process_signal", "fechar_posicao_real"]
