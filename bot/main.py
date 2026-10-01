"""Ein Durchlauf aller Bots. Wird von GitHub Actions alle 30 Minuten gestartet."""
import json
import os
import sys
import time

from . import config as C
from . import engine as E
from . import learning as L
from . import pool as P
from .kraken import get_candles

WARMUP = 500  # Schatten-Varianten lernen beim ersten Start aus bis zu 500 vergangenen Kerzen


def _read(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def _write(path, data, **kw):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, **kw)


def bot_path(b):
    return os.path.join(C.STATE_DIR, f"{b}.json")


def new_bot_state(bot):
    return {"real": E.new_account(0.0), "active": 0, "log": [], "pair_mult": {},
            "shadows": [dict(E.new_account(L.SHADOW_CASH), lean=True) for _ in bot["variants"]]}


def variant_label(i):
    return "ABCDEFG"[i]


def fx_rates(errors):
    """EUR je Einheit der Kurswährung."""
    rates = {"EUR": 1.0}
    try:
        eurusd = get_candles("EURUSD", 240)[1]["c"]
    except Exception:
        try:  # Ersatz: über Bitcoin-Kurse in USD und EUR
            eurusd = get_candles("XBTUSD", 60)[1]["c"] / get_candles("XBTEUR", 60)[1]["c"]
        except Exception as e:
            errors.append(f"EUR/USD-Kurs fehlt: {e}")
            return rates
    rates["USD"] = 1 / eurusd
    for cur in ("JPY", "CHF", "CAD"):
        try:
            rates[cur] = rates["USD"] / get_candles(f"USD{cur}", 240)[1]["c"]
        except Exception:
            pass
    return rates


def run_bot(bid, bot, st, rates, enabled, errors, unavailable):
    labels = [variant_label(i) for i in range(len(bot["variants"]))]
    for pair in bot["pairs"]:
        quote = pair[-3:]
        if quote not in rates:
            unavailable.append(pair)
            continue
        try:
            closed, live = get_candles(pair, bot["tf"], bot["aclass"])
        except Exception as e:
            unavailable.append(pair)
            if not isinstance(e, ValueError):
                errors.append(f"{bot['name']} {C.display(pair)}: {e}")
            continue
        rate = rates[quote]
        # 1) Schatten-Varianten (lernen; beim ersten Mal aus der Vergangenheit)
        for vi, sh in enumerate(st["shadows"]):
            E.process(sh, bot, pair, closed, rate, bot["variants"][vi], vi,
                      start_from=max(len(closed) - WARMUP, 0))
            sh["marks"][pair] = live["c"] * rate
        # 2) echtes Konto folgt der aktiven Variante, Risiko je Paar angepasst
        mult = L.pair_multiplier(st, pair, st["real"]["trades"])
        act = st["active"]
        E.process(st["real"], bot, pair, closed, rate, bot["variants"][act], act, mult=mult, can_open=enabled)
        st["real"]["marks"][pair] = live["c"] * rate
    return L.choose_variant(st, labels)


def stats(trades, curve, net_in):
    wins = [t for t in trades if t["pnl"] > 0]
    peak, mdd = 0.0, 0.0
    for _, pnl in curve:  # Kurve = Gewinn/Verlust in EUR (Umbuchungen zählen nicht)
        peak = max(peak, pnl)
        if net_in > 1:
            mdd = max(mdd, (peak - pnl) / net_in)
    return {"trades": len(trades), "winrate": round(len(wins) / len(trades) * 100, 1) if trades else None,
            "avg_r": round(sum(t["r"] for t in trades) / len(trades), 2) if trades else None,
            "max_drawdown_pct": round(mdd * 100, 2)}


def downsample(curve, n=200):
    if len(curve) <= n:
        return curve
    step = len(curve) / n
    return [curve[int(i * step)] for i in range(n)] + [curve[-1]]


