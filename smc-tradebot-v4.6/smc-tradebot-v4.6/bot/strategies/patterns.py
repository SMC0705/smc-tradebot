"""MUSTER-BIBLIOTHEK: die bekanntesten Kerzen- und Chartmuster.

Jedes Kaufmuster liefert Stop und Ziel aus seiner eigenen Geometrie (z. B. Flaggenmast, Höhe des
Doppelbodens). Warnmuster (bärisch) werden nicht gehandelt – sie bremsen andere Käufe.
Welche Muster bei welchem Bot wirklich funktionieren, findet das Lern-Modul selbst heraus
(brain/learning.py): Jeder Bot testet ALLE Muster in einem Schattenkonto und handelt echt nur die,
die sich nach Gebühren bewährt haben.

Alle Funktionen bekommen abgeschlossene Kerzen (älteste zuerst) und schauen nie in die Zukunft.
"""
from .indicators import atr, ema, rsi, sma

LABELS = {
    # Kaufmuster
    "double_bottom": "Doppelboden (W)", "inv_head_shoulders": "Umgek. Schulter-Kopf-Schulter",
    "bull_flag": "Bullen-Flagge", "asc_triangle": "Aufsteigendes Dreieck", "breakout_retest": "Ausbruch + Retest",
    "rsi_divergence": "Bullische RSI-Divergenz", "bb_squeeze": "Bollinger-Squeeze-Ausbruch",
    "inside_bar": "Inside-Bar-Ausbruch", "morning_star": "Morgenstern", "three_soldiers": "Drei weiße Soldaten",
    "engulfing": "Bullisches Engulfing", "hammer": "Hammer",
    # Warnmuster
    "double_top": "Doppeltop (M)", "head_shoulders": "Schulter-Kopf-Schulter", "bear_engulfing": "Bärisches Engulfing",
    "shooting_star": "Sternschnuppe", "evening_star": "Abendstern", "three_crows": "Drei schwarze Krähen",
    "rsi_bear_divergence": "Bärische RSI-Divergenz",
}
WINDOW = 120   # Muster brauchen keine lange Vorgeschichte


# --- Hilfen -------------------------------------------------------------------------
def _body(k):
    return abs(k["c"] - k["o"])


def _range(k):
    return max(k["h"] - k["l"], 1e-12)


def _swings(c, kind, n=3):
    """Indizes bestätigter Tief-/Hochpunkte (n Kerzen links und rechts niedriger/höher)."""
    key = "l" if kind == "low" else "h"
    out = []
    for i in range(n, len(c) - n):
        v = c[i][key]
        seg = [c[j][key] for j in range(i - n, i + n + 1)]
        if (kind == "low" and v <= min(seg)) or (kind == "high" and v >= max(seg)):
            out.append(i)
    return out


def _ctx(c):
    cl = [x["c"] for x in c]
    return {"cl": cl, "atr": atr(c)[-1], "e20": ema(cl, 20), "e50": ema(cl, 50), "rsi": rsi(cl),
            "lows": _swings(c, "low"), "highs": _swings(c, "high")}


def _order(c, stop, target, name, a, max_r=4.0):
    entry = c[-1]["c"]
    stop -= 0.1 * a
    if not (0 < stop < entry < target):
        return None
    target = min(target, entry + max_r * (entry - stop))   # unrealistische Ziele kappen
    return {"stop": stop, "target": target, "pattern": name, "reason": f"Muster: {LABELS[name]}"}


def _rr(c, stop, name, a, rr=2.0):
    entry = c[-1]["c"]
    return _order(c, stop, entry + rr * (entry - (stop - 0.1 * a)), name, a)


# --- Kaufmuster: Chartformationen ---------------------------------------------------------
def double_bottom(c, x):
    lows = [i for i in x["lows"] if i >= len(c) - 40]
    if len(lows) < 2:
        return None
    i1, i2 = lows[-2], lows[-1]
    l1, l2 = c[i1]["l"], c[i2]["l"]
    if i2 - i1 < 5 or abs(l2 - l1) / l1 > 0.015 or i2 < len(c) - 15:
        return None
    neck = max(k["h"] for k in c[i1:i2 + 1])
    if neck - min(l1, l2) < 2 * x["atr"] or not (c[-1]["c"] > neck >= c[-2]["c"]):
        return None
    low = min(l1, l2)
    return _order(c, low, neck + (neck - low), "double_bottom", x["atr"])


def inv_head_shoulders(c, x):
    lows = [i for i in x["lows"] if i >= len(c) - 60]
    if len(lows) < 3:
        return None
    i1, i2, i3 = lows[-3:]
    ls, hd, rs = c[i1]["l"], c[i2]["l"], c[i3]["l"]
    if not (hd < min(ls, rs) - 0.5 * x["atr"] and abs(ls - rs) / ls <= 0.03):
        return None
    neck = max(max(k["h"] for k in c[i1:i2 + 1]), max(k["h"] for k in c[i2:i3 + 1]))
    if not (c[-1]["c"] > neck >= c[-2]["c"]):
        return None
    return _order(c, rs, neck + (neck - hd), "inv_head_shoulders", x["atr"])


