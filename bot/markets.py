"""MÄRKTE: welche Werte gehandelt werden, wie sie in der App heißen und zu welchen
Nachrichten-Themen sie gehören. Paare, die Kraken nicht anbietet, werden automatisch
übersprungen und in der App angezeigt – man kann hier also gefahrlos Kandidaten eintragen.
"""
# Kraken-Paarnamen
CRYPTO = ["XBTEUR", "ETHEUR", "LTCEUR", "SOLEUR", "XRPEUR", "ADAEUR", "DOTEUR", "LINKEUR", "AVAXEUR", "ATOMEUR"]
MEMES = ["DOGEEUR", "SHIBEUR", "PEPEEUR", "BONKEUR", "WIFEUR", "FLOKIEUR"]
FOREX = ["EURUSD", "GBPUSD", "AUDUSD", "USDJPY", "USDCHF", "USDCAD"]
# Kraken xStocks (Aktien als Token): KI-/Tech-Werte, Palantir und Indizes
STOCKS = ["NVDAxUSD", "PLTRxUSD", "MSFTxUSD", "GOOGLxUSD", "METAxUSD", "AMZNxUSD", "AAPLxUSD", "AMDxUSD",
          "AVGOxUSD", "TSMxUSD", "ORCLxUSD", "ARMxUSD", "CRWDxUSD", "INTCxUSD", "TSLAxUSD", "SPYxUSD", "QQQxUSD"]
# Krisen-Werte (Kraken xStocks + PAXG). Einzelne Rüstungsaktien (Lockheed, RTX, Northrop, General Dynamics)
# und der Öl-ETF USO gibt es bei Kraken nicht – der Rüstungs-ETF ITA enthält sie aber alle.
CRISIS = [
    "PAXGEUR", "GLDxUSD", "GDXxUSD",                       # Gold, Gold-ETF, Goldminen-ETF
    "ITAxUSD", "XARxUSD", "SHLDxUSD", "LHXxUSD", "BAxUSD",  # Rüstung: ETFs (ITA, XAR, SHLD) und Einzelwerte
    "XOMxUSD", "CVXxUSD", "BKRxUSD", "XLExUSD", "OXYxUSD", "SLBxUSD",  # Öl & Energie
]

# Zu welchen Nachrichten-Themen ein Krisen-Wert passt (siehe settings.THEMES)
_GOLD, _WAR, _OIL = ["krieg", "crash", "zoelle"], ["krieg"], ["oel", "krieg"]
ASSET_THEMES = {
    **{p: _GOLD for p in ("PAXGEUR", "GLDxUSD", "GDXxUSD")},
    **{p: _WAR for p in ("ITAxUSD", "XARxUSD", "SHLDxUSD", "LHXxUSD", "BAxUSD")},
    **{p: _OIL for p in ("XOMxUSD", "CVXxUSD", "BKRxUSD", "XLExUSD", "OXYxUSD", "SLBxUSD")},
}

# Woran man einen Coin in Schlagzeilen erkennt (für Hack-/Klage-Warnungen)
COIN_WORDS = {
    "XBTEUR": ["bitcoin", "btc"], "ETHEUR": ["ethereum", "ether"], "SOLEUR": ["solana"],
    "XRPEUR": ["xrp", "ripple"], "LTCEUR": ["litecoin"], "DOGEEUR": ["dogecoin"], "SHIBEUR": ["shiba"],
    "PEPEEUR": ["pepe"], "BONKEUR": ["bonk"], "WIFEUR": ["dogwifhat"], "FLOKIEUR": ["floki"],
    "ADAEUR": ["cardano"], "DOTEUR": ["polkadot"], "LINKEUR": ["chainlink"], "AVAXEUR": ["avalanche"],
    "ATOMEUR": ["cosmos"],
}

# Marktlage-Quellen des Analysten
REGIME_NAMES = {"XBTEUR": "Bitcoin", "SOLEUR": "Solana", "SPYxUSD": "S&P 500"}

NAMES = {"PAXGEUR": "Gold (PAXG)/EUR", "GLDxUSD": "Gold-ETF GLD/USD", "GDXxUSD": "Goldminen-ETF GDX/USD",
         "ITAxUSD": "Rüstungs-ETF ITA/USD", "XARxUSD": "Rüstungs-ETF XAR/USD", "SHLDxUSD": "Rüstungs-ETF SHLD/USD",
         "XLExUSD": "Energie-ETF XLE/USD"}


def display(pair):
    """XBTEUR -> BTC/EUR, AAPLxUSD -> AAPL/USD"""
    if pair in NAMES:
        return NAMES[pair]
    base, quote = pair[:-3], pair[-3:]
    base = {"XBT": "BTC"}.get(base, base)
    if base.endswith("x") and len(base) > 2:
        base = base[:-1]
    return f"{base}/{quote}"
