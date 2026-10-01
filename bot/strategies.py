"""Alle Strategien. Jede bekommt ABGESCHLOSSENE Kerzen (älteste zuerst) und ein
Parameter-Set und gibt ein Kaufsignal zurück (nur Long, kein Hebel) oder None.

Signal: {"stop", "target", "reason", optional "trail_n", "max_hold", "eod"}
Eingestiegen wird immer erst zum Eröffnungskurs der NÄCHSTEN Kerze (kein Blick in die Zukunft).
"""
from .indicators import ema, rsi, atr

WINDOW = 260  # so viele Kerzen bekommt jede Strategie


def _avg(xs):
    return sum(xs) / len(xs) if xs else 0.0


# 1) SMC – Strukturbruch + Fair Value Gap -> erster Retest des Order Blocks
def smc(c, p):
    n_sw, look, rr = 3, 40, p.get("rr", 2.5)
    if len(c) < 210:
        return None
    last = len(c) - 1
    closes = [x["c"] for x in c]
    if closes[last] < ema(closes, 200)[last]:
        return None
    a = atr(c)[last]
    highs = [i for i in range(n_sw, len(c) - n_sw)
             if all(c[i]["h"] >= c[k]["h"] for k in range(i - n_sw, i + n_sw + 1))]
    bos = None
    for j in range(last - 1, max(last - look, n_sw * 2), -1):
        prior = [s for s in highs if s + n_sw < j]
        if prior:
            s = prior[-1]
            lvl = c[s]["h"]
            if c[j]["c"] > lvl >= c[j - 1]["c"]:
                bos = (s, j, lvl)
                break
    if not bos:
        return None
    s, j, lvl = bos
    lo_i = min(range(s, j + 1), key=lambda k: c[k]["l"])
    ob = next((k for k in range(lo_i, max(lo_i - 6, 0), -1) if c[k]["c"] < c[k]["o"]), None)
    if ob is None:
        return None
    z_lo, z_hi = c[ob]["l"], c[ob]["h"]
    if not any(c[k - 2]["h"] < c[k]["l"] for k in range(max(ob + 2, 2), j + 1)):
        return None
    if any(c[k]["l"] <= z_hi or c[k]["c"] < z_lo for k in range(j + 1, last)):
        return None
    cur = c[last]
    if not (cur["l"] <= z_hi and cur["c"] > z_lo and cur["c"] > cur["o"]):
        return None
    entry, stop = cur["c"], z_lo - 0.25 * a
    risk = entry - stop
    if risk <= 0 or not 0.003 < risk / entry < 0.06:
        return None
    return {"stop": stop, "target": entry + rr * risk,
            "reason": f"BOS über {lvl:.5g}, Retest Order Block"}


# 2) Trendfolge – schneller EMA kreuzt langsamen nach oben, über EMA200, RSI ok
def trend(c, p):
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


# 3) Scalping – Rücksetzer an EMA21 im kurzfristigen Aufwärtstrend
def scalp(c, p):
    if len(c) < 60:
        return None
    cl = [x["c"] for x in c]
    e9, e21, e50 = ema(cl, 9), ema(cl, 21), ema(cl, 50)
    i, cur, prev = len(c) - 1, c[-1], c[-2]
    if not (e9[i] > e21[i] > e50[i]):
        return None
    if not (prev["l"] <= e21[i - 1] and cur["c"] > e9[i] and cur["c"] > cur["o"] and rsi(cl)[-1] > 50):
        return None
    entry = cur["c"]
    stop = min(x["l"] for x in c[-4:]) - 0.1 * atr(c)[-1]
    risk = entry - stop
    if risk <= 0 or risk / entry < p.get("min_stop", 0.004) or risk / entry > 0.02:
        return None  # Ziel muss deutlich über den Gebühren liegen
    return {"stop": stop, "target": entry + p.get("rr", 1.5) * risk, "max_hold": p.get("hold", 24),
            "reason": "Rücksetzer an EMA21 im Aufwärtstrend"}


# 4) Daytrading – Ausbruch aus der Spanne der letzten Stunden mit Volumen, Schluss am Tagesende
def day(c, p):
    n = p.get("range", 16)
    if len(c) < max(60, n + 22):
        return None
    cl = [x["c"] for x in c]
    rng = c[-n - 1:-1]
    hi = max(x["h"] for x in rng)
    cur, prev = c[-1], c[-2]
    vol_ok = cur["v"] > p.get("vol", 1.5) * _avg([x["v"] for x in c[-21:-1]])
    if not (cur["c"] > hi >= prev["c"] and vol_ok and cur["c"] > ema(cl, 50)[-1]):
        return None
    entry, a = cur["c"], atr(c)[-1]
    stop = entry - 1.5 * a
    if stop <= 0 or (entry - stop) / entry < 0.004:
        return None
    return {"stop": stop, "target": entry + p.get("rr", 2.0) * (entry - stop), "eod": True,
            "reason": f"Ausbruch über {n}-Kerzen-Hoch mit Volumen"}


# 5) Swing (Tageskerzen) – Donchian-Ausbruch, Nachziehen des Stops am n-Tage-Tief
def swing(c, p):
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


# 6) Memecoins – Momentum-Ausbruch mit Volumen-Explosion, enger Trailing-Stop
def meme(c, p):
    n = p.get("n", 24)
    if len(c) < max(60, n + 22):
        return None
    cl = [x["c"] for x in c]
    cur = c[-1]
    hi = max(x["h"] for x in c[-n - 1:-1])
    vol_ok = cur["v"] > p.get("vol", 2.0) * _avg([x["v"] for x in c[-21:-1]])
    r = rsi(cl)[-1]
    if not (cur["c"] > hi and vol_ok and 55 < r < 85 and cur["c"] > cur["o"]):
        return None
    entry, a = cur["c"], atr(c)[-1]
    stop = entry - 1.5 * a
    if stop <= 0 or (entry - stop) / entry > 0.12:
        return None
    return {"stop": stop, "target": entry + p.get("rr", 3.0) * (entry - stop), "trail_n": 8,
            "max_hold": 96, "reason": f"Ausbruch mit {cur['v'] / max(_avg([x['v'] for x in c[-21:-1]]), 1e-12):.1f}x Volumen"}


SIGNALS = {"smc": smc, "trend": trend, "scalp": scalp, "day": day, "swing": swing, "meme": meme}