def bull_flag(c, x):
    a = x["atr"]
    seg = c[-16:-3]
    ph = len(c) - 16 + max(range(len(seg)), key=lambda j: seg[j]["h"])   # Spitze des Fahnenmasts
    start = min(range(max(ph - 8, 0), ph + 1), key=lambda j: c[j]["l"])
    pole = c[ph]["h"] - c[start]["l"]
    flag = c[ph + 1:-1]
    if pole < 3 * a or not 3 <= len(flag) <= 12:
        return None
    f_hi, f_lo = max(k["h"] for k in flag), min(k["l"] for k in flag)
    if f_hi - f_lo > 0.5 * pole or f_lo < c[start]["l"] + 0.4 * pole or f_hi > c[ph]["h"]:
        return None
    if not (c[-1]["c"] > f_hi and c[-1]["c"] > c[-1]["o"]):
        return None
    return _order(c, f_lo, c[-1]["c"] + pole, "bull_flag", a)


def asc_triangle(c, x):
    win = c[-31:-1]
    res = max(k["h"] for k in win)
    base = len(c) - 31
    touches = [i for i in x["highs"] if i >= base and c[i]["h"] >= res * 0.995]
    lows = [i for i in x["lows"] if i >= base]
    if len(touches) < 2 or len(lows) < 2 or not all(c[a]["l"] < c[b]["l"] for a, b in zip(lows, lows[1:])):
        return None
    if not (c[-1]["c"] > res >= c[-2]["c"]):
        return None
    return _order(c, c[lows[-1]]["l"], c[-1]["c"] + (res - c[lows[0]]["l"]), "asc_triangle", x["atr"])


def breakout_retest(c, x):
    level = max(k["h"] for k in c[-40:-12])
    broke = any(k["c"] > level * 1.002 for k in c[-12:-3])
    cur = c[-1]
    if not (broke and cur["l"] <= level * 1.003 and cur["c"] > level and cur["c"] > cur["o"]):
        return None
    return _rr(c, min(cur["l"], c[-2]["l"]), "breakout_retest", x["atr"], 2.5)


def rsi_divergence(c, x):
    lows = [i for i in x["lows"] if i >= len(c) - 40]
    if len(lows) < 2:
        return None
    i1, i2 = lows[-2], lows[-1]
    r = x["rsi"]
    if not (c[i2]["l"] < c[i1]["l"] and r[i2] > r[i1] + 3 and i2 >= len(c) - 8 and r[i2] < 45):
        return None
    if not (c[-1]["c"] > c[-1]["o"] and c[-1]["c"] > c[-2]["h"]):
        return None
    return _rr(c, c[i2]["l"], "rsi_divergence", x["atr"])


def bb_squeeze(c, x):
    cl = x["cl"]
    if len(cl) < 120:
        return None
    mid = sma(cl, 20)
    widths = []
    for i in range(len(cl) - 100, len(cl)):
        w = cl[i - 19:i + 1]
        m = sum(w) / 20
        sd = (sum((v - m) ** 2 for v in w) / 20) ** 0.5
        widths.append((4 * sd / m, m + 2 * sd))
    prev_w = widths[-2][0]
    if prev_w > sorted(w for w, _ in widths)[10] or cl[-1] <= widths[-1][1]:
        return None   # vorher keine Enge (unterste 10 %) oder kein Ausbruch über das obere Band
    return _rr(c, min(mid[-1], c[-1]["l"]), "bb_squeeze", x["atr"])


# --- Kaufmuster: Kerzen -----------------------------------------------------------------
def _at_support(c, x, k):
    return k["l"] <= min(q["l"] for q in c[-21:-1]) * 1.01 and x["cl"][-2] < x["e20"][-2]


def inside_bar(c, x):
    mother, inner, cur = c[-3], c[-2], c[-1]
    if not (inner["h"] <= mother["h"] and inner["l"] >= mother["l"] and cur["c"] > mother["h"]
            and cur["c"] > x["e50"][-1]):
        return None
    return _rr(c, mother["l"], "inside_bar", x["atr"])


def morning_star(c, x):
    k1, k2, k3 = c[-3], c[-2], c[-1]
    if not (k1["c"] < k1["o"] and _body(k1) >= 0.6 * x["atr"] and _body(k2) <= 0.3 * _body(k1)
            and k3["c"] > k3["o"] and k3["c"] > (k1["o"] + k1["c"]) / 2):
        return None
    return _rr(c, min(k1["l"], k2["l"], k3["l"]), "morning_star", x["atr"])


