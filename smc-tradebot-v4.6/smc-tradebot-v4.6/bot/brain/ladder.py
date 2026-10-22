"""Inkubations-Leiter und Decay-Check (Idee aus Algory: eine Strategie muss sich beweisen, bevor sie volles Risiko bekommt).

Leiter – Faktor auf das normale Risiko des Bots im echten Konto (Regeln in settings.LADDER_RULES):
  Ersatzbank   0     keine neuen Trades im echten Konto, die Schatten-Varianten handeln weiter
  Probe        ¼     hier startet jeder Bot
  Bewährung    ½     ab 10 Trades auf der Probe-Stufe mit Ø R > 0
  Voll         1     ab 20 Trades auf ½ mit Ø R > 0, wenn auch die letzten 30 Trades zusammen im Plus sind
Aufgestiegen wird nur durch abgeschlossene Trades – nie, weil Zeit vergangen ist.

Decay-Check – nach je 15 neuen abgeschlossenen Trades wird der Bot neu bewertet (Note 0–100 aus genau diesen Trades):
  Ø R < 0                                 -> „Ersatz fällig“: eine Stufe runter, die beste Schatten-Variante übernimmt
  Note mind. 5 Punkte unter der letzten   -> „schwächelt“: eine Stufe runter (nie tiefer als Probe)
  sonst                                   -> „gesund“
Auf der Probe-Stufe heißt „Ersatz fällig“: Ist eine Schatten-Variante im Plus, übernimmt sie und startet neu auf Probe –
sonst geht der Bot auf die Ersatzbank. Von dort kommt er zurück, sobald eine Schatten-Variante seit dem Gang auf die Bank
mind. 15 Trades mit Ø R > 0 hat; diese Variante wird dann aktiv. Das ersetzt das „schwache Bots von Hand auf 0 % stellen“.

Gemessen wird in R (Gewinn geteilt durch das eingesetzte Risiko, nach Gebühren). Ein Trade mit ¼ Risiko zählt deshalb
genauso viel wie einer mit vollem Risiko. Gezählt werden die Trades über ihre laufende Nummer (seq), nicht über die Zeit.
Trades aus der Zeit vor v4.6 haben keine Nummer und zählen für die Leiter nicht.
"""
import math
import time

from .. import settings as S
from . import learning as L

LR = S.LADDER_RULES
ORDER = ["bank", "probe", "halb", "voll"]          # von unten nach oben
NAMES = {"bank": "Ersatzbank", "probe": "Probe", "halb": "Bewährung", "voll": "Volles Risiko"}
HEALTH = {"neu": "noch nicht geprüft", "gesund": "gesund", "schwach": "schwächelt", "ersatz": "Ersatz fällig"}
SHARE = {"bank": "0", "probe": "¼", "halb": "½", "voll": "1"}


def _n(acc):
    return acc.get("n_closed", 0)


def new(real, now=None):
    now = now or int(time.time())
    n = _n(real)
    return {"stage": LR["start"], "since": now, "since_n": n, "review_n": n, "note": None, "health": "neu",
            "reviewed_t": None, "hist": []}


def state(st, now=None):
    if "ladder" not in st:
        st["ladder"] = new(st["real"], now)
    return st["ladder"]


def factor(st):
    return LR["factor"][state(st)["stage"]]


def block_reason(st):
    """Grund, warum das echte Konto gerade nichts Neues kauft (nur auf der Ersatzbank)."""
    if state(st)["stage"] == "bank":
        return "Bot sitzt auf der Ersatzbank (Decay-Check) – nur die Schatten-Varianten handeln"
    return None


def note(trades):
    """Note 0–100. 50 = kein Vorteil nach Gebühren. Der Ø R wird Richtung 0 gezogen, damit wenige Trades
    nicht überbewertet werden (+0,3 R über 15 Trades ≈ 71, −0,3 R ≈ 29)."""
    rs = [t["r"] for t in trades]
    return round(50 + 50 * math.tanh(sum(rs) / (len(rs) + 5) / 0.5))


