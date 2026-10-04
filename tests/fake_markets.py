"""Künstliche Märkte und Nachrichten für Tests – ersetzt alle Internet-Abrufe.
Die Kurse sind Zufallsbewegungen mit wechselnden Trends: Gewinne/Verluste darin sagen NICHTS über
echte Märkte aus. Es geht nur darum, dass der Code fehlerfrei läuft und die Regeln greifen."""
import hashlib
import random
import time

from bot.data import dex, kraken, news

T0 = 1_780_000_000 - (1_780_000_000 % 86400)   # fester Startzeitpunkt (Mitternacht UTC)
NOW = [T0]
_series = {}
FX_BASE = {"EURUSD": 1.08, "USDJPY": 150, "USDCHF": 0.9, "USDCAD": 1.36, "GBPUSD": 1.27, "AUDUSD": 0.66}
MISSING = {"BONKEUR", "GDxUSD"}                  # so tun, als gäbe es diese Paare bei Kraken nicht


def _seed(*parts):
    return int(hashlib.md5("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


def _gen(pair, tf, n):
    r = random.Random(_seed(pair, tf))
    p = FX_BASE.get(pair, r.uniform(0.5, 500))
    vol = 0.0006 if pair in FX_BASE else 0.004 * (tf / 60) ** 0.5
    out, drift, start = [], 0.0, T0 - 720 * tf * 60
    for i in range(n):
        if i % 150 == 0:
            drift = r.uniform(-0.3, 0.4) * vol
        o = p
        c = o * (1 + drift + r.gauss(0, vol))
        out.append({"t": start + i * tf * 60, "o": o, "h": max(o, c) * (1 + abs(r.gauss(0, vol / 3))),
                    "l": min(o, c) * (1 - abs(r.gauss(0, vol / 3))), "c": c,
                    "v": r.expovariate(1) * (4 if r.random() < 0.05 else 1)})
        p = c
    return out


def get_candles(pair, interval, aclass=None):
    if pair in MISSING:
        raise ValueError("Unknown asset pair")
    key = (pair, interval)
    if key not in _series:
        _series[key] = _gen(pair, interval, 720 + 10 * 86400 // (interval * 60) + 10)
    cs = [c for c in _series[key] if c["t"] <= NOW[0]][-721:]
    return cs[:-1], cs[-1]


# --- pump.fun -------------------------------------------------------------------
_rnd = random.Random(7)
TOKENS = [f"Mint{i:03d}xxxxxxxxxxxxxxxxxxpump" for i in range(40)]


def _pools(_path=""):
    if "pump-fun" in _path or "new_pools" in _path:   # junge Coins, die noch auf der Bonding-Curve handeln
        return [{"pool": "Curve" + m[:7], "mint": m, "symbol": f"NEU{i}", "dex": "pump-fun", "price": 0.00001 * (i + 1),
                 "liq": _rnd.uniform(4e3, 30e3), "vol_h1": _rnd.uniform(4e3, 60e3), "vol_h6": _rnd.uniform(10e3, 120e3),
                 "ch_m5": _rnd.uniform(-5, 15), "ch_h1": _rnd.uniform(-20, 200), "buys": _rnd.randint(30, 300),
                 "sells": _rnd.randint(20, 250), "created": NOW[0] - _rnd.randint(900, 4 * 3600),
                 "mcap": _rnd.uniform(1e4, 9e4)} for i, m in enumerate(TOKENS[25:40])]
    return [{"pool": "Pool" + m[:7], "mint": m, "symbol": f"MEME{i}", "dex": "pumpswap", "price": 0.001 * (i + 1),
             "liq": _rnd.uniform(10e3, 300e3), "vol_h1": _rnd.uniform(5e3, 200e3), "vol_h6": _rnd.uniform(50e3, 600e3),
             "ch_m5": _rnd.uniform(-5, 8), "ch_h1": _rnd.uniform(-20, 60), "buys": _rnd.randint(50, 400),
             "sells": _rnd.randint(50, 300), "created": NOW[0] - _rnd.randint(600, 10 * 86400),
             "mcap": _rnd.uniform(1e5, 5e6)} for i, m in enumerate(TOKENS[:25])]


def _candles_5m(pool):
    r, p, out, start = random.Random(_seed(pool)), 1.0, [], T0 - 150 * 300
    for i in range(150 + (NOW[0] - T0) // 300):
        o = p
        c = o * (1 + r.gauss(0.002, 0.03))
        out.append({"t": start + i * 300, "o": o, "h": max(o, c) * 1.01, "l": min(o, c) * 0.99, "c": c,
                    "v": r.expovariate(1) * (5 if r.random() < 0.15 else 1)})
        p = c
    cs = [x for x in out if x["t"] <= NOW[0]][-150:]
    return cs[:-1], cs[-1]


# --- Nachrichten ------------------------------------------------------------------
HEADLINES = [
    ("BBC World", "Missile strikes hit port as war escalates"), ("Tagesschau", "Raketenangriff auf Ölraffinerie"),
    ("Reuters", "Oil jumps as Opec signals supply cuts after attack"), ("Tagesschau", "Leitzins: EZB hält still"),
    ("CoinDesk", "Solana-based exchange hacked, $40M stolen"), ("BBC Business", "Stocks steady ahead of earnings"),
    ("Deutsche Welle", "Ceasefire talks resume in Geneva"), ("Reuters", "US announces new tariffs on imports"),
]


def _news(errors, cache=None):
    r = random.Random(_seed("news", NOW[0] // 1800))
    k = (NOW[0] - T0) // 1800
    heavy = 10 <= k <= 20                     # in Lauf 10–20 gibt es eine "Krise"
    items = [{"src": s, "title": t, "link": "https://example.org", "t": NOW[0] - r.randint(0, 5 * 3600)}
             for s, t in HEADLINES if r.random() < (0.9 if heavy else 0.25)]
    if heavy:
        items += [{"src": "Reuters", "title": f"Airstrike reported near border ({i})", "link": "", "t": NOW[0] - 600 * i}
                  for i in range(5)]
    spike = 2.8 if heavy else round(r.uniform(0.7, 1.3), 2)
    return {"headlines": items, "gdelt": {"krieg": {"recent": 50, "base": 20, "spike": spike},
                                          "oel": {"recent": 10, "base": 10, "spike": 1.0}},
            "fear_greed": {"value": r.randint(20, 85), "label": "Test"}, "termine": news.load_termine(),
            "ok": ["Test-Quelle"], "failed": [], "fetched": NOW[0]}


def install():
    """Alle Datenquellen durch Testdaten ersetzen und die Uhr kontrollierbar machen."""
    kraken.get_candles = get_candles
    dex.gt_pools, dex.ds_trending_mints = _pools, (lambda: TOKENS[20:])
    dex.ds_tokens = lambda ms: [p for p in _pools() if p["mint"] in ms]
    dex.candles_5m = _candles_5m
    news.collect = _news
    time.time = lambda: NOW[0]


def set_run(k):
    NOW[0] = T0 + k * 1800 + 60      # Lauf k = alle 30 Minuten
