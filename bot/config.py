"""Zentrale Einstellungen: Märkte, Bots, Risiko. Hier kannst du alles anpassen."""
import os

# "paper" = Demo mit Spielgeld und echten Live-Kursen. "live" ist bewusst noch nicht eingebaut.
MODE = os.environ.get("BOT_MODE", "paper")

POOL_START_EUR = 8000.0       # Spielgeld im Sammelkonto (Demo)
MAX_DRAWDOWN_STOP = 0.25      # Not-Aus je Bot: −25 % vom Höchststand -> keine neuen Trades
MIN_ORDER_EUR = 10.0

# --- Märkte (Kraken-Paarnamen) ----------------------------------------------
CRYPTO = ["XBTEUR", "ETHEUR", "LTCEUR", "SOLEUR", "XRPEUR"]
MEMES = ["DOGEEUR", "SHIBEUR", "PEPEEUR", "BONKEUR", "WIFEUR", "FLOKIEUR"]
FOREX = ["EURUSD", "GBPUSD", "AUDUSD", "USDJPY", "USDCHF", "USDCAD"]
# Kraken xStocks: KI-/Tech-Werte, Palantir und Indizes
STOCKS = ["NVDAxUSD", "PLTRxUSD", "MSFTxUSD", "GOOGLxUSD", "METAxUSD", "AMZNxUSD", "AAPLxUSD", "AMDxUSD",
          "AVGOxUSD", "TSMxUSD", "ORCLxUSD", "ARMxUSD", "CRWDxUSD", "INTCxUSD", "TSLAxUSD", "SPYxUSD", "QQQxUSD"]

# --- Bots --------------------------------------------------------------------
# tf = Kerzenlänge in Minuten. variants = Parameter-Sets, zwischen denen der Bot
# anhand seiner Ergebnisse selbst wählt (Lern-Modul).
_BASE = dict(risk=0.02, max_pos=3, frac=0.33, fee=0.004, slip=0.001, aclass=None)

BOTS = {
    "scalp": dict(_BASE, name="Scalping", style="Minuten", tf=5, market="Krypto", pairs=CRYPTO,
                  strategy="scalp", variants=[
                      {"rr": 1.5, "min_stop": 0.004, "hold": 24},
                      {"rr": 2.0, "min_stop": 0.006, "hold": 36},
                      {"rr": 2.5, "min_stop": 0.008, "hold": 48}]),
    "day": dict(_BASE, name="Daytrading", style="15 Minuten", tf=15, market="Krypto", pairs=CRYPTO,
                strategy="day", variants=[
                    {"range": 16, "vol": 1.5, "rr": 2.0},
                    {"range": 32, "vol": 1.5, "rr": 2.0},
                    {"range": 16, "vol": 2.0, "rr": 3.0}]),
    "smc": dict(_BASE, name="SMC", style="Stunden", tf=60, market="Krypto", pairs=CRYPTO,
                strategy="smc", variants=[{"rr": 2.5}, {"rr": 2.0}, {"rr": 3.0}]),
    "trend": dict(_BASE, name="Trendfolge", style="Stunden", tf=60, market="Krypto", pairs=CRYPTO,
                  strategy="trend", variants=[
                      {"fast": 20, "slow": 50, "rr": 2.0},
                      {"fast": 10, "slow": 30, "rr": 2.0},
                      {"fast": 20, "slow": 50, "rr": 3.0}]),
    "swing": dict(_BASE, name="Swing", style="Tage", tf=1440, market="Krypto", pairs=CRYPTO,
                  strategy="swing", variants=[
                      {"n": 20, "trail": 10}, {"n": 55, "trail": 20}, {"n": 10, "trail": 5}]),
    "meme": dict(_BASE, name="Memecoins", style="15 Minuten", tf=15, market="Memecoins", pairs=MEMES,
                 strategy="meme", risk=0.01, max_pos=2, frac=0.25, slip=0.003, variants=[
                     {"n": 24, "vol": 2.0, "rr": 3.0},
                     {"n": 48, "vol": 2.5, "rr": 3.0},
                     {"n": 24, "vol": 3.0, "rr": 4.0}]),
    "pump": dict(_BASE, name="pump.fun", style="5 Minuten", tf=5, market="Solana", pairs=[], source="pumpfun",
                 strategy="meme", risk=0.01, max_pos=4, frac=0.10, fee=0.01, slip=0.01, variants=[
                     {"stop": 0.15, "target": 0.40, "trail": 12},
                     {"stop": 0.25, "target": 0.80, "trail": 24},
                     {"stop": 0.10, "target": 0.25, "trail": 6}]),
    "fx": dict(_BASE, name="Forex", style="4 Stunden", tf=240, market="Währungen", pairs=FOREX,
               strategy="trend", fee=0.002, slip=0.0002, variants=[
                   {"fast": 20, "slow": 50, "rr": 2.0},
                   {"fast": 10, "slow": 30, "rr": 2.0},
                   {"fast": 20, "slow": 50, "rr": 3.0}]),
    "stocks": dict(_BASE, name="Aktien", style="Stunden", tf=60, market="Aktien", pairs=STOCKS,
                   strategy="trend", aclass="tokenized_asset", max_pos=5, frac=0.2, variants=[
                       {"fast": 20, "slow": 50, "rr": 2.0},
                       {"fast": 10, "slow": 30, "rr": 2.0},
                       {"fast": 20, "slow": 50, "rr": 3.0}]),
}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(ROOT, "state", "v2")
ALLOC_FILE = os.path.join(ROOT, "config", "allocation.json")
STATUS_FILE = os.path.join(ROOT, "docs", "data", "status.json")


def display(pair):
    """XBTEUR -> BTC/EUR, AAPLxUSD -> AAPL/USD"""
    base, quote = pair[:-3], pair[-3:]
    base = {"XBT": "BTC"}.get(base, base)
    if base.endswith("x") and len(base) > 2:
        base = base[:-1]
    return f"{base}/{quote}"
