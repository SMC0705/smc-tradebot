"""Lern-Modul: Jeder Bot testet mehrere Parameter-Varianten parallel mit Schatten-Konten.
Das echte Konto folgt der Variante mit der besten nachgewiesenen Leistung.
Außerdem wird das Risiko pro Paar angepasst: schwache Paare werden reduziert oder pausiert,
starke leicht erhöht. Alles wird im Lern-Protokoll festgehalten.

Leistung wird in R gemessen (Gewinn/Verlust geteilt durch das eingesetzte Risiko, nach Gebühren).
Damit Zufallstreffer nicht überbewertet werden, wird der Durchschnitt Richtung 0 gezogen
(Score = Summe R / (Anzahl + 10)), und ein Wechsel braucht mindestens 10 Trades.
"""
import time

from .config import display

SHADOW_CASH = 10000.0
PRIOR = 10
MIN_TRADES = 10
SWITCH_MARGIN = 0.05


def score(trades):
    rs = [t["r"] for t in trades]
    return sum(rs) / (len(rs) + PRIOR), len(rs), (sum(rs) / len(rs) if rs else 0.0)


def _log(st, msg):
    st["log"].append([int(time.time()), msg])
    st["log"] = st["log"][-30:]


def choose_variant(st, labels):
    scores = [score(v["trades"]) for v in st["shadows"]]
    act = st["active"]
    best = max(range(len(scores)), key=lambda i: scores[i][0])
    if (best != act and scores[best][1] >= MIN_TRADES and scores[best][0] - scores[act][0] > SWITCH_MARGIN
            and scores[best][2] > scores[act][2] and scores[best][2] > 0):
        _log(st, f"Wechsel zu Variante {labels[best]}: Ø {scores[best][2]:+.2f} R über {scores[best][1]} Trades "
                 f"(bisher {labels[act]}: Ø {scores[act][2]:+.2f} R)")
        st["active"] = best
    return scores


def pair_multiplier(st, pair, real_trades):
    """Risiko-Faktor je Paar aus den letzten 15 Trades (aktive Variante + echtes Konto)."""
    sh = [t for t in st["shadows"][st["active"]]["trades"] if t["pair"] == pair]
    rl = [t for t in real_trades if t["pair"] == pair]
    recent = sorted(sh + rl, key=lambda t: t["closed_t"])[-15:]
    n = len(recent)
    m = sum(t["r"] for t in recent) / n if n else 0.0
    if n >= 8 and m < -0.6:
        new = 0.0
    elif n >= 5 and m < -0.3:
        new = 0.5
    elif n >= 5 and m > 0.4:
        new = 1.25
    else:
        new = 1.0
    old = st["pair_mult"].get(pair, 1.0)
    if new != old:
        txt = {0.0: "pausiert", 0.5: "halbes Risiko", 1.0: "normales Risiko", 1.25: "erhöhtes Risiko (1,25x)"}[new]
        _log(st, f"{display(pair)}: jetzt {txt} (Ø {m:+.2f} R aus {n} Trades)")
    st["pair_mult"][pair] = new
    return new