def bot_status(bid, bot, st, weight, scores, unavailable):
    a = st["real"]
    eq = E.equity(a)
    trades = [dict(t, pair=C.display(t["pair"])) for t in reversed(a["trades"][-30:])]
    pos = []
    for p in a["positions"].values():
        val = p["qty"] * a["marks"].get(p["pair"], p["entry"] * p["rate"])
        pos.append({"pair": C.display(p["pair"]), "entry": p["entry"], "stop": p["stop"], "target": p["target"],
                    "opened_t": p["opened_t"], "value": round(val, 2),
                    "pnl_pct": round((val * (1 - bot["fee"]) / p["cost"] - 1) * 100, 2), "reason": p["reason"]})
    return {
        "name": bot["name"], "style": bot["style"], "market": bot["market"], "weight": round(weight, 1),
        "enabled": weight > 0, "equity": round(eq, 2), "net_in": round(a["net_in"], 2),
        "pnl": round(eq - a["net_in"], 2),
        "pnl_pct": round((eq / a["net_in"] - 1) * 100, 2) if a["net_in"] > 1 else 0.0,
        "cash": round(a["cash"], 2), "halted": a["halted"], "positions": pos, "trades": trades,
        "stats": stats(a["trades"], a["equity_curve"], max(a["net_in"], a.get("cap", 0.0))),
        "curve": downsample(a["equity_curve"]),
        "unavailable": [C.display(p) for p in unavailable],
        "learning": {
            "active": variant_label(st["active"]),
            "variants": [{"label": variant_label(i), "params": bot["variants"][i], "trades": s[1],
                          "avg_r": round(s[2], 2), "score": round(s[0], 3)} for i, s in enumerate(scores)],
            "paused": [C.display(p) for p, m in st["pair_mult"].items() if m == 0],
            "log": list(reversed(st["log"][-10:])),
        },
    }


def run():
    if C.MODE != "paper":
        sys.exit("Echtgeld-Modus ist noch nicht freigeschaltet. Erst Demo auswerten!")
    now = int(time.time())
    errors = []
    weights = P.load_weights()
    pool = _read(os.path.join(C.STATE_DIR, "pool.json"), None) or P.new_pool()
    states = {b: _read(bot_path(b), None) or new_bot_state(bot) for b, bot in C.BOTS.items()}

    rates = fx_rates(errors)
    all_scores, unav = {}, {}
    for b, bot in C.BOTS.items():
        unav[b] = []
        t0 = time.time()
        all_scores[b] = run_bot(b, bot, states[b], rates, weights[b] > 0, errors, unav[b])
        print(f"[{b}] fertig in {time.time() - t0:.1f}s")

    accounts = {b: s["real"] for b, s in states.items()}
    for b, amt in P.rebalance(pool, accounts, weights):
        print(f"Umbuchung {b}: {amt:+.2f} EUR")

    total = pool["unallocated"]
    for b, s in states.items():
        eq = E.update_risk(s["real"])
        total += eq
        s["real"]["equity_curve"] = (s["real"]["equity_curve"] + [[now, round(eq - s["real"]["net_in"], 2)]])[-3000:]
        for sh in s["shadows"]:
            sh["equity_curve"] = []  # Schatten brauchen keine Kurve
        _write(bot_path(b), s, separators=(",", ":"))
    pool["curve"] = (pool["curve"] + [[now, round(total, 2)]])[-3000:]
    _write(os.path.join(C.STATE_DIR, "pool.json"), pool, separators=(",", ":"))

    status = {
        "mode": C.MODE, "updated_at": now, "currency": "EUR", "errors": errors,
        "pool": {"equity": round(total, 2), "start": pool["start"],
                 "pnl_pct": round((total / pool["start"] - 1) * 100, 2),
                 "unallocated": round(pool["unallocated"], 2), "weights": weights,
                 "rebalancing": pool["pending_runs"] > 0, "curve": downsample(pool["curve"])},
        "bots": {b: bot_status(b, C.BOTS[b], states[b], weights[b], all_scores[b], unav[b]) for b in C.BOTS},
    }
    _write(C.STATUS_FILE, status, separators=(",", ":"))
    print(f"Sammelkonto: {total:.2f} EUR | Fehler: {errors or 'keine'}")


if __name__ == "__main__":
    run()