def _avg(trades):
    return sum(t["r"] for t in trades) / len(trades) if trades else 0.0


def _after(acc, n):
    return [t for t in acc["trades"] if t.get("seq", 0) > n]


def _set(st, lad, stage, now, msg):
    old = lad["stage"]
    lad.update(stage=stage, since=now, since_n=_n(st["real"]))
    if stage == "bank":
        lad["bench"] = {"born": st.get("live_since"), "n": [_n(sh) for sh in st["shadows"]]}
    else:
        lad.pop("bench", None)
    if stage in ("probe", "bank") or ORDER.index(stage) < ORDER.index(old):
        lad["review_n"] = _n(st["real"])   # nach einem Abstieg zählt der nächste Check nur neue Trades
    L.log(st, msg)


def _best_shadow(st):
    """Beste Schatten-Variante (gleiche Wertung wie beim normalen Variantenwechsel) – nur wenn sie im Plus ist."""
    scores = [L.score(sh["trades"]) for sh in st["shadows"]]
    if not scores:
        return None
    best = max(range(len(scores)), key=lambda i: scores[i][0])
    if scores[best][1] >= L.MIN_TRADES and scores[best][2] > 0:
        return best
    return None


def _review(st, lad, new_trades, labels, now):
    n, avg, prev = note(new_trades), _avg(new_trades), lad.get("note")
    lad.update(review_n=max(t["seq"] for t in new_trades), note=n, reviewed_t=now)
    stage, i = lad["stage"], ORDER.index(lad["stage"])
    head = f"Decay-Check: Note {n} aus {len(new_trades)} Trades (Ø {avg:+.2f} R)"
    if avg < 0:
        lad["health"] = "ersatz"
        swap = _best_shadow(st)
        if swap is not None and swap != st["active"]:
            old = st["active"]
            st["active"] = swap
            target = "probe" if stage == "probe" else ORDER[i - 1]
            _set(st, lad, target, now, f"{head} – Ersatz fällig: Variante {labels[swap]} übernimmt von "
                                       f"{labels[old]}, Stufe {NAMES[target]} ({SHARE[target]} Risiko)")
        elif stage == "probe":
            _set(st, lad, "bank", now, f"{head} – Ersatz fällig, aber keine Variante im Plus: Ersatzbank "
                                       f"(nur Schatten-Trades, bis eine Variante {LR['bench_n']} Trades im Plus hat)")
        else:
            _set(st, lad, ORDER[i - 1], now, f"{head} – Ersatz fällig, keine bessere Variante: zurück auf "
                                             f"{NAMES[ORDER[i - 1]]} ({SHARE[ORDER[i - 1]]} Risiko)")
    elif prev is not None and n <= prev - LR["drop"]:
        lad["health"] = "schwach"
        if stage in ("halb", "voll"):
            _set(st, lad, ORDER[i - 1], now, f"{head} – schwächelt (vorher {prev}): zurück auf "
                                             f"{NAMES[ORDER[i - 1]]} ({SHARE[ORDER[i - 1]]} Risiko)")
        else:
            L.log(st, f"{head} – schwächelt (vorher {prev}), bleibt auf Probe")
    else:
        lad["health"] = "gesund"
        L.log(st, f"{head} – gesund")
    lad["hist"] = (lad["hist"] + [[now, n, lad["health"], lad["stage"]]])[-20:]


