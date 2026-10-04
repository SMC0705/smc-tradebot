"""MÄRKTE: welche Werte gehandelt werden, wie sie in der App heißen, zu welchen Nachrichten-Themen
sie gehören und wann die US-Börse offen hat. Paare, die Kraken nicht anbietet, werden automatisch
übersprungen und in der App angezeigt – man kann hier also gefahrlos Kandidaten eintragen.
"""
from datetime import date, datetime, timedelta, timezone

# Kraken-Paarnamen. Krypto: 25 Coins, alle mit mind. ca. 200.000 € Tagesumsatz im EUR-Paar (geprüft Okt. 2026)
CRYPTO = ["XBTEUR", "ETHEUR", "LTCEUR", "SOLEUR", "XRPEUR", "ADAEUR", "DOTEUR", "LINKEUR", "AVAXEUR", "ATOMEUR",
          "BCHEUR", "XLMEUR", "TRXEUR", "UNIEUR", "AAVEEUR", "NEAREUR", "SUIEUR", "ALGOEUR", "ARBEUR", "OPEUR",
          "POLEUR", "APTEUR", "INJEUR", "FILEUR", "RENDEREUR"]
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
    "ATOMEUR": ["cosmos"], "BCHEUR": ["bitcoin cash"], "XLMEUR": ["stellar", "xlm"], "TRXEUR": ["tron"],
    "UNIEUR": ["uniswap"], "AAVEEUR": ["aave"], "NEAREUR": ["near protocol"], "SUIEUR": ["sui"],
    "ALGOEUR": ["algorand"], "ARBEUR": ["arbitrum"], "OPEUR": ["op mainnet", "optimism network"],
    "POLEUR": ["polygon"], "APTEUR": ["aptos"], "INJEUR": ["injective"], "FILEUR": ["filecoin"],
    "RENDEREUR": ["render network"],
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


# --- US-Börse (für das Aktien-Daytrading) --------------------------------------------------
# Aktien-Token handeln bei Kraken rund um die Uhr an Werktagen (24/5). Echte Bewegung und Umsatz gibt es aber
# nur, wenn die US-Börse offen ist: 9:30–16:00 New Yorker Zeit (bei uns meist 15:30–22:00).
# Feiertage und verkürzte Tage (Schluss 13:00) laut NYSE Group – jährlich ergänzen.
US_HOLIDAYS = {"2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19", "2026-07-03",
               "2026-09-07", "2026-11-26", "2026-12-25", "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26",
               "2027-05-31", "2027-06-18", "2027-07-05", "2027-09-06", "2027-11-25", "2027-12-24"}
US_EARLY_CLOSE = {"2026-11-27", "2026-12-24", "2027-11-26"}

try:
    from zoneinfo import ZoneInfo
    _NY = ZoneInfo("America/New_York")
except Exception:          # ohne Zeitzonen-Daten: US-Sommerzeit selbst berechnen
    _NY = None


def _ny_offset_h(d):
    """Abstand New York zu UTC in Stunden (Sommerzeit: 2. Sonntag im März bis 1. Sonntag im November)."""
    start = date(d.year, 3, 8) + timedelta(days=(6 - date(d.year, 3, 8).weekday()) % 7)
    end = date(d.year, 11, 1) + timedelta(days=(6 - date(d.year, 11, 1).weekday()) % 7)
    return -4 if start <= d < end else -5


def _ny_date(ts):
    if _NY:
        return datetime.fromtimestamp(ts, _NY).date()
    d = datetime.fromtimestamp(ts - 5 * 3600, timezone.utc).date()
    return datetime.fromtimestamp(ts + _ny_offset_h(d) * 3600, timezone.utc).date()


def _ny_ts(d, hour, minute):
    if _NY:
        return int(datetime(d.year, d.month, d.day, hour, minute, tzinfo=_NY).timestamp())
    return int(datetime(d.year, d.month, d.day, hour, minute, tzinfo=timezone.utc).timestamp()) - _ny_offset_h(d) * 3600


def us_session(ts):
    """(Eröffnung, Schluss) der US-Börse als Unix-Zeit für den New Yorker Tag von ts – oder None am Wochenende/Feiertag."""
    d = _ny_date(ts)
    if d.weekday() >= 5 or d.isoformat() in US_HOLIDAYS:
        return None
    return _ny_ts(d, 9, 30), _ny_ts(d, 13 if d.isoformat() in US_EARLY_CLOSE else 16, 0)
