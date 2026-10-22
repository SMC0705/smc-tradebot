"""Daytrading (15-Minuten-Kerzen). Alle Positionen werden spätestens zum Tagesende (UTC) geschlossen.

Modus "range" (Standard): Ausbruch über das Hoch der letzten n Kerzen mit erhöhtem Volumen, über EMA50.
Modus "williams": Volatilitäts-Ausbruch nach Larry Williams – Kauf, sobald der Kurs über
  Tageseröffnung + k × Spanne des Vortags steigt (k = 0,5 … 0,7).
"""
from .indicators import atr, ema


def _avg(xs):
    return sum(xs) / len(xs) if xs else 0.0


def signal(c, p):
    if p.get("mode") == "williams":
        return _williams(c, p)
    n = p.get("range", 16)
    if len(c) < max(60, n + 22):
        return None
    cl = [x["c"] for x in c]
    hi = max(x["h"] for x in c[-n - 1:-1])
    cur, prev = c[-1], c[-2]
    vol_ok = cur["v"] > p.get("vol", 1.5) * _avg([x["v"] for x in c[-21:-1]])
    if not (cur["c"] > hi >= prev["c"] and vol_ok and cur["c"] > ema(cl, 50)[-1]):
        return None
    return _order(c, p, f"Ausbruch über {n}-Kerzen-Hoch mit Volumen")


def _williams(c, p):
    if len(c) < 150:
        return None
    cur = c[-1]
    day0 = cur["t"] - cur["t"] % 86400
    today = [x for x in c if x["t"] >= day0]
    prev_day = [x for x in c if day0 - 86400 <= x["t"] < day0]
    if not today or len(prev_day) < 48:          # Vortag muss (fast) vollständig sein
        return None
    rng = max(x["h"] for x in prev_day) - min(x["l"] for x in prev_day)
    level = today[0]["o"] + p.get("k", 0.5) * rng
    before = c[-2]["c"] if len(today) > 1 else today[0]["o"]
    if not (cur["c"] > level >= before):
        return None
    return _order(c, p, f"Williams-Ausbruch (Eröffnung + {p.get('k', 0.5)} × Vortagesspanne)")


def _order(c, p, reason):
    entry, a = c[-1]["c"], atr(c)[-1]
    stop = entry - 1.5 * a
    if stop <= 0 or (entry - stop) / entry < 0.004:
        return None
    return {"stop": stop, "target": entry + p.get("rr", 2.0) * (entry - stop), "eod": True, "reason": reason}
