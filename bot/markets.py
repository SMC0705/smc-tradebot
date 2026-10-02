"""MÄRKTE: welche Werte gehandelt werden, wie sie in der App heißen und zu welchen
Nachrichten-Themen sie gehören. Paare, die Kraken nicht anbietet, werden automatisch
übersprungen und in der App angezeigt – man kann hier also gefahrlos Kandidaten eintragen.
"""
# Kraken-Paarnamen
CRYPTO = ["XBTEUR", "ETHEUR", "LTCEUR", "SOLEUR", "XRPEUR"]
MEMES = ["DOGEEUR", "SHIBEUR", "PEPEEUR", "BONKEUR", "WIFEUR", "FLOKIEUR"]
FOREX = ["EURUSD", "GBPUSD", "AUDUSD", "USDJPY", "USDCHF", "USDCAD"]
# Kraken xStocks (Aktien als Token): KI-/Tech-Werte, Palantir und Indizes
STOCKS = ["NVDAxUSD", "PLTRxUSD", "MSFTxUSD", "GOOGLxUSD", "METAxUSD", "AMZNxUSD", "AAPLxUSD", "AMDxUSD",
          "AVGOxUSD", "TSMxUSD", "ORCLxUSD", "ARMxUSD", "CRWDxUSD", "INTCxUSD", "TSLAxUSD", "SPYxUSD", "QQQxUSD"]
# Krisen-Werte: Gold (PAXG = tokenisiertes Gold), Energie, Rüstung, Öl-/Gold-ETFs (falls bei Kraken vorhanden)
CRISIS = ["PAXGEUR", "XOMxUSD", "CVXxUSD", "LMTxUSD", "RTXxUSD", "NOCxUSD", "GDxUSD", "USOxUSD", "GLDxUSD"]

# Zu welchen Nachrichten-Themen ein Krisen-Wert passt (siehe settings.THEMES)
ASSET_THEMES = {
    "PAXGEUR": ["krieg", "crash", "zoelle"], "GLDxUSD": ["krieg", "crash", "zoelle"],
    "XOMxUSD": ["oel", "krieg"], "CVXxUSD": ["oel", "krieg"], "USOxUSD": ["oel", "krieg"],
    "LMTxUSD": ["krieg"], "RTXxUSD": ["krieg"], "NOCxUSD": ["krieg"], "GDxUSD": ["krieg"],
}

# Woran man einen Coin in Schlagzeilen erkennt (für Hack-/Klage-Warnungen)
COIN_WORDS = {
    "XBTEUR": ["bitcoin", "btc"], "ETHEUR": ["ethereum", "ether"], "SOLEUR": ["solana"],
    "XRPEUR": ["xrp", "ripple"], "LTCEUR": ["litecoin"], "DOGEEUR": ["dogecoin"], "SHIBEUR": ["shiba"],
    "PEPEEUR": ["pepe"], "BONKEUR": ["bonk"], "WIFEUR": ["dogwifhat"], "FLOKIEUR": ["floki"],
}

# Marktlage-Quellen des Analysten
REGIME_NAMES = {"XBTEUR": "Bitcoin", "SOLEUR": "Solana", "SPYxUSD": "S&P 500"}

NAMES = {"PAXGEUR": "Gold (PAXG)/EUR"}


def display(pair):
    """XBTEUR -> BTC/EUR, AAPLxUSD -> AAPL/USD"""
    if pair in NAMES:
        return NAMES[pair]
    base, quote = pair[:-3], pair[-3:]
    base = {"XBT": "BTC"}.get(base, base)
    if base.endswith("x") and len(base) > 2:
        base = base[:-1]
    return f"{base}/{quote}"
