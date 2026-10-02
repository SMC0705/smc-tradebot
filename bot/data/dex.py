"""Kostenlose On-Chain-Marktdaten für Solana/pump.fun:
- DexScreener (Scan, großzügige Limits)
- GeckoTerminal (Kerzen, ohne Schlüssel max. ~10 Anfragen/Minute)
"""
from datetime import datetime

from . import http

GT = "https://api.geckoterminal.com/api/v2"
DS = "https://api.dexscreener.com"
_gap = {"gt": 6.5, "ds": 1.1}


def _get(src, url):
    return http.get_json(url, src, gap=_gap[src])


def _f(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _ts(iso):
    try:
        return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())
    except Exception:
        return 0


def gt_pools(path):
    """GeckoTerminal-Poolliste -> einheitliches Format."""
    out = []
    for p in _get("gt", f"{GT}{path}").get("data", []):
        a, rel = p.get("attributes", {}), p.get("relationships", {})
        mint = rel.get("base_token", {}).get("data", {}).get("id", "").replace("solana_", "")
        tx = a.get("transactions", {}).get("h1", {}) or {}
        out.append({
            "pool": a.get("address"), "mint": mint, "symbol": (a.get("name") or "?").split(" / ")[0],
            "dex": rel.get("dex", {}).get("data", {}).get("id", ""), "price": _f(a.get("base_token_price_usd")),
            "liq": _f(a.get("reserve_in_usd")), "vol_h1": _f(a.get("volume_usd", {}).get("h1")),
            "vol_h6": _f(a.get("volume_usd", {}).get("h6")),
            "ch_m5": _f(a.get("price_change_percentage", {}).get("m5")),
            "ch_h1": _f(a.get("price_change_percentage", {}).get("h1")),
            "buys": int(_f(tx.get("buys"))), "sells": int(_f(tx.get("sells"))),
            "created": _ts(a.get("pool_created_at") or ""),
            "mcap": _f(a.get("market_cap_usd")) or _f(a.get("fdv_usd")),
        })
    return out


def ds_tokens(mints):
    """DexScreener: Paare für bis zu 30 Token-Adressen -> je Token das liquideste Paar."""
    best = {}
    for p in _get("ds", f"{DS}/tokens/v1/solana/{','.join(mints[:30])}") or []:
        bt = p.get("baseToken", {})
        tx = p.get("txns", {}).get("h1", {}) or {}
        item = {
            "pool": p.get("pairAddress"), "mint": bt.get("address", ""), "symbol": bt.get("symbol", "?"),
            "dex": p.get("dexId", ""), "price": _f(p.get("priceUsd")), "liq": _f((p.get("liquidity") or {}).get("usd")),
            "vol_h1": _f((p.get("volume") or {}).get("h1")), "vol_h6": _f((p.get("volume") or {}).get("h6")),
            "ch_m5": _f((p.get("priceChange") or {}).get("m5")), "ch_h1": _f((p.get("priceChange") or {}).get("h1")),
            "buys": int(_f(tx.get("buys"))), "sells": int(_f(tx.get("sells"))),
            "created": int(_f(p.get("pairCreatedAt")) / 1000), "mcap": _f(p.get("marketCap")) or _f(p.get("fdv")),
        }
        if item["mint"] and (item["mint"] not in best or item["liq"] > best[item["mint"]]["liq"]):
            best[item["mint"]] = item
    return list(best.values())


def ds_trending_mints():
    """Solana-Token, die auf DexScreener gerade beworben werden oder neue Profile haben."""
    mints = []
    for path in ("/token-boosts/top/v1", "/token-boosts/latest/v1", "/token-profiles/latest/v1"):
        try:
            for x in _get("ds", f"{DS}{path}") or []:
                if x.get("chainId") == "solana" and x.get("tokenAddress"):
                    mints.append(x["tokenAddress"])
        except Exception:
            pass
    return list(dict.fromkeys(mints))


def candles_5m(pool):
    """5-Minuten-Kerzen eines Pools (älteste zuerst). Gibt (abgeschlossene, aktuelle) zurück."""
    d = _get("gt", f"{GT}/networks/solana/pools/{pool}/ohlcv/minute?aggregate=5&limit=150&currency=usd")
    rows = d.get("data", {}).get("attributes", {}).get("ohlcv_list", [])
    cs = sorted(({"t": int(r[0]), "o": _f(r[1]), "h": _f(r[2]), "l": _f(r[3]), "c": _f(r[4]), "v": _f(r[5])}
                 for r in rows), key=lambda k: k["t"])
    if len(cs) < 2:
        raise ValueError("keine Kerzen")
    return cs[:-1], cs[-1]
