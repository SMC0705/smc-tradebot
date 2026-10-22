"""Fokus-Bot (Idee aus der „416-Märkte“-Anleitung, ohne deren Versprechen): Er sieht die frischen Kaufsignale
ALLER Bots, lässt sie bewerten (brain/ranking.py) und handelt nur die eine beste Gelegenheit –
eine Position zur Zeit, 1 % Risiko, Tagesverlust-Limit 3 %. Stop, Ziel, Börse und Ausstieg übernimmt er vom Bot,
von dem das Signal stammt. Seine drei Varianten lernen, ab welcher Mindestnote sich ein Kauf lohnt (0,6 / 0,5 / 0,7)."""
import time
from datetime import datetime, timezone

from .. import settings as S
from ..bots import BOTS
from ..brain import ladder
from ..brain import learning as L
from ..data import kraken
from . import account as A
from .runner import LABELS, save_checks


def _none(c, p):   # der Fokus-Bot sucht keine eigenen Signale
    return None


def _cfg(bot, src):
    """Regeln des Signal-Bots (Takt, Börse, Ausstieg) mit den Geld-Regeln des Fokus-Bots."""
    return dict(src, risk=bot["risk"], frac=bot["frac"], max_pos=1, cooldown=0)


def day_locked(acc, now):
    """Tagesverlust-Limit: Ist das Konto heute (UTC) um mehr als 3 % gefallen, gibt es bis morgen keine neuen Trades."""
    d = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
    eq = A.equity(acc)
    day = acc.setdefault("day", {"d": d, "eq0": eq, "locked": False})
    if day["d"] != d:
        day.update(d=d, eq0=eq, locked=False)
    if eq < day["eq0"] * (1 - S.FOCUS_RULES["daily_loss"]):
        day["locked"] = True
    return day["locked"]


def _manage(acc, bot, rates, enabled, stats, lf=1.0):
    """Offene Position bzw. wartende Order mit den Kerzen des Signal-Bots weiterführen.
    lf = Stufe der Inkubations-Leiter (nur echtes Konto; bei < 1 wird mindestens die Mindestgröße gekauft)."""
    meta = acc.setdefault("meta", {})
    for pair in sorted(set(acc["positions"]) | set(acc["pending"])):
        info, rate = meta.get(pair), rates.get(pair[-3:])
        if not info or info["bot"] not in BOTS or not rate:
            continue
        src = BOTS[info["bot"]]
        try:
            closed, live = kraken.get_candles(pair, src["tf"], src["aclass"])
        except Exception:
            continue
        A.process(acc, _cfg(bot, src), pair, closed, rate, {}, info.get("variant", 0), can_open=enabled,
                  fn=_none, live=live, stats=stats, floor=lf < 1)
        acc["marks"][pair] = live["c"] * rate
    for pair in [p for p in meta if p not in acc["positions"] and p not in acc["pending"]]:
        del meta[pair]


def _enter(acc, bot, e, vi, enabled, stats, lf=1.0):
    c = e["cand"]
    src, pair = BOTS[c["bot"]], c["pair"]
    try:
        closed, live = kraken.get_candles(pair, src["tf"], src["aclass"])
    except Exception:
        return False
    cfg = _cfg(bot, src)
    sig = dict(c["sig"], variant=vi, reason=f"Fokus #1 (Note {e['score']:.2f}) – {src['name']}: {c['sig']['reason']}")
    acc["last_t"][pair] = c["last_t"]          # ab jetzt die Kerzen dieses Werts verfolgen
    acc.setdefault("meta", {})[pair] = {"bot": c["bot"], "variant": vi, "score": e["score"]}
    A.place_order(acc, cfg, pair, sig, c["price"], c["typ"], c["t"], lf)
    A.count(stats, "orders", c["t"], pair, f"Fokus #1 mit Note {e['score']:.2f} ({src['name']}) – "
                                          + ("Limit-Kauf gelegt" if c["typ"] == "limit" else "Kauf zum Marktpreis"))
    A.process(acc, cfg, pair, closed, c["rate"], {}, vi, can_open=enabled, fn=_none, live=live, stats=stats,
              floor=lf < 1)
    acc["marks"][pair] = live["c"] * c["rate"]
    return True


def run(bot, st, ranked, rates, enabled, now=None):
    now = now or int(time.time())
    labels = [LABELS[i] for i in range(len(bot["variants"]))]
    stats = A.new_stats()
    accounts = [(st["real"], st["active"], True)] + [(sh, i, False) for i, sh in enumerate(st["shadows"])]
    lf = ladder.factor(st)   # Inkubations-Leiter: nur fürs echte Konto
    for acc, vi, real in accounts:
        _manage(acc, bot, rates, enabled, stats if real else None, lf if real else 1.0)
    allowed = [e for e in ranked if e["block"] is None]
    stats["signals"] = len(ranked)
    stats["own"] = len(ranked) - len(allowed)
    status, taken = None, None
    for acc, vi, real in accounts:
        need = bot["variants"][vi]["min_score"]
        if acc["positions"] or acc["pending"]:
            why = "Fokus hält schon eine Position – erst wenn sie geschlossen ist, kommt die nächste"
        elif day_locked(acc, now):
            why = f"Tagesverlust-Limit ({S.FOCUS_RULES['daily_loss'] * 100:.0f} %) erreicht – heute keine neuen Trades"
        elif real and not enabled:
            why = "Bot ist ausgeschaltet (0 %)"
        elif real and lf <= 0:
            why = ladder.block_reason(st)
        elif not allowed:
            why = "keine erlaubte Gelegenheit in diesem Lauf"
        elif allowed[0]["score"] < need:
            why = f"beste Note {allowed[0]['score']:.2f} liegt unter der Mindestnote {need:.2f}"
        else:
            why = None
            if _enter(acc, bot, allowed[0], vi, enabled, stats if real else None, lf if real else 1.0) and real:
                taken = allowed[0]
        if real:
            status = why or f"Kauf: {allowed[0]['name']} (Note {allowed[0]['score']:.2f})"
    st["board"] = {"t": now, "min_score": bot["variants"][st["active"]]["min_score"], "status": status,
                   "items": [{k: e[k] for k in ("name", "bot_name", "score", "parts", "edge", "rr", "block")}
                             | {"taken": e is taken} for e in ranked[:S.FOCUS_RULES["board"]]]}
    save_checks(st, stats, now)
    return L.choose_variant(st, labels)
