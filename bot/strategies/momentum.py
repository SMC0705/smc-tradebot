"""Momentum für den Krisen-Bot (Stunden-Kerzen): Kauf beim Ausbruch über das Hoch der letzten n Stunden,
wenn EMA20 über EMA50 liegt. Stop 2 × ATR, danach nachgezogen am Tief der letzten Kerzen.
Ob überhaupt gekauft werden darf, entscheidet der Nachrichten-Analyst (passendes Krisen-Thema aktiv).
"""
from .indicators import atr, ema


def signal(c, p):
    n = p.get("n", 24)
    if len(c) < max(60, n + 2):
        return None
    cl = [x["c"] for x in c]
    hi = max(x["h"] for x in c[-n - 1:-1])
    if not (cl[-1] > hi and cl[-1] > ema(cl, 20)[-1] > ema(cl, 50)[-1]):
        return None
    stop = cl[-1] - 2 * atr(c)[-1]
    if stop <= 0:
        return None
    return {"stop": stop, "target": cl[-1] * 10, "trail_n": p.get("trail", 12), "max_hold": p.get("hold", 168),
            "reason": f"Momentum: {n}-Stunden-Hoch gebrochen"}
