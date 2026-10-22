"""Trendfolge (Vorbild: Ed Seykota / Richard Donchian). Zwei Einstiege:
- "cross" (Standard): schneller EMA kreuzt den langsamen nach oben, Kurs über EMA200, RSI zwischen 45 und 70.
- "pullback": im laufenden Aufwärtstrend (EMA schnell > langsam > EMA200, langsame Linie steigt) den Rücksetzer
  an die schnelle EMA kaufen, sobald eine grüne Kerze wieder darüber schließt. Stop unter dem Tief des Rücksetzers.
Ausstieg: festes Ziel (rr x Risiko) oder mit "trail" ein nachgezogener Stop am Tief der letzten n Kerzen
("Gewinne laufen lassen").
"""
from .indicators import atr, ema, rsi


def signal(c, p):
    if len(c) < 210:
        return None
    cl = [x["c"] for x in c]
    fast, slow = p.get("fast", 20), p.get("slow", 50)
    f, s, e200 = ema(cl, fast), ema(cl, slow), ema(cl, 200)
    r, a, i = rsi(cl)[-1], atr(c)[-1], len(c) - 1
    if p.get("mode") == "pullback":
        cur, prev = c[-1], c[-2]
        if not (f[i] > s[i] > e200[i] and s[i] > s[i - 10] and 45 < r < 70):
            return None
        if not (prev["l"] <= f[i - 1] and cur["c"] > f[i] and cur["c"] > cur["o"]):
            return None
        stop = min(x["l"] for x in c[-5:]) - 0.5 * a
        reason = f"Rücksetzer an EMA{fast} im Aufwärtstrend, RSI {r:.0f}"
    else:
        if not (f[i - 1] <= s[i - 1] and f[i] > s[i] and cl[i] > e200[i] and 45 < r < 70):
            return None
        stop = cl[i] - 2 * a
        reason = f"EMA{fast} kreuzt EMA{slow}, RSI {r:.0f}"
    if stop <= 0 or stop >= cl[i]:
        return None
    if p.get("trail"):
        return {"stop": stop, "target": cl[i] * 100, "trail_n": p["trail"], "reason": reason + ", Stop wird nachgezogen"}
    return {"stop": stop, "target": cl[i] + p.get("rr", 2.0) * (cl[i] - stop), "reason": reason}