def _climb(st, lad, now):
    real, stage = st["real"], lad["stage"]
    here = _after(real, lad["since_n"])
    if stage == "probe" and len(here) >= LR["probe_n"] and _avg(here) > 0:
        _set(st, lad, "halb", now, f"Aufstieg auf Bewährung (½ Risiko): {len(here)} Trades auf Probe, Ø {_avg(here):+.2f} R")
    elif stage == "halb" and len(here) >= LR["halb_n"] and _avg(here) > 0:
        last = real["trades"][-LR["climb_n"]:]
        if len(last) >= LR["climb_n"] and _avg(last) > 0:
            _set(st, lad, "voll", now, f"Aufstieg auf volles Risiko: {len(here)} Trades auf ½ (Ø {_avg(here):+.2f} R), "
                                       f"letzte {len(last)} Trades Ø {_avg(last):+.2f} R")


def _bench(st, lad, labels, now):
    ref = lad.get("bench") or {}
    if ref.get("born") != st.get("live_since") or len(ref.get("n", [])) != len(st["shadows"]):
        # Varianten wurden neu gestartet (neue Version): ab ihrem jetzigen Stand zählen
        ref = lad["bench"] = {"born": st.get("live_since"), "n": [_n(sh) for sh in st["shadows"]]}
    best, best_score = None, None
    for i, sh in enumerate(st["shadows"]):
        tr = _after(sh, ref["n"][i])
        if len(tr) >= LR["bench_n"] and _avg(tr) > 0:
            sc = L.score(tr)[0]
            if best is None or sc > best_score:
                best, best_score = i, sc
    if best is not None:
        tr = _after(st["shadows"][best], ref["n"][best])
        st["active"] = best
        lad.update(note=None, health="neu")
        _set(st, lad, "probe", now, f"Zurück von der Ersatzbank: Variante {labels[best]} hat {len(tr)} Schatten-Trades "
                                    f"mit Ø {_avg(tr):+.2f} R – startet auf Probe (¼ Risiko)")


def update(st, labels, now=None):
    """Nach jedem Lauf eines Bots: Ersatzbank prüfen, sonst Decay-Check (alle 15 neuen Trades) und Aufstieg."""
    now = now or int(time.time())
    lad = state(st, now)
    if lad["stage"] == "bank":
        _bench(st, lad, labels, now)
        return
    new_trades = _after(st["real"], lad["review_n"])
    if len(new_trades) >= LR["review_n"]:
        _review(st, lad, new_trades, labels, now)
    if lad["stage"] != "bank":
        _climb(st, lad, now)


def status(st, labels):
    """Für die App: Stufe, Gesundheit und was bis zur nächsten Stufe fehlt."""
    lad, real = state(st), st["real"]
    stage = lad["stage"]
    out = {"stage": stage, "name": NAMES[stage], "share": SHARE[stage], "factor": LR["factor"][stage],
           "since": lad["since"], "health": lad["health"], "health_text": HEALTH[lad["health"]], "note": lad["note"],
           "reviewed_t": lad["reviewed_t"], "review": {"have": len(_after(real, lad["review_n"])), "need": LR["review_n"]},
           "hist": lad["hist"][-8:], "next": None}
    here = _after(real, lad["since_n"])
    if stage == "probe":
        out["next"] = {"to": "halb", "have": len(here), "need": LR["probe_n"], "avg_r": round(_avg(here), 2)}
    elif stage == "halb":
        last = real["trades"][-LR["climb_n"]:]
        out["next"] = {"to": "voll", "have": len(here), "need": LR["halb_n"], "avg_r": round(_avg(here), 2),
                       "last_avg_r": round(_avg(last), 2), "last_n": len(last)}
    elif stage == "bank":
        ref = lad.get("bench") or {"n": [0] * len(st["shadows"])}
        prog = [(i, _after(sh, ref["n"][i] if i < len(ref["n"]) else 0)) for i, sh in enumerate(st["shadows"])]
        i, tr = max(prog, key=lambda p: (_avg(p[1]) > 0, len(p[1]))) if prog else (0, [])
        out["next"] = {"to": "probe", "have": len(tr), "need": LR["bench_n"], "avg_r": round(_avg(tr), 2),
                       "variant": labels[i] if i < len(labels) else None}
    return out
