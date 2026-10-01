"""Die beiden Strategien. Jede bekommt nur ABGESCHLOSSENE Kerzen und gibt ein
Kaufsignal zurück (nur Long, kein Hebel) oder None.

Signal-Format: {"stop": float, "target": float, "reason": str}
"""
from .indicators import ema, rsi, atr

MIN_CANDLES = 210


# ---------------------------------------------------------------------------
# 1) SMC – Smart Money Concepts (vereinfacht, nur Long)
#    Ablauf: Strukturbruch nach oben (BOS) mit Verdrängung (Fair Value Gap)
#    -> Kurs kommt zum ersten Mal in den Order Block zurück und reagiert bullish
#    -> Kauf, Stop unter dem Order Block, Ziel 2,5x Risiko.
# ---------------------------------------------------------------------------
SWING_N = 3          # Fraktal-Breite für Hoch-/Tiefpunkte
BOS_LOOKBACK = 40    # Strukturbruch darf max. so viele Kerzen her sein
SMC_RR = 2.5


def _swing_highs(c, n):
    out = []
    for i in range(n, len(c) - n):
        h = c[i]["h"]
        if all(h >= c[k]["h"] for k in range(i - n, i + n + 1)):
            out.append(i)
    return out


def smc_signal(c):
    if len(c) < MIN_CANDLES:
        return None
    last = len(c) - 1
    closes = [x["c"] for x in c]
    e200 = ema(closes, 200)
    a = atr(c)
    if closes[last] < e200[last]:
        return None  # nur im übergeordneten Aufwärtstrend kaufen

    highs = _swing_highs(c, SWING_N)
    # jüngsten Strukturbruch (BOS) suchen
    bos = None
    for j in range(last - 1, max(last - BOS_LOOKBACK, SWING_N * 2), -1):
        prior = [s for s in highs if s + SWING_N < j]
        if not prior:
            continue
        s = prior[-1]
        level = c[s]["h"]
        if c[j]["c"] > level and c[j - 1]["c"] <= level:
            bos = (s, j, level)
            break
    if not bos:
        return None
    s, j, level = bos

    # Start der Impulsbewegung = tiefstes Tief zwischen Swing-Hoch und Bruch
    lo_i = min(range(s, j + 1), key=lambda k: c[k]["l"])
    # Order Block = letzte rote Kerze am/vor dem Tief
    ob_i = None
    for k in range(lo_i, max(lo_i - 6, 0), -1):
        if c[k]["c"] < c[k]["o"]:
            ob_i = k
            break
    if ob_i is None:
        return None
    zone_lo, zone_hi = c[ob_i]["l"], c[ob_i]["h"]

    # Verdrängung: es muss eine bullische Fair Value Gap im Impuls geben
    if not any(c[k - 2]["h"] < c[k]["l"] for k in range(max(ob_i + 2, 2), j + 1)):
        return None

    # Zone noch gültig und erster Retest genau jetzt
    for k in range(j + 1, last):
        if c[k]["l"] <= zone_hi or c[k]["c"] < zone_lo:
            return None
    cur = c[last]
    if not (cur["l"] <= zone_hi and cur["c"] > zone_lo and cur["c"] > cur["o"]):
        return None

    entry = cur["c"]
    stop = zone_lo - 0.25 * a[last]
    risk = entry - stop
    if risk <= 0 or risk / entry > 0.06 or risk / entry < 0.003:
        return None
    return {
        "stop": stop,
        "target": entry + SMC_RR * risk,
        "reason": f"BOS über {level:.4g}, Retest Order Block {zone_lo:.4g}–{zone_hi:.4g}",
    }


# ---------------------------------------------------------------------------
# 2) Trendfolge – EMA20 kreuzt EMA50 nach oben, Kurs über EMA200, RSI ok
# ---------------------------------------------------------------------------
def trend_signal(c):
    if len(c) < MIN_CANDLES:
        return None
    closes = [x["c"] for x in c]
    e20, e50, e200 = ema(closes, 20), ema(closes, 50), ema(closes, 200)
    r = rsi(closes)
    a = atr(c)
    i = len(c) - 1
    crossed = e20[i - 1] <= e50[i - 1] and e20[i] > e50[i]
    if not (crossed and closes[i] > e200[i] and 45 < r[i] < 70):
        return None
    entry = closes[i]
    stop = entry - 2 * a[i]
    if stop <= 0:
        return None
    return {
        "stop": stop,
        "target": entry + 4 * a[i],
        "reason": f"EMA20 kreuzt EMA50, RSI {r[i]:.0f}",
    }


SIGNALS = {"smc": smc_signal, "trend": trend_signal}
NAMES = {"smc": "SMC", "trend": "Trendfolge"}
