"""Scalping (5-Minuten-Kerzen): Rücksetzer an die EMA21 im kurzfristigen Aufwärtstrend.
Variante mit "adx_min" = "Holy Grail" von Linda Raschke: nur handeln, wenn der Trend stark ist (ADX > 30).
Ziel muss deutlich über den Gebühren liegen (min_stop), sonst lohnt sich der Trade nicht.
"""
from .indicators import adx, atr, ema, rsi


def signal(c, p):
    if len(c) < 60:
        return None
    cl = [x["c"] for x in c]
    e9, e21, e50 = ema(cl, 9), ema(cl, 21), ema(cl, 50)
    i, cur, prev = len(c) - 1, c[-1], c[-2]
    if not (e9[i] > e21[i] > e50[i]):
        return None
    if not (prev["l"] <= e21[i - 1] and cur["c"] > e9[i] and cur["c"] > cur["o"] and rsi(cl)[-1] > 50):
        return None
    if p.get("adx_min") and adx(c[-120:]) < p["adx_min"]:
        return None
    entry = cur["c"]
    stop = min(x["l"] for x in c[-4:]) - 0.1 * atr(c)[-1]
    risk = entry - stop
    if risk <= 0 or risk / entry < p.get("min_stop", 0.004) or risk / entry > 0.02:
        return None
    return {"stop": stop, "target": entry + p.get("rr", 1.5) * risk, "max_hold": p.get("hold", 24),
            "reason": "Rücksetzer an EMA21 im Aufwärtstrend" + (" (starker Trend)" if p.get("adx_min") else "")}
