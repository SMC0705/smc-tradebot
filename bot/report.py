"""Baut die Übersicht für die Handy-App (docs/data/status.json). Hier wird nur zusammengefasst –
keine Handels-Entscheidungen."""
import time

from . import settings as S
from .brain import learning as L
from .strategies.patterns import LABELS as PATTERN_LABELS
from .markets import display
from .trading import account as A
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


def bot_status(bot, st, weight, team, scores, unavailable):
    a = st["real"]
    eq = A.equity(a)
    names = st.get("names", {})
    onchain = bot.get("source") == "pumpfun"
    disp = (lambda x: names.get(x, x[:6] + "…")) if onchain else display
    pos = []
    for p in a["positions"].values():
        val = p["qty"] * a["marks"].get(p["pair"], p["entry"] * p["rate"])
        pos.append({"pair": disp(p["pair"]), "addr": p["pair"] if onchain else None, "entry": p["entry"],
                    "stop": p["stop"], "target": p["target"], "opened_t": p["opened_t"], "value": round(val, 2),
                    "pnl_pct": round((val * (1 - bot["fee"]) / p["cost"] - 1) * 100, 2), "reason": p["reason"]})
    return {
        "name": bot["name"], "style": bot["style"], "market": bot["market"], "team": team,
        "weight": round(weight, 1), "enabled": weight > 0, "equity": round(eq, 2), "net_in": round(a["net_in"], 2),
        "pnl": round(eq - a["net_in"], 2),
        "pnl_pct": round((eq / a["net_in"] - 1) * 100, 2) if a["net_in"] > 1 else 0.0,
        "cash": round(a["cash"], 2), "halted": a["halted"], "positions": pos,
        "trades": [dict(t, pair=disp(t["pair"])) for t in reversed(a["trades"][-30:])],
        "stats": stats(a["trades"], a["equity_curve"], max(a["net_in"], a.get("cap", 0.0))),
        "curve": downsample(a["equity_curve"]),
        "unavailable": [display(p) for p in unavailable],
        "scan": st.get("last_scan"),
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


def build(now, errors, pool, total, weights, suggestion, teams, bots, news):
    return {
        "mode": S.MODE, "updated_at": now, "currency": "EUR", "errors": errors,
        "pool": {"equity": round(total, 2), "start": pool["start"],
                 "pnl_pct": round((total / pool["start"] - 1) * 100, 2),
                 "unallocated": round(pool["unallocated"], 2), "weights": weights,
                 "rebalancing": pool["pending_runs"] > 0, "curve": downsample(pool["curve"]),
                 "suggestion": suggestion},
        "teams": teams, "bots": bots, "news": news,
    }
