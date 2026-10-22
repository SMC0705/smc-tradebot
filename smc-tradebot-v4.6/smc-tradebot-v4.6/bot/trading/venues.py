"""Börsen & Kosten: Wo wird ein Wert gehandelt und was kostet ein Kauf bzw. Verkauf dort?
- Krypto: Revolut X (0 % Maker, 0,09 % Taker), wenn der Coin dort in EUR eng gehandelt wird
  (Geld-Brief-Spanne <= settings.MAX_SPREAD). Sonst Kraken (Gebührenstufe settings.KRAKEN_TIER).
- Aktien-Token und Devisen: Kraken. pump.fun: Solana-DEX.
Jede Position merkt sich beim Kauf ihre Börse und Kosten – der Verkauf wird mit denselben gerechnet."""
from .. import settings as S
from ..data import revolutx
from ..markets import FOREX


def fee_class(bot, pair):
    if bot.get("source") == "pumpfun":
        return "dex"
    if pair in FOREX:
        return "fx"
    if pair.endswith("xUSD"):      # Kraken xStocks (Aktien-Token)
        return "xstocks"
    return "crypto"


def venue(bot, pair):
    """{"name", "maker", "taker", "slip", "spread"} für diesen Wert (Gebühren je Richtung)."""
    cls = fee_class(bot, pair)
    if cls == "crypto" and S.CRYPTO_VENUE == "revolutx":
        q = revolutx.quote(pair)
        if q and q["spread"] <= S.MAX_SPREAD:
            v = S.VENUES["revolutx"]
            return {"name": "revolutx", "maker": v["maker"], "taker": v["taker"],
                    "slip": max(S.MIN_SLIP, q["spread"] / 2), "spread": q["spread"]}
    f = S.FEES[cls]
    q = revolutx.quote(pair) if cls == "crypto" else None
    return {"name": "dex" if cls == "dex" else "kraken", "maker": f["maker"], "taker": f["taker"],
            "slip": bot["slip"], "spread": q["spread"] if q else None}


def label(name):
    return S.VENUES.get(name, {}).get("label", name)
