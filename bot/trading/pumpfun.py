"""pump.fun-Bot: durchsucht bei jedem Lauf die aktiv gehandelten pump.fun-Coins
(Trend-Listen, Top-Volumen auf PumpSwap, auf DexScreener beworbene Coins), filtert
riskante Kandidaten aus und kauft nur starke Ausbrüche mit Volumen.

Sicherheitsfilter (98 % der pump.fun-Coins sind Betrug oder sterben schnell):
- nur Coins, die die Bonding-Curve verlassen haben (echter Liquiditätspool)
- Liquidität >= 40.000 $, Pool älter als 1 Stunde, Marktwert 200 Tsd.–100 Mio. $
- mehr Käufe als Verkäufe in der letzten Stunde, Volumen >= 30.000 $/Std.
- kein Wiedereinstieg in denselben Coin innerhalb von 12 Stunden
Gebühren (DEX-Gebühr, Priority Fee, Preis-Einfluss) werden mit 1 % je Richtung angesetzt.
"""
import time

from ..data import dex as D
from ..strategies.indicators import ema
from . import account as E

MAX_OHLCV_CALLS = 9          # GeckoTerminal-Limit schonen
COOLDOWN = 12 * 3600
DEAD_AFTER = 12              # so viele Läufe ohne Kursdaten -> Position gilt als wertlos (Rug)


def scan(errors):
    pools = {}
    for path in ("/networks/solana/trending_pools?page=1", "/networks/solana/trending_pools?page=2",
                 "/networks/solana/dexes/pumpswap/pools?page=1&sort=h24_volume_usd_desc",
                 "/networks/solana/dexes/pumpswap/pools?page=2&sort=h24_volume_usd_desc"):
        try:
            for p in D.gt_pools(path):
                pools.setdefault(p["mint"], p)
        except Exception as e:
            errors.append(f"pump.fun-Scan (GeckoTerminal): {e}")
            break
    try:
        mints = [m for m in D.ds_trending_mints() if m.endswith("pump")]
        for i in range(0, min(len(mints), 90), 30):
            for p in D.ds_tokens(mints[i:i + 30]):
                pools.setdefault(p["mint"], p)
    except Exception as e:
        errors.append(f"pump.fun-Scan (DexScreener): {e}")
    return [p for p in pools.values() if p["mint"].endswith("pump") and p["pool"]]


def prefilter(p, now):
    return (p["dex"] not in ("pump-fun", "pumpfun") and p["liq"] >= 40_000 and p["vol_h1"] >= 30_000
            and now - p["created"] >= 3600 and 200_000 <= p["mcap"] <= 100_000_000
            and p["buys"] > p["sells"] * 1.1 and 5 <= p["ch_h1"] <= 80 and p["ch_m5"] > 0 and p["price"] > 0)


def momentum_score(p):
    accel = p["vol_h1"] / max(p["vol_h6"] / 6, 1)
    return accel * min(p["buys"] / max(p["sells"], 1), 3) * (1 + p["ch_h1"] / 100)


def confirm(c):
    """Bestätigung auf 5-Minuten-Kerzen: Ausbruch über das 1-Stunden-Hoch mit Volumen."""
    if len(c) < 30:
        return False
    cur = c[-1]
    hi = max(x["h"] for x in c[-13:-1])
    avgv = sum(x["v"] for x in c[-13:-1]) / 12
    return cur["c"] > hi and cur["v"] > 2 * avgv and cur["c"] > ema([x["c"] for x in c], 20)[-1]


def run(bot, st, rates, enabled, errors, gate=None):
    now = int(time.time())
    usd = rates.get("USD")
    if not usd:
        errors.append("pump.fun: EUR/USD-Kurs fehlt")
        return
    accounts = [st["real"]] + st["shadows"]
    names = st.setdefault("names", {})
    misses = st.setdefault("misses", {})
    cool = st.setdefault("cooldown", {})
    for k in [k for k, t in cool.items() if now - t > COOLDOWN]:
        del cool[k]
    budget = MAX_OHLCV_CALLS

    # 1) offene Positionen mit 5-Minuten-Kerzen nachspielen (Stop, Ziel, Trailing, Zeitablauf)
    held = sorted({pool for a in accounts for pool in a["positions"]},
                  key=lambda x: min(a["last_t"].get(x, 0) for a in accounts if x in a["positions"]))
    for pool in held:
        if budget <= 0:
            break
        budget -= 1
        try:
            closed, live = D.candles_5m(pool)
            misses[pool] = 0
        except Exception:
            misses[pool] = misses.get(pool, 0) + 1
            if misses[pool] >= DEAD_AFTER:
                for a in accounts:
                    if pool in a["positions"]:
                        p = a["positions"][pool]
                        E.close_position(a, bot, pool, p["entry"] * 0.05, now, usd, "Keine Kurse mehr (Rug?)")
            continue
        for a in accounts:
            if pool not in a["positions"]:
                continue
            for i, k in enumerate(closed):
                if k["t"] > a["last_t"].get(pool, 0) and pool in a["positions"]:
                    E.manage(a, bot, pool, closed, i, usd)
                    a["last_t"][pool] = k["t"]
                    a["marks"][pool] = k["c"] * usd
            if pool in a["positions"]:
                a["marks"][pool] = live["c"] * usd
            else:
                cool[pool] = now

    # 2) Markt scannen und die besten Kandidaten prüfen
    found = scan(errors)
    cands = sorted((p for p in found if prefilter(p, now) and p["pool"] not in cool
                    and not any(p["pool"] in a["positions"] for a in accounts)),
                   key=momentum_score, reverse=True)
    st["last_scan"] = {"t": now, "found": len(found), "passed": len(cands)}
    for p in cands:
        if budget <= 0:
            break
        budget -= 1
        try:
            closed, live = D.candles_5m(p["pool"])
        except Exception:
            continue
        if not confirm(closed):
            continue
        names[p["pool"]] = p["symbol"]
        price = live["c"] or p["price"]
        for vi, a in enumerate(accounts):
            is_real = vi == 0
            var = st["active"] if is_real else vi - 1
            v = bot["variants"][var]
            sig = {"stop": price * (1 - v["stop"]), "target": price * (1 + v["target"]), "trail_n": v["trail"],
                   "max_hold": 288, "variant": var,
                   "reason": f"Ausbruch, {p['ch_h1']:+.0f} % in 1 Std., Liq. {p['liq'] / 1000:.0f} Tsd. $"}
            if is_real and not enabled:
                continue
            if not a["halted"] and len(a["positions"]) < bot["max_pos"]:
                m = (gate(p["pool"], sig, now) if gate else 1.0) if is_real else 1.0
                if m <= 0:
                    continue
                E.open_position(a, bot, p["pool"], sig, price, now, usd, m)
                if p["pool"] in a["positions"]:
                    a["last_t"][p["pool"]] = live["t"]
                    a["marks"][p["pool"]] = price * usd
        cool[p["pool"]] = now
    # Namen aufräumen
    keep = {pool for a in accounts for pool in a["positions"]} | {t["pair"] for t in st["real"]["trades"][-30:]}
    st["names"] = {k: v for k, v in names.items() if k in keep or k in cool}
