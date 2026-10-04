"""pump.fun-Bots: durchsuchen bei jedem Lauf die aktiv gehandelten pump.fun-Coins und kaufen starke
Ausbrüche mit Volumen. Zwei Profile (in bots.py "scan"), damit man vergleichen kann, ob Filter helfen:

"safe" – vorsichtig (Bot „pump.fun“):
  nur Coins, die die Bonding-Curve verlassen haben (echter Liquiditätspool), Liquidität >= 40.000 $,
  Pool älter als 1 Stunde, Marktwert 200 Tsd.–100 Mio. $, Volumen >= 30.000 $/Std., mehr Käufe als Verkäufe.
"all" – alles (Bot „pump.fun Alles“):
  der ganze pump.fun-Markt, auch ganz neue Coins, die noch auf der Bonding-Curve handeln. Nur Mindestfilter
  (Liquidität und Volumen je >= 3.000 $, älter als 10 Minuten). Viel mehr Trades – aber: nicht einmal 2 % der
  pump.fun-Coins schaffen es von der Bonding-Curve weg, fast alle anderen sterben schnell.

Für beide: Bestätigung auf 5-Minuten-Kerzen (Ausbruch über das letzte Hoch mit Volumen), kein Wiedereinstieg in
denselben Coin für 12 Std., Gebühren ca. 1 % je Richtung (Bonding-Curve bzw. PumpSwap + Priority Fee) plus Kursabschlag.
"""
import time
import urllib.error

from ..data import dex as D
from ..strategies.indicators import ema
from . import account as E

COOLDOWN = 12 * 3600
DEAD_AFTER = 12              # so viele Läufe ohne Kursdaten -> Position gilt als wertlos (Rug)
_LISTS = ["/networks/solana/trending_pools?page=1", "/networks/solana/trending_pools?page=2",
          "/networks/solana/dexes/pumpswap/pools?page=1&sort=h24_volume_usd_desc",
          "/networks/solana/dexes/pumpswap/pools?page=2&sort=h24_volume_usd_desc"]
BONDING = ("pump-fun", "pumpfun")   # so heißt die Bonding-Curve bei GeckoTerminal bzw. DexScreener

PROFILES = {
    "safe": {"label": "Sicherheitsfilter", "lists": _LISTS, "bonding": False,
             "liq": 40_000, "vol_h1": 30_000, "age": 3600, "mcap": (200_000, 100_000_000), "buy_ratio": 1.1,
             "ch_h1": (5, 80), "min_candles": 30, "look": 12, "vol_mult": 2.0, "max_hold": 288, "calls": 9},
    "all": {"label": "Mindestfilter", "bonding": True,
            "lists": _LISTS + ["/networks/solana/trending_pools?page=1&duration=5m",
                               "/networks/solana/dexes/pump-fun/pools?page=1&sort=h24_volume_usd_desc",
                               "/networks/solana/new_pools?page=1"],
            "liq": 3_000, "vol_h1": 3_000, "age": 600, "mcap": (5_000, 1_000_000_000), "buy_ratio": 1.0,
            "ch_h1": (0, 1000), "min_candles": 8, "look": 6, "vol_mult": 1.5, "max_hold": 144, "calls": 8},
}


def profile(bot):
    return PROFILES[bot.get("scan", "safe")]


def scan(errors, prof):
    pools = {}
    for path in prof["lists"]:
        try:
            for p in D.gt_pools(path):
                pools.setdefault(p["mint"], p)
        except urllib.error.HTTPError as e:
            if e.code == 429:            # GeckoTerminal-Limit erreicht -> diesen Lauf keine weiteren Listen
                errors.append("pump.fun-Scan (GeckoTerminal): zu viele Anfragen")
                break
            continue                     # Liste gibt es nicht (mehr) -> nächste
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


def prefilter(p, now, prof=PROFILES["safe"]):
    lo, hi = prof["mcap"]
    c_lo, c_hi = prof["ch_h1"]
    return ((prof["bonding"] or p["dex"] not in BONDING) and p["liq"] >= prof["liq"] and p["vol_h1"] >= prof["vol_h1"]
            and now - p["created"] >= prof["age"] and lo <= p["mcap"] <= hi
            and p["buys"] >= p["sells"] * prof["buy_ratio"] and p["buys"] > 0 and c_lo <= p["ch_h1"] <= c_hi
            and p["ch_m5"] > 0 and p["price"] > 0)


def momentum_score(p):
    accel = p["vol_h1"] / max(p["vol_h6"] / 6, 1)
    return accel * min(p["buys"] / max(p["sells"], 1), 3) * (1 + min(p["ch_h1"], 300) / 100)


def confirm(c, prof=PROFILES["safe"]):
    """Bestätigung auf 5-Minuten-Kerzen: Ausbruch über das Hoch der letzten Kerzen mit Volumen, über EMA20."""
    n = prof["look"]
    if len(c) < max(prof["min_candles"], n + 1):
        return False
    cur = c[-1]
    hi = max(x["h"] for x in c[-n - 1:-1])
    avgv = sum(x["v"] for x in c[-n - 1:-1]) / n
    return cur["c"] > hi and cur["v"] > prof["vol_mult"] * avgv and cur["c"] > ema([x["c"] for x in c], 20)[-1]


def run(bot, st, rates, enabled, errors, gate=None):
    now = int(time.time())
    usd = rates.get("USD")
    if not usd:
        errors.append(f"{bot['name']}: EUR/USD-Kurs fehlt")
        return
    prof = profile(bot)
    accounts = [st["real"]] + st["shadows"]
    names = st.setdefault("names", {})
    misses = st.setdefault("misses", {})
    cool = st.setdefault("cooldown", {})
    for k in [k for k, t in cool.items() if now - t > COOLDOWN]:
        del cool[k]
    budget = prof["calls"]

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
    found = scan(errors, prof)
    cands = sorted((p for p in found if prefilter(p, now, prof) and p["pool"] not in cool
                    and not any(p["pool"] in a["positions"] for a in accounts)),
                   key=momentum_score, reverse=True)
    st["last_scan"] = {"t": now, "found": len(found), "passed": len(cands), "filter": prof["label"]}
    for p in cands:
        if budget <= 0:
            break
        budget -= 1
        try:
            closed, live = D.candles_5m(p["pool"])
        except Exception:
            continue
        if not confirm(closed, prof):
            continue
        names[p["pool"]] = p["symbol"]
        price = live["c"] or p["price"]
        stage = "Bonding-Curve" if p["dex"] in BONDING else f"Liq. {p['liq'] / 1000:.0f} Tsd. $"
        for vi, a in enumerate(accounts):
            is_real = vi == 0
            var = st["active"] if is_real else vi - 1
            v = bot["variants"][var]
            sig = {"stop": price * (1 - v["stop"]), "target": price * (1 + v["target"]), "trail_n": v["trail"],
                   "max_hold": prof["max_hold"], "variant": var,
                   "reason": f"Ausbruch, {p['ch_h1']:+.0f} % in 1 Std., {stage}"}
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
