"""SMC – Smart Money Concepts (vereinfacht, nur Long).
Strukturbruch nach oben (BOS) mit Verdrängung (Fair Value Gap) -> erster Retest des Order Blocks
-> Kauf, Stop unter dem Order Block, Ziel = rr x Risiko.
"""
from .indicators import atr, ema


def signal(c, p):
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
