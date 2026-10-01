"""Ein Durchlauf des Bots. Wird von GitHub Actions alle 30 Minuten gestartet."""
import json
import os
import sys
import time

from . import config as C
from . import engine as E
from .kraken import get_candles
from .strategies import SIGNALS, NAMES


def load(name):
    path = os.path.join(C.STATE_DIR, f"{name}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return E.new_account()


def save(name, acc):
    os.makedirs(C.STATE_DIR, exist_ok=True)
    with open(os.path.join(C.STATE_DIR, f"{name}.json"), "w") as f:
        json.dump(acc, f, indent=1)


def stats(acc):
    tr = acc["trades"]
    wins = [t for t in tr if t["pnl"] > 0]
    peak, mdd = acc["start"], 0.0
    for _, eq in acc["equity_curve"]:
        peak = max(peak, eq)
        mdd = max(mdd, (peak - eq) / peak)
    return {
        "trades": len(tr),
        "winrate": round(len(wins) / len(tr) * 100, 1) if tr else None,
        "max_drawdown_pct": round(mdd * 100, 2),
    }


def downsample(curve, n=300):
    if len(curve) <= n:
        return curve
    step = len(curve) / n
    return [curve[int(i * step)] for i in range(n)] + [curve[-1]]


def build_status(accounts, prices, now, errors):
    out = {"mode": C.MODE, "updated_at": now, "currency": "EUR", "strategies": {}, "errors": errors}
    tot_eq = tot_start = 0.0
    for name, acc in accounts.items():
        eq = E.equity(acc, prices)
        tot_eq += eq
        tot_start += acc["start"]
        out["strategies"][name] = {
            "name": NAMES[name],
            "equity": round(eq, 2),
            "start": acc["start"],
            "pnl_pct": round((eq / acc["start"] - 1) * 100, 2),
            "cash": round(acc["cash"], 2),
            "halted": acc["halted"],
            "positions": [
                {
                    "pair": p["pair"], "entry": p["entry"], "price": prices.get(p["pair"]),
                    "stop": p["stop"], "target": p["target"], "opened_t": p["opened_t"],
                    "value": round(p["qty"] * prices.get(p["pair"], p["entry"]), 2),
                    "pnl_pct": round((prices.get(p["pair"], p["entry"]) * (1 - C.FEE_RATE) * p["qty"] / p["cost"] - 1) * 100, 2),
                    "reason": p["reason"],
                }
                for p in acc["positions"].values()
            ],
            "trades": list(reversed(acc["trades"][-30:])),
            "stats": stats(acc),
            "curve": downsample(acc["equity_curve"]),
        }
    out["total"] = {"equity": round(tot_eq, 2), "start": tot_start,
                    "pnl_pct": round((tot_eq / tot_start - 1) * 100, 2) if tot_start else 0}
    return out


def run():
    if C.MODE != "paper":
        sys.exit("Echtgeld-Modus ist noch nicht freigeschaltet. Erst Demo auswerten!")
    now = int(time.time())
    accounts = {s: load(s) for s in C.STRATEGIES}
    prices, errors = {}, []

    for pair, code in C.PAIRS.items():
        try:
            closed, live = get_candles(code, C.CANDLE_MINUTES)
        except Exception as e:
            errors.append(f"{pair}: {e}")
            continue
        prices[pair] = live["c"]
        live_k = dict(live, closed=False)
        signal_t = closed[-1]["t"]
        for name, acc in accounts.items():
            # 1) offene Position prüfen (Stop / Ziel / Einstand)
            E.manage(acc, pair, closed[-50:] + [live_k])
            # 2) neues Signal nur einmal pro abgeschlossener Kerze auswerten
            if acc["last_signal_t"].get(pair, 0) >= signal_t:
                continue
            acc["last_signal_t"][pair] = signal_t
            sig = SIGNALS[name](closed)
            if sig and E.try_open(acc, pair, sig, live["c"], now, prices):
                print(f"[{name}] KAUF {pair} @ {live['c']} – {sig['reason']}")

    for name, acc in accounts.items():
        eq = E.update_risk_state(acc, prices)
        acc["equity_curve"].append([now, round(eq, 2)])
        acc["equity_curve"] = acc["equity_curve"][-5000:]
        save(name, acc)
        print(f"[{name}] Guthaben {eq:.2f} EUR, offen: {list(acc['positions'])}")

    status = build_status(accounts, prices, now, errors)
    os.makedirs(os.path.dirname(C.STATUS_FILE), exist_ok=True)
    with open(C.STATUS_FILE, "w") as f:
        json.dump(status, f, separators=(",", ":"))
    if errors:
        print("Fehler:", errors)


if __name__ == "__main__":
    run()
