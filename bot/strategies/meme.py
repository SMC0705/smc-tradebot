"""Memecoins (Kraken): Momentum-Ausbruch mit Volumen-Explosion, enger Trailing-Stop."""
from .indicators import atr, rsi


def _avg(xs):
    return sum(xs) / len(xs) if xs else 0.0


def signal(c, p):
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
