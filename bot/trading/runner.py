"""Führt EINEN Bot einen Lauf lang aus: für jeden Wert die neuen Kerzen holen, zuerst die
Schatten-Varianten (Lernen) und dann das echte Konto (mit Team-Entscheidung) durchspielen."""
import hashlib
import json

from .. import settings as S
from ..brain import learning as L
from ..data import kraken
from ..markets import display
from . import account as A
from . import pumpfun

LABELS = "ABCDEFG"


def _vhash(bot):
    return hashlib.md5(json.dumps(bot["variants"], sort_keys=True).encode()).hexdigest()[:10]


def _shadows(bot):
    return [dict(A.new_account(L.SHADOW_CASH), lean=True) for _ in bot["variants"]]


def new_state(bot):
    return {"real": A.new_account(0.0), "active": 0, "log": [], "pair_mult": {},
            "shadows": _shadows(bot), "vhash": _vhash(bot)}


def prepare(st, bot):
    """Wurden die Varianten im Code geändert, beginnt das Lernen neu (das echte Konto bleibt)."""
    if st.get("vhash") != _vhash(bot):
        st.update(shadows=_shadows(bot), active=0, pair_mult={}, vhash=_vhash(bot))
        L.log(st, "Varianten wurden geändert – Lernen startet neu (zuerst aus der Vergangenheit)")
    return st


def run(bid, bot, st, rates, enabled, errors, unavailable, gate=None):
    labels = [LABELS[i] for i in range(len(bot["variants"]))]
    if bot.get("source") == "pumpfun":
        pumpfun.run(bot, st, rates, enabled, errors, gate)
        return L.choose_variant(st, labels)
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
        # 1) Schatten-Varianten: lernen (beim ersten Mal aus der Vergangenheit), ohne Team-Regeln
        for vi, sh in enumerate(st["shadows"]):
            A.process(sh, bot, pair, closed, rate, bot["variants"][vi], vi,
                      start_from=max(len(closed) - S.WARMUP_CANDLES, 0))
            sh["marks"][pair] = live["c"] * rate
        # 2) echtes Konto: aktive Variante, Risiko je Paar (Lernen) und Team-Entscheidung (gate)
        mult = L.pair_multiplier(st, pair, st["real"]["trades"])
        act = st["active"]
        A.process(st["real"], bot, pair, closed, rate, bot["variants"][act], act, mult=mult,
                  can_open=enabled, gate=gate)
        st["real"]["marks"][pair] = live["c"] * rate
    return L.choose_variant(st, labels)
