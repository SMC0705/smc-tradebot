"""Lern-Modul: Jeder Bot lernt auf drei Wegen aus seinen Ergebnissen.

1. Varianten: Drei Einstellungen seiner Strategie laufen parallel in Schatten-Konten (ohne echtes Geld).
   Das echte Konto folgt der Variante mit der besten nachgewiesenen Leistung.
2. Muster: Alle Kauf-Muster der Muster-Bibliothek (strategies/patterns.py) laufen in einem eigenen
   Schatten-Konto. Muster, die sich bei DIESEM Bot (Markt + Kerzentakt) nach Gebühren bewähren,
   gelten als "gelernt" und werden vom echten Konto zusätzlich gehandelt (mit halbem Risiko).
3. Werte: Verliert ein Wert (z. B. ETH/EUR) seit dem Live-Start deutlich, bekommt er weniger Risiko oder
   höchstens 24 Std. Pause – danach gibt es einen neuen Versuch mit halbem Risiko.

Leistung wird in R gemessen (Gewinn/Verlust geteilt durch das eingesetzte Risiko, nach Gebühren).
Damit Zufallstreffer nicht überbewertet werden, wird der Durchschnitt Richtung 0 gezogen.
Alles Wichtige landet im Lern-Protokoll, das die App anzeigt.
"""
import time

from .. import settings as S
from ..markets import display
from ..strategies.patterns import BULLISH, LABELS

SHADOW_CASH = 10000.0
PRIOR = 10
MIN_TRADES = 10
SWITCH_MARGIN = 0.05
LR = S.LEARN_RULES


def score(trades, prior=PRIOR):
    rs = [t["r"] for t in trades]
    return sum(rs) / (len(rs) + prior), len(rs), (sum(rs) / len(rs) if rs else 0.0)


def log(st, msg):
    st["log"].append([int(time.time()), msg])
    st["log"] = st["log"][-30:]


# --- 1) Varianten ----------------------------------------------------------------------
def choose_variant(st, labels):
    scores = [score(v["trades"]) for v in st["shadows"]]
    act = st["active"]
    best = max(range(len(scores)), key=lambda i: scores[i][0])
    if (best != act and scores[best][1] >= MIN_TRADES and scores[best][0] - scores[act][0] > SWITCH_MARGIN
            and scores[best][2] > scores[act][2] and scores[best][2] > 0):
        log(st, f"Wechsel zu Variante {labels[best]}: Ø {scores[best][2]:+.2f} R über {scores[best][1]} Trades "
                f"(bisher {labels[act]}: Ø {scores[act][2]:+.2f} R)")
        st["active"] = best
    return scores


# --- 2) Muster ---------------------------------------------------------------------------
def pattern_stats(st):
    """Ergebnis je Muster aus Muster-Schattenkonto + echten Muster-Trades."""
    trades = [t for t in st.get("muster", {}).get("trades", []) if t.get("pattern")]
    trades += [t for t in st["real"]["trades"] if t.get("pattern")]
    out = {}
    for fn in BULLISH:
        name = fn.__name__
        sc, n, avg = score([t for t in trades if t["pattern"] == name], prior=5)
        if n >= LR["pattern_min_trades"] and sc >= LR["pattern_min_score"]:
            status = "gelernt"
        elif n >= LR["pattern_min_trades"] and avg < 0:
            status = "verworfen"
        else:
            status = "beobachtet"
        out[name] = {"trades": n, "avg_r": round(avg, 2), "score": round(sc, 3), "status": status}
    return out


def learned_patterns(st):
    return {name for name, s in pattern_stats(st).items() if s["status"] == "gelernt"}


def track_patterns(st):
    """Protokolliert, wenn ein Muster gelernt oder verworfen wird."""
    known = st.setdefault("pattern_status", {})
    for name, s in pattern_stats(st).items():
        if s["status"] != "beobachtet" and known.get(name) != s["status"]:
            log(st, f"Muster {s['status']}: {LABELS[name]} (Ø {s['avg_r']:+.2f} R aus {s['trades']} Test-Trades)")
        known[name] = s["status"]


# --- 3) Werte ------------------------------------------------------------------------------
def pair_multiplier(st, pair, real_trades, now=None):
    """Risiko-Faktor je Wert. Zählt nur Trades seit dem Live-Start bzw. seit der letzten Pause –
    die Lern-Vergangenheit der Schatten-Konten führt nicht mehr zu Pausen."""
    now = now or int(time.time())
    pauses, since_d = st.setdefault("pair_pause", {}), st.setdefault("pair_since", {})
    old = st["pair_mult"].get(pair, 1.0)
    until = pauses.get(pair, 0)
    if until > now:
        st["pair_mult"][pair] = 0.0
        return 0.0
    if until:   # Pause vorbei -> neuer Versuch mit halbem Risiko
        del pauses[pair]
        since_d[pair] = now
        st["pair_mult"][pair] = 0.5
        log(st, f"{display(pair)}: Pause vorbei – neuer Versuch mit halbem Risiko")
        return 0.5
    since = max(st.get("live_since", 0), since_d.get(pair, 0))
    sh = [t for t in st["shadows"][st["active"]]["trades"] if t["pair"] == pair and t["closed_t"] >= since]
    rl = [t for t in real_trades if t["pair"] == pair and t["closed_t"] >= since]
    recent = sorted(sh + rl, key=lambda t: t["closed_t"])[-15:]
    n = len(recent)
    m = sum(t["r"] for t in recent) / n if n else 0.0
    if n >= LR["pair_pause_n"] and m < LR["pair_pause_r"]:
        pauses[pair] = now + LR["pair_pause_h"] * 3600
        log(st, f"{display(pair)}: {LR['pair_pause_h']} Std. Pause (Ø {m:+.2f} R aus {n} Trades seit Live-Start)")
        st["pair_mult"][pair] = 0.0
        return 0.0
    if n >= 5 and m < -0.3:
        new = 0.5
    elif n >= 5 and m > 0.4:
        new = 1.25
    elif old == 0.5 and since_d.get(pair) and n < 5:
        new = 0.5   # nach einer Pause erst wieder voll, wenn es sich bewährt hat
    else:
        new = 1.0
    if new != old:
        txt = {0.5: "halbes Risiko", 1.0: "normales Risiko", 1.25: "erhöhtes Risiko (1,25x)"}[new]
        log(st, f"{display(pair)}: jetzt {txt} (Ø {m:+.2f} R aus {n} Trades)")
    st["pair_mult"][pair] = new
    return new
