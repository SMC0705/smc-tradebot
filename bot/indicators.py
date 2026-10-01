"""Technische Indikatoren (reines Python, keine Zusatzpakete)."""


def ema(values, period):
    out, k, prev = [], 2 / (period + 1), None
    for v in values:
        prev = v if prev is None else v * k + prev * (1 - k)
        out.append(prev)
    return out


def rsi(closes, period=14):
    out = [50.0] * len(closes)
    if len(closes) <= period:
        return out
    gains = losses = 0.0
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        gains += max(d, 0)
        losses += max(-d, 0)
    ag, al = gains / period, losses / period
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        ag = (ag * (period - 1) + max(d, 0)) / period
        al = (al * (period - 1) + max(-d, 0)) / period
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def atr(candles, period=14):
    trs = []
    for i, c in enumerate(candles):
        if i == 0:
            trs.append(c["h"] - c["l"])
        else:
            pc = candles[i - 1]["c"]
            trs.append(max(c["h"] - c["l"], abs(c["h"] - pc), abs(c["l"] - pc)))
    out, prev = [], None
    for i, tr in enumerate(trs):
        prev = tr if prev is None else (prev * (period - 1) + tr) / period
        out.append(prev)
    return out
