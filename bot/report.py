"""Baut die Übersicht für die Handy-App (docs/data/status.json). Hier wird nur zusammengefasst –
keine Handels-Entscheidungen."""
import time

from . import settings as S
from .bots import BOTS
from .brain import ladder
from .brain import learning as L
from .strategies.patterns import LABELS as PATTERN_LABELS
from .markets import display
from .trading import account as A
from .trading import venues as V
from .trading.runner import LABELS


def stats(trades, curve, capital):
    wins = [t for t in trades if t["pnl"] > 0]
    peak, mdd = 0.0, 0.0
    for _, pnl in curve:  # Kurve = Gewinn/Verlust in EUR (Umbuchungen zählen nicht)
        peak = max(peak, pnl)
        if capital > 1:
            mdd = max(mdd, (peak - pnl) / capital)
    return {"trades": len(trades), "winrate": round(len(wins) / len(trades) * 100, 1) if trades else None,
            "avg_r": round(sum(t["r"] for t in trades) / len(trades), 2) if trades else None,
            "max_drawdown_pct": round(mdd * 100, 2)}


def downsample(curve, n=200):
    if len(curve) <= n:
        return curve
    step = len(curve) / n
    return [curve[int(i * step)] for i in range(n)] + [curve[-1]]


def checks(st, now):
    """Prüfprotokoll fürs Handy: letzte Prüfung, Summen der letzten 24 Std., wichtigste Hinweise."""
    runs = [c for c in st.get("checks", []) if now - c["t"] <= 24 * 3600]
    keys = ("candles", "signals", "too_small", "own", "team", "orders", "unfilled", "bought", "sold")
    last = st.get("checks", [])[-1] if st.get("checks") else None
    return {"last_t": last["t"] if last else None, "pairs": last["pairs"] if last else 0, "runs": len(runs),
            "day": {k: sum(c.get(k, 0) for c in runs) for k in keys},
            "notes": list(reversed(st.get("check_notes", [])))[:12]}