def three_soldiers(c, x):
    ks = c[-3:]
    if not all(k["c"] > k["o"] and _body(k) >= 0.5 * x["atr"] and (k["h"] - k["c"]) <= 0.3 * _range(k) for k in ks):
        return None
    if not (ks[0]["c"] < ks[1]["c"] < ks[2]["c"] and x["cl"][-4] < x["e20"][-4]):
        return None
    return _rr(c, ks[0]["l"], "three_soldiers", x["atr"])


def engulfing(c, x):
    prev, cur = c[-2], c[-1]
    if not (prev["c"] < prev["o"] and cur["c"] > cur["o"] and cur["o"] <= prev["c"] and cur["c"] >= prev["o"]
            and _at_support(c, x, cur)):
        return None
    return _rr(c, min(prev["l"], cur["l"]), "engulfing", x["atr"])


def hammer(c, x):
    k = c[-1]
    lower = min(k["o"], k["c"]) - k["l"]
    upper = k["h"] - max(k["o"], k["c"])
    if not (lower >= 2 * max(_body(k), 1e-12) and upper <= 0.3 * _range(k) and _at_support(c, x, k)):
        return None
    return _rr(c, k["l"], "hammer", x["atr"])


BULLISH = [double_bottom, inv_head_shoulders, bull_flag, asc_triangle, breakout_retest, rsi_divergence,
           bb_squeeze, inside_bar, morning_star, three_soldiers, engulfing, hammer]


# --- Warnmuster (bärisch) ---------------------------------------------------------------
def bearish_names(c):
    """Welche Warnmuster sind gerade zu sehen? (Nur zur Bremse – wir verkaufen nicht leer.)"""
    if len(c) < 60:
        return []
    c = c[-WINDOW:]
    x, out = _ctx(c), []
    prev, cur = c[-2], c[-1]
    near_top = cur["h"] >= max(q["h"] for q in c[-21:-1]) * 0.99
    if prev["c"] > prev["o"] and cur["c"] < cur["o"] and cur["o"] >= prev["c"] and cur["c"] <= prev["o"] and near_top:
        out.append("bear_engulfing")
    upper = cur["h"] - max(cur["o"], cur["c"])
    if upper >= 2 * max(_body(cur), 1e-12) and (min(cur["o"], cur["c"]) - cur["l"]) <= 0.3 * _range(cur) and near_top:
        out.append("shooting_star")
    k1, k2, k3 = c[-3], c[-2], c[-1]
    if (k1["c"] > k1["o"] and _body(k1) >= 0.6 * x["atr"] and _body(k2) <= 0.3 * _body(k1)
            and k3["c"] < k3["o"] and k3["c"] < (k1["o"] + k1["c"]) / 2):
        out.append("evening_star")
    if all(k["c"] < k["o"] and _body(k) >= 0.5 * x["atr"] for k in c[-3:]) and c[-3]["c"] > c[-2]["c"] > c[-1]["c"]:
        out.append("three_crows")
    highs = [i for i in x["highs"] if i >= len(c) - 40]
    if len(highs) >= 2:
        i1, i2 = highs[-2], highs[-1]
        h1, h2 = c[i1]["h"], c[i2]["h"]
        if i2 - i1 >= 5 and abs(h2 - h1) / h1 <= 0.015:
            neck = min(k["l"] for k in c[i1:i2 + 1])
            if cur["c"] < neck:
                out.append("double_top")
        r = x["rsi"]
        if h2 > h1 and r[i2] < r[i1] - 3 and i2 >= len(c) - 8 and cur["c"] < cur["o"]:
            out.append("rsi_bear_divergence")
    if len(highs) >= 3:
        i1, i2, i3 = highs[-3:]
        ls, hd, rs = c[i1]["h"], c[i2]["h"], c[i3]["h"]
        if hd > max(ls, rs) + 0.5 * x["atr"] and abs(ls - rs) / ls <= 0.03:
            neck = min(min(k["l"] for k in c[i1:i2 + 1]), min(k["l"] for k in c[i2:i3 + 1]))
            if cur["c"] < neck:
                out.append("head_shoulders")
    return out


# --- Einstieg für Strategien ---------------------------------------------------------------
def find(c, allowed=None):
    """Alle Kaufmuster, die auf der letzten Kerze vollendet wurden."""
    if len(c) < 60:
        return []
    c = c[-WINDOW:]
    x = _ctx(c)
    out = []
    for fn in BULLISH:
        if allowed is not None and fn.__name__ not in allowed:
            continue
        s = fn(c, x)
        if s:
            out.append(s)
    return out


def signal(c, p):
    """Strategie "patterns": nimmt das erste gefundene Muster (Formationen vor Einzelkerzen).
    p["allowed"] = erlaubte Muster (None = alle), p["risk_mult"] = Risiko-Faktor für Muster-Trades."""
    found = find(c, p.get("allowed"))
    if not found:
        return None
    s = found[0]
    if p.get("risk_mult") is not None:
        s["risk_mult"] = p["risk_mult"]
    return s
