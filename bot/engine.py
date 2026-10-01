"""Paper-Trading-Konto: Positionsgröße, Stop-Loss, Take-Profit, Gebühren."""
from . import config as C


def new_account():
    return {
        "start": C.START_BALANCE_EUR,
        "cash": C.START_BALANCE_EUR,
        "peak_equity": C.START_BALANCE_EUR,
        "halted": False,
        "positions": {},
        "trades": [],
        "equity_curve": [],
        "last_signal_t": {},
    }


def equity(acc, prices):
    return acc["cash"] + sum(p["qty"] * prices.get(pair, p["entry"]) for pair, p in acc["positions"].items())


def try_open(acc, pair, sig, price, t, prices):
    """Eröffnet eine Long-Position, wenn Regeln es erlauben. Gibt True zurück bei Kauf."""
    if acc["halted"] or pair in acc["positions"] or len(acc["positions"]) >= C.MAX_OPEN_POSITIONS:
        return False
    fill = price * (1 + C.SLIPPAGE)
    if fill <= sig["stop"] or fill >= sig["target"]:
        return False
    eq = equity(acc, prices)
    risk_unit = fill - sig["stop"]
    qty = (eq * C.RISK_PER_TRADE) / risk_unit
    max_notional = min(eq * C.MAX_POSITION_FRACTION, acc["cash"] / (1 + C.FEE_RATE))
    qty = min(qty, max_notional / fill)
    cost = qty * fill * (1 + C.FEE_RATE)
    if qty <= 0 or cost < 10:  # Mindestorder ~10 €
        return False
    acc["cash"] -= cost
    acc["positions"][pair] = {
        "pair": pair, "qty": qty, "entry": fill, "cost": cost,
        "stop": sig["stop"], "init_stop": sig["stop"], "target": sig["target"],
        "opened_t": t, "checked_t": t, "reason": sig["reason"],
    }
    return True


def _close(acc, pair, price, t, result):
    p = acc["positions"].pop(pair)
    proceeds = p["qty"] * price * (1 - C.FEE_RATE)
    acc["cash"] += proceeds
    pnl = proceeds - p["cost"]
    acc["trades"].append({
        "pair": pair, "entry": p["entry"], "exit": price, "qty": p["qty"],
        "pnl": round(pnl, 2), "pnl_pct": round(pnl / p["cost"] * 100, 2),
        "opened_t": p["opened_t"], "closed_t": t, "result": result, "reason": p["reason"],
    })


def manage(acc, pair, candles):
    """Prüft offene Position gegen Kerzen (älteste zuerst). Konservativ:
    werden Stop und Ziel in derselben Kerze berührt, zählt der Stop."""
    for k in candles:
        p = acc["positions"].get(pair)
        if not p:
            return
        if k["t"] <= p["checked_t"]:
            continue
        if k["l"] <= p["stop"]:
            px = min(p["stop"], k["o"]) * (1 - C.SLIPPAGE)  # Gap nach unten -> schlechterer Kurs
            res = "Einstand" if p["stop"] >= p["entry"] else "Stop-Loss"
            _close(acc, pair, px, k["t"], res)
            return
        if k["h"] >= p["target"]:
            _close(acc, pair, max(p["target"], k["o"]) * (1 - C.SLIPPAGE), k["t"], "Ziel")
            return
        risk = p["entry"] - p["init_stop"]
        if C.BREAKEVEN_AT_R and k["h"] >= p["entry"] + C.BREAKEVEN_AT_R * risk:
            # Stop auf Einstand inkl. Gebühren
            p["stop"] = max(p["stop"], p["entry"] * (1 + 2 * C.FEE_RATE))
        if k.get("closed", True):
            p["checked_t"] = k["t"]


def update_risk_state(acc, prices):
    eq = equity(acc, prices)
    acc["peak_equity"] = max(acc["peak_equity"], eq)
    if eq < acc["peak_equity"] * (1 - C.MAX_DRAWDOWN_STOP):
        acc["halted"] = True
    return eq
