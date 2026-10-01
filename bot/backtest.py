"""Backtest auf historischen Kraken-Kerzen (oder synthetischen Daten zum Testen).
Aufruf: python -m bot.backtest          (holt die letzten 720 Stunden-Kerzen von Kraken)
"""
import random
import sys

from . import config as C
from . import engine as E
from .strategies import SIGNALS, NAMES


def synthetic(n=3000, seed=1, p0=100.0):
    rnd = random.Random(seed)
    out, p, drift, t = [], p0, 0.0, 1_700_000_000
    for i in range(n):
        if i % 200 == 0:
            drift = rnd.uniform(-0.0012, 0.0015)
        o = p
        c = o * (1 + drift + rnd.gauss(0, 0.008))
        h = max(o, c) * (1 + abs(rnd.gauss(0, 0.003)))
        l = min(o, c) * (1 - abs(rnd.gauss(0, 0.003)))
        out.append({"t": t, "o": o, "h": h, "l": l, "c": c, "v": 1})
        p, t = c, t + 3600
    return out


def backtest(data):
    """data: {pair: candles}. Einstieg zum Eröffnungskurs der nächsten Kerze."""
    res = {}
    for name, fn in SIGNALS.items():
        acc = E.new_account()
        n = min(len(v) for v in data.values())
        for i in range(210, n - 1):
            prices = {pair: cs[i]["c"] for pair, cs in data.items()}
            for pair, cs in data.items():
                E.manage(acc, pair, [cs[i]])
                sig = fn(cs[: i + 1])
                if sig:
                    E.try_open(acc, pair, sig, cs[i + 1]["o"], cs[i]["t"], prices)
            acc["equity_curve"].append([cs[i]["t"], E.update_risk_state(acc, prices)])
        prices = {pair: cs[n - 1]["c"] for pair, cs in data.items()}
        eq = E.equity(acc, prices)
        tr = acc["trades"]
        wins = sum(1 for t in tr if t["pnl"] > 0)
        res[name] = (eq, len(tr), wins)
        print(f"{NAMES[name]:<11} Ende {eq:9.2f} EUR ({(eq/acc['start']-1)*100:+.1f} %) | "
              f"Trades {len(tr)} | Gewinner {wins} | offen {len(acc['positions'])}")
    return res


if __name__ == "__main__":
    if "--synthetic" in sys.argv:
        data = {f"SYN{s}": synthetic(seed=s) for s in range(4)}
    else:
        from .kraken import get_candles
        data = {pair: get_candles(code, C.CANDLE_MINUTES)[0] for pair, code in C.PAIRS.items()}
    backtest(data)
