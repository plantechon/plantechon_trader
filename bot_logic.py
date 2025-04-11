import os
import time
import ccxt
from datetime import datetime
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
    "timeframe": "",
    "trailing_ativo": False,
    "trailing_offset": 0.0
}

# 🔧 Cálculo de posição
def calcular_quantidade(ativo, preco_entrada, risco_percent=2, alavancagem=5):
    saldo = 50
    valor_total = saldo * alavancagem
    quantidade = valor_total / float(preco_entrada)
    return round(quantidade, 3)

# ✅ Verifica se a posição foi realmente aberta usando fetch_balance
def verificar_posicao_ativa(par, tipo, tentativas=3):
    symbol = par.replace("/", "")
    for tentativa in range(tentativas):
        try:
            time.sleep(2)
            balance = binance.fetch_balance({'type': 'future'})
            positions = balance.get('info', {}).get('positions', [])
            for pos in positions:
                if pos['symbol'] == symbol:
                    amt = float(pos.get('positionAmt', 0))
                    if (tipo == "buy" and amt > 0) or (tipo == "sell" and amt < 0):
                        return True
        except Exception as e:
            print(f"[ERRO] Verificação de posição (fallback): {e}", flush=True)
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
            time.sleep(2)
            if verificar_posicao_ativa(par, tipo):
                print("[EXECUÇÃO] Ordem enviada com sucesso!", flush=True)
                return True
            else:
                notificar_telegram("⚠️ Ordem enviada, mas nenhuma posição ativa encontrada na Binance.")
                print("[ERRO] Ordem enviada, mas nenhuma posição ativa encontrada.", flush=True)
        except Exception as e:
            print(f"[ERRO] Falha ao executar ordem real: {e}", flush=True)
    return False

# 🚪 Fecha posição real
def fechar_posicao_real(par, tipo, quantidade):
    try:
        side = "sell" if tipo == "buy" else "buy"
        position_side = "LONG" if tipo == "buy" else "SHORT"
        binance.create_order(
            symbol=par,
            type="market",
            side=side,
            amount=quantidade,
            params={"positionSide": position_side}
        )
        print(f"[ENCERRAMENTO] Posição fechada: {par} | Tipo: {tipo.upper()} | Quantidade: {quantidade}", flush=True)
    except Exception as e:
        print(f"[ERRO] Falha ao fechar posição: {e}", flush=True)

# 📈 Atualiza SL com trailing stop dinâmico
def atualizar_trailing_stop(preco_atual):
    if not estado["trailing_ativo"]:
        return
    tipo = estado["tipo"]
    offset = estado["trailing_offset"]
    if tipo == "buy":
        novo_sl = preco_atual - offset
        if novo_sl > estado["sl"]:
            estado["sl"] = novo_sl
            notificar_telegram(f"🔁 SL atualizado com trailing: {estado['sl']:.2f}")
    elif tipo == "sell":
        novo_sl = preco_atual + offset
        if novo_sl < estado["sl"]:
            estado["sl"] = novo_sl
            notificar_telegram(f"🔁 SL atualizado com trailing: {estado['sl']:.2f}")

# 🧠 Processa o sinal recebido
def process_signal(data):
    try:
        print("[SINAL] Sinal recebido:")
        print(data)

        tipo = data["tipo"].lower()
        ativo = data["ativo"].replace(" ", "")
        entrada = float(data["entrada"])
        risco_percent = float(data.get("risco_percent", 2))
        tp1_percent = float(data.get("tp1_percent", 2))
        tp2_percent = float(data.get("tp2_percent", 4))
        tp3_percent = float(data.get("tp3_percent", 6))
        timeframe = data.get("timeframe", "")
        trailing_offset = float(data.get("trailing_offset", 0))

        quantidade = calcular_quantidade(ativo, entrada, risco_percent)
        print(f"[ORDEM] Par: {ativo} | Entrada: {entrada} | Quantidade: {quantidade}")

        estado.update({
            "em_operacao": True,
            "par": ativo,
            "entrada": entrada,
            "tp1": entrada * (1 + tp1_percent/100) if tipo == "buy" else entrada * (1 - tp1_percent/100),
            "tp2": entrada * (1 + tp2_percent/100) if tipo == "buy" else entrada * (1 - tp2_percent/100),
            "tp3": entrada * (1 + tp3_percent/100) if tipo == "buy" else entrada * (1 - tp3_percent/100),
            "sl": entrada * (1 - risco_percent/100) if tipo == "buy" else entrada * (1 + risco_percent/100),
            "tipo": tipo,
            "quantidade": quantidade,
            "hora_ultima_checagem": time.time(),
            "timeframe": timeframe,
            "trailing_ativo": trailing_offset > 0,
            "trailing_offset": trailing_offset
        })

        emoji = "🟢" if tipo == "buy" else "🔴"
        hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        notificar_telegram(
            f"📡 Novo sinal recebido!\n\n"
            f"🪙 Ativo: {ativo}\n"
            f"{emoji} Tipo: {'COMPRA' if tipo == 'buy' else 'VENDA'}\n"
            f"💰 Entrada: {entrada:.2f}\n"
            f"🎯 TP1: 🎯 {estado['tp1']:.2f}\n"
            f"🎯 TP2: 🎯 {estado['tp2']:.2f}\n"
            f"🎯 TP3: 🎯 {estado['tp3']:.2f}\n"
            f"🛑 Stop Loss: {estado['sl']:.2f}\n"
            f"📉 Trailing: {trailing_offset if trailing_offset > 0 else 'Desativado'}\n"
            f"🕒 Timeframe: {timeframe.upper()}\n"
            f"📅 Horário: {hora}"
        )

        sucesso = executar_ordem_real(ativo, tipo, quantidade)
        return {"status": "ok" if sucesso else "erro", "mensagem": "Sinal processado"}

    except Exception as e:
        print(f"[ERRO] Falha ao processar sinal: {e}", flush=True)
        return {"status": "erro", "mensagem": str(e)}
