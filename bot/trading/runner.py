"""Führt EINEN Bot einen Lauf lang aus: für jeden Wert die neuen Kerzen holen, zuerst die
Schatten-Konten (Varianten + Muster = Lernen) und dann das echte Konto (mit Team-Entscheidung) durchspielen.
Was das echte Konto dabei gesehen und entschieden hat, landet im Prüfprotokoll (App: Bot antippen)."""
import hashlib
import json
import time

from .. import settings as S
from ..brain import learning as L
from ..data import kraken
from ..markets import display
from ..strategies import SIGNALS, patterns
from . import account as A
from . import pumpfun

LABELS = "ABCDEFG"


def _vhash(bot):
    key = json.dumps([S.ENGINE_VERSION, bot["variants"]], sort_keys=True)
    return hashlib.md5(key.encode()).hexdigest()[:10]


def _muster():
    return dict(A.new_account(L.SHADOW_CASH), lean=True, muster=True)


def _shadows(bot):
    return [dict(A.new_account(L.SHADOW_CASH), lean=True) for _ in bot["variants"]]


def new_state(bot):
    return {"real": A.new_account(0.0), "active": 0, "log": [], "pair_mult": {},
            "shadows": _shadows(bot), "muster": _muster(), "vhash": _vhash(bot), "live_since": int(time.time())}


def prepare(st, bot):
    """Wurden die Varianten im Code geändert, beginnt das Lernen neu (das echte Konto bleibt)."""
    pend = st["real"].setdefault("pending", {})
    for pair, o in list(pend.items()):
        if "sig" not in o:   # Signal aus der Zeit vor v4.3 -> Kauf zum Marktpreis, Team entscheidet beim Kauf
            pend[pair] = {"sig": o, "type": "market", "price": None, "from": 0, "until": 2 ** 62, "m": None}
    if st.get("vhash") != _vhash(bot):
        st.update(shadows=_shadows(bot), muster=_muster(), active=0, pair_mult={}, pair_pause={}, pair_since={},
                  pattern_status={}, vhash=_vhash(bot), live_since=int(time.time()))
        L.log(st, "Strategie wurde verbessert – Lernen startet neu (zuerst aus der Vergangenheit)")
    st.setdefault("muster", _muster())
    return st


def scores_only(bot, st):
    """Für übersprungene Bots (Zeitlimit): nur die Lern-Übersicht, ohne neue Kerzen."""
    return L.choose_variant(st, [LABELS[i] for i in range(len(bot["variants"]))])


def run(bid, bot, st, rates, enabled, errors, unavailable, gate=None):
    labels = [LABELS[i] for i in range(len(bot["variants"]))]
    if bot.get("source") == "pumpfun":
        pumpfun.run(bot, st, rates, enabled, errors, gate)
        return L.choose_variant(st, labels)
    main_fn = SIGNALS[bot["strategy"]]
    learned = L.learned_patterns(st)
    pattern_p = {"allowed": learned, "risk_mult": S.LEARN_RULES["pattern_risk"]}

    def combined(c, p):   # echtes Konto: eigene Strategie, sonst ein gelerntes Muster
        return main_fn(c, p) or (patterns.signal(c, pattern_p) if learned else None)

    stats = A.new_stats()
    for pair in bot["pairs"]:
        quote = pair[-3:]
        if quote not in rates:
            unavailable.append(pair)
            continue
        try:
            closed, live = kraken.get_candles(pair, bot["tf"], bot["aclass"])
        except Exception as e:
            unavailable.append(pair)
            if not isinstance(e, ValueError):
                errors.append(f"{bot['name']} {display(pair)}: {e}")
            continue
        rate = rates[quote]
        stats["pairs"] += 1
        # 1) Schatten-Varianten: lernen (beim ersten Mal aus der Vergangenheit), ohne Team-Regeln
        for vi, sh in enumerate(st["shadows"]):
            A.process(sh, bot, pair, closed, rate, bot["variants"][vi], vi,
                      start_from=max(len(closed) - S.WARMUP_CANDLES, 0), live=live)
            sh["marks"][pair] = live["c"] * rate
        # 2) Muster-Schattenkonto: testet ALLE Muster der Bibliothek auf diesem Markt und Takt
        #    (ohne Positions-Limit, damit jedes Muster oft genug getestet wird)
        A.process(st["muster"], dict(bot, max_pos=99, frac=0.05), pair, closed, rate, {"allowed": None}, -1,
                  start_from=max(len(closed) - S.WARMUP_CANDLES, 0), fn=patterns.signal, live=live)
        st["muster"]["marks"][pair] = live["c"] * rate
        # 3) echtes Konto: aktive Variante + gelernte Muster, Risiko je Wert (Lernen) und Team-Entscheidung
        mult = L.pair_multiplier(st, pair, st["real"]["trades"])
        act = st["active"]
        A.process(st["real"], bot, pair, closed, rate, bot["variants"][act], act, mult=mult,
                  can_open=enabled, gate=gate, fn=combined, tag_patterns=True, live=live, stats=stats)
        st["real"]["marks"][pair] = live["c"] * rate
    L.track_patterns(st)
    save_checks(st, stats)
    return L.choose_variant(st, labels)


def save_checks(st, stats, now=None):
    """Prüfprotokoll: Zähler dieses Laufs (24 Std. werden aufbewahrt) und die wichtigsten Hinweise."""
    now = now or int(time.time())
    notes = sorted(stats.pop("notes"), key=lambda n: (n[0], -(n[1] or 0)))[:8]
    st["checks"] = (st.get("checks", []) + [dict(stats, t=now)])[-S.CHECKS_KEEP:]
    new = [[t or now, text] for _, t, text in sorted(notes, key=lambda n: (n[1] or 0, -n[0]))]   # zeitlich sortiert
    st["check_notes"] = (st.get("check_notes", []) + new)[-15:]