def execution(bot):
    """Wie der Bot kauft, an welcher Börse und was es kostet (für die Anzeige)."""
    if not bot["pairs"] or bot.get("source") in ("pumpfun", "focus"):
        return None
    typ, groups = A.order_type(bot), {}
    for p in bot["pairs"]:
        v = V.venue(bot, p)
        g = groups.setdefault(v["name"], {"venue": V.label(v["name"]), "n": 0, "maker": v["maker"] * 100,
                                          "taker": v["taker"] * 100, "stops": []})
        g["n"] += 1
        g["stops"].append(A.min_stop(bot, p, typ) * 100)
    for g in groups.values():   # typischer (mittlerer) Mindest-Stop
        g["min_stop"] = round(sorted(g.pop("stops"))[g["n"] // 2], 2)
    return {"entry": typ, "venues": sorted(groups.values(), key=lambda g: -g["n"])}


def bot_status(bot, st, weight, team, scores, unavailable, now=None):
    now = now or int(time.time())
    a = st["real"]
    eq = A.equity(a)
    names = st.get("names", {})
    onchain = bot.get("source") == "pumpfun"
    disp = (lambda x: names.get(x, x[:6] + "…")) if onchain else display
    pos = []
    for p in a["positions"].values():
        val = p["qty"] * a["marks"].get(p["pair"], p["entry"] * p["rate"])
        price, risk_px = val / p["qty"] / p["rate"], p["entry"] - p["init_stop"]
        r_now = (price - p["entry"]) / risk_px if risk_px > 0 else 0.0
        r_tgt = min((p["target"] - p["entry"]) / risk_px, 3.0) if risk_px > 0 else 2.0
        pos.append({"pair": disp(p["pair"]), "addr": p["pair"] if onchain else None, "entry": p["entry"],
                    "stop": p["stop"], "target": p["target"], "opened_t": p["opened_t"], "value": round(val, 2),
                    "pnl_pct": round((val * (1 - p.get("fee_t", A.fees(bot, p["pair"])[1])) / p["cost"] - 1) * 100, 2),
                    "reason": p["reason"], "venue": V.label(p["venue"]) if p.get("venue") else None,
                    "price": price, "r_now": round(r_now, 2),     # Fortschritt: 0 = am Stop, 1 = am Ziel
                    "progress": round(max(0.0, min(1.0, (r_now + 1) / (r_tgt + 1))), 3)})
    return {
        "name": bot["name"], "style": bot["style"], "market": bot["market"], "team": team,
        "weight": round(weight, 1), "enabled": weight > 0, "equity": round(eq, 2), "net_in": round(a["net_in"], 2),
        "pnl": round(eq - a["net_in"], 2),
        "pnl_pct": round((eq / a["net_in"] - 1) * 100, 2) if a["net_in"] > 1 else 0.0,
        "cash": round(a["cash"], 2), "halted": a["halted"], "positions": pos,
        "trades": [dict(t, pair=disp(t["pair"]), venue=V.label(t["venue"]) if t.get("venue") else None)
                   for t in reversed(a["trades"][-30:])],
        "stats": stats(a["trades"], a["equity_curve"], max(a["net_in"], a.get("cap", 0.0))),
        "curve": downsample(a["equity_curve"]),
        "unavailable": [display(p) for p in unavailable],
        "scan": st.get("last_scan"),
        "board": st.get("board") if bot.get("source") == "focus" else None,
        "checks": checks(st, now), "exec": execution(bot),
        "ladder": ladder.status(st, [LABELS[i] for i in range(len(bot["variants"]))]),
        "orders": [{"pair": disp(pp), "type": o["type"], "price": o.get("price"), "until": o.get("until"),
                    "reason": o["sig"].get("reason")} for pp, o in a.get("pending", {}).items() if "sig" in o],
        "learning": {
            "active": LABELS[st["active"]],
            "variants": [{"label": LABELS[i], "params": bot["variants"][i], "trades": s[1],
                          "avg_r": round(s[2], 2), "score": round(s[0], 3)} for i, s in enumerate(scores)],
            "paused": [{"pair": display(p), "until": u} for p, u in st.get("pair_pause", {}).items() if u > time.time()],
            "patterns": [] if onchain else sorted(({"id": k, "label": PATTERN_LABELS[k], **v} for k, v in L.pattern_stats(st).items()),
                               key=lambda x: ({"gelernt": 0, "beobachtet": 1, "verworfen": 2}[x["status"]], -x["trades"])),
            "log": list(reversed(st["log"][-10:])),
        },
    }


def news_status(sit, nstate):
    if not sit:
        return None
    return {
        "level": sit["level"], "level_text": sit["level_text"], "reasons": sit["reasons"],
        "themes": sit["themes"], "fear_greed": sit["fear_greed"], "hint": sit["hint"],
        "pauses": [{"pair": display(k), "until": v["until"], "title": v["title"], "src": v["src"]}
                   for k, v in sit["pauses"].items()],
        "upcoming": sit["upcoming"], "event_now": sit["event_now"],
        "headlines": [{k: h[k] for k in ("src", "title", "link", "t", "themes")} for h in sit["headlines"]],
        "sources": sit["sources"], "log": list(reversed(nstate.get("log", [])[-15:])),
    }


COUNCIL = {"analyst": "Analyst", "news": "Nachrichten", "trend": "Großer Trend", "muster": "Muster",
           "kollegen": "Kollegen", "risiko": "Risiko-Manager"}


def council_status(tstate, states):
    """Der Rat: letzte Abstimmungen und wer mit seiner Stimme bisher richtig lag
    (Bedenken + Verlust oder Ja + Gewinn = richtig). Gezählt werden echte, abgeschlossene Trades."""
    recent = sorted(tstate.get("council", []), key=lambda c: -c["t"])[:12]
    recent = [dict(c, bot=BOTS[c["bot"]]["name"] if c["bot"] in BOTS else c["bot"]) for c in recent]
    score = {k: [0, 0] for k in COUNCIL}
    for st in states.values():
        for t in st["real"]["trades"]:
            for k, f in (t.get("votes") or {}).items():
                if k in score:
                    score[k][0] += 1
                    score[k][1] += (f < 1) != (t["r"] > 0)
    return {"members": COUNCIL, "recent": recent,
            "accuracy": [{"id": k, "name": COUNCIL[k], "votes": n, "right": r, "pct": round(r / n * 100) if n else None}
                         for k, (n, r) in score.items()]}


def build(now, errors, pool, total, weights, suggestion, teams, bots, news, markets=None, council=None):
    return {
        "mode": S.MODE, "version": S.RELEASE, "updated_at": now, "currency": "EUR", "errors": errors,
        "pool": {"equity": round(total, 2), "start": pool["start"],
                 "pnl_pct": round((total / pool["start"] - 1) * 100, 2),
                 "unallocated": round(pool["unallocated"], 2), "weights": weights,
                 "rebalancing": pool["pending_runs"] > 0, "curve": downsample(pool["curve"]),
                 "suggestion": suggestion},
        "teams": teams, "bots": bots, "news": news, "markets": markets or [], "council": council,
    }
