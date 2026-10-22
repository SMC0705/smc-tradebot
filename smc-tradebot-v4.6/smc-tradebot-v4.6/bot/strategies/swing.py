"""Swing nach den Turtle-Regeln (Richard Dennis, 1983): Kauf beim Ausbruch über das n-Tage-Hoch
(System 1: 20 Tage, System 2: 55 Tage), Stop 2 x ATR ("2N"), Ausstieg wenn das Tief der letzten
Tage unterschritten wird (Trailing). Nur über EMA50 (Trendfilter).
"""
from .indicators import atr, ema


def signal(c, p):
    n = p.get("n", 20)
    if len(c) < max(60, n + 2):
        return None
    cl = [x["c"] for x in c]
    hi = max(x["h"] for x in c[-n - 1:-1])
    cur = c[-1]
    if not (cur["c"] > hi and cur["c"] > ema(cl, 50)[-1]):
        return None
    stop = cur["c"] - 2 * atr(c)[-1]
    if stop <= 0:
        return None
    return {"stop": stop, "target": cur["c"] * 100, "trail_n": p.get("trail", 10),
            "reason": f"{n}-Tage-Hoch gebrochen"}
