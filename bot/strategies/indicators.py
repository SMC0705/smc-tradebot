"""Technische Indikatoren (reines Python, keine Zusatzpakete). Alle Funktionen geben eine Liste
in gleicher Länge wie die Eingabe zurück (außer adx: nur der letzte Wert)."""


def sma(values, period):
    """Einfacher gleitender Durchschnitt (am Anfang über die vorhandenen Werte)."""
    out, s = [], 0.0
    for i, v in enumerate(values):
        s += v
        if i >= period:
            s -= values[i - period]
        out.append(s / min(i + 1, period))
    return out


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


def adx(c, n=14):
    """Trendstärke nach Wilder (0–100). Über 20–25 = klarer Trend, darunter = Seitwärtsmarkt."""
    if len(c) < 2 * n + 2:
        return 0.0
    tr, pdm, mdm = [], [], []
    for i in range(1, len(c)):
        up, dn = c[i]["h"] - c[i - 1]["h"], c[i - 1]["l"] - c[i]["l"]
        pdm.append(up if up > dn and up > 0 else 0.0)
        mdm.append(dn if dn > up and dn > 0 else 0.0)
        tr.append(max(c[i]["h"] - c[i]["l"], abs(c[i]["h"] - c[i - 1]["c"]), abs(c[i]["l"] - c[i - 1]["c"])))

    def wilder(xs):
        s = sum(xs[:n])
        out = [s]
        for x in xs[n:]:
            s = s - s / n + x
            out.append(s)
        return out

    dx = []
    for t, p, m in zip(wilder(tr), wilder(pdm), wilder(mdm)):
        pdi, mdi = (100 * p / t, 100 * m / t) if t else (0.0, 0.0)
        dx.append(100 * abs(pdi - mdi) / (pdi + mdi) if pdi + mdi else 0.0)
    a = sum(dx[:n]) / n
    for x in dx[n:]:
        a = (a * (n - 1) + x) / n
    return a
