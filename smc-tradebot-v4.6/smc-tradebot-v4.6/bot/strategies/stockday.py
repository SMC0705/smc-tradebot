"""Aktien-Daytrading (15-Minuten-Kerzen, Aktien-Token von Kraken) – nur solange die US-Börse offen ist.
Spätestens zum Börsenschluss wird verkauft: kein Risiko über Nacht. Aktien-Token kosten bei Kraken
nur 0,08 % Gebühr (Limit-Kauf 0 %) – deshalb lohnen sich hier auch kleine Tagesbewegungen.

Modus "orb" (Opening Range Breakout, Toby Crabel): Die ersten 30 bzw. 60 Minuten bilden die Eröffnungs-Spanne.
  Schließt eine Kerze zum ersten Mal an diesem Tag darüber, wird gekauft. Stop in der Mitte bzw. am Tief der Spanne.
Modus "pullback": Rücksetzer an die EMA21 im Aufwärtstrend des Tages (die Scalping-Idee, auf Aktien übertragen).
Nicht in der ersten halben Stunde (Eröffnungs-Chaos) und nicht in der letzten halben Stunde.
"""
from ..markets import us_session
from .indicators import atr, ema, rsi

TF = 15 * 60


def signal(c, p):
    if len(c) < 60:
        return None
    cur = c[-1]
    sess = us_session(cur["t"])
    if not sess or cur["t"] < sess[0]:
        return None
    end = cur["t"] + TF
    if not (sess[0] + 30 * 60 <= end <= sess[1] - 30 * 60):
        return None
    s = _orb(c, p, sess[0], end) if p.get("mode", "orb") == "orb" else _pullback(c, p)
    if s:
        s["eod"] = "us"
    return s


def _orb(c, p, open_t, end):
    n = p.get("or", 2)
    or_end = open_t + n * TF
    if end <= or_end:
        return None
    rng = [x for x in c if open_t <= x["t"] < or_end]
    if len(rng) < n:
        return None
    hi, lo = max(x["h"] for x in rng), min(x["l"] for x in rng)
    cur = c[-1]
    if not (cur["c"] > hi and cur["c"] > cur["o"]):
        return None
    if any(x["c"] > hi for x in c[:-1] if x["t"] >= or_end):
        return None   # nur der erste Ausbruch des Tages zählt
    if cur["c"] < ema([x["c"] for x in c], 50)[-1]:
        return None   # nur im Aufwärtstrend
    stop = (hi + lo) / 2 if p.get("stop", "mid") == "mid" else lo
    risk = cur["c"] - stop
    if risk <= 0 or risk / cur["c"] > 0.03:
        return None
    return {"stop": stop, "target": cur["c"] + p.get("rr", 2.0) * risk,
            "reason": f"Ausbruch aus der {n * 15}-Min.-Eröffnungsspanne"}


def _pullback(c, p):
    cl = [x["c"] for x in c]
    e9, e21, e50 = ema(cl, 9), ema(cl, 21), ema(cl, 50)
    i, cur, prev = len(c) - 1, c[-1], c[-2]
    if not (e9[i] > e21[i] > e50[i]):
        return None
    if not (prev["l"] <= e21[i - 1] and cur["c"] > e9[i] and cur["c"] > cur["o"] and rsi(cl)[-1] > 50):
        return None
    stop = min(x["l"] for x in c[-4:]) - 0.1 * atr(c)[-1]
    risk = cur["c"] - stop
    if risk <= 0 or risk / cur["c"] > 0.03:
        return None
    return {"stop": stop, "target": cur["c"] + p.get("rr", 2.0) * risk, "reason": "Rücksetzer an EMA21 im Tagestrend"}
