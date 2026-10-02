"""Trendfolge: schneller EMA kreuzt langsamen nach oben, Kurs über EMA200, RSI zwischen 45 und 70.
Klassische Trendfolge nach dem Vorbild von Ed Seykota / Richard Donchian.
"""
from .indicators import atr, ema, rsi


def signal(c, p):
    if len(c) < 210:
        return None
    cl = [x["c"] for x in c]
    f, s, e200 = ema(cl, p.get("fast", 20)), ema(cl, p.get("slow", 50)), ema(cl, 200)
    r, a, i = rsi(cl)[-1], atr(c)[-1], len(c) - 1
    if not (f[i - 1] <= s[i - 1] and f[i] > s[i] and cl[i] > e200[i] and 45 < r < 70):
        return None
    stop = cl[i] - 2 * a
    if stop <= 0:
        return None
    return {"stop": stop, "target": cl[i] + p.get("rr", 2.0) * 2 * a,
            "reason": f"EMA{p.get('fast', 20)} kreuzt EMA{p.get('slow', 50)}, RSI {r:.0f}"}
