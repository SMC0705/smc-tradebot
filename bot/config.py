"""Zentrale Einstellungen des Bots. Hier kannst du alles anpassen."""
import os

# "paper" = Demo mit Spielgeld und echten Live-Kursen. "live" ist bewusst noch nicht eingebaut.
MODE = os.environ.get("BOT_MODE", "paper")

# Handelspaare auf Kraken (Anzeigename -> Kraken-Paar-Code)
PAIRS = {
    "BTC/EUR": "XBTEUR",
    "ETH/EUR": "ETHEUR",
    "LTC/EUR": "LTCEUR",
    "SOL/EUR": "SOLEUR",
}

CANDLE_MINUTES = 60          # 1-Stunden-Kerzen
START_BALANCE_EUR = 1000.0   # Spielgeld pro Strategie in der Demo

RISK_PER_TRADE = 0.02        # 2 % des Guthabens Verlust pro Trade, wenn der Stop-Loss greift
MAX_OPEN_POSITIONS = 3       # max. gleichzeitige Positionen pro Strategie
MAX_POSITION_FRACTION = 0.33 # eine Position darf max. 33 % des Guthabens binden (kein Hebel)
FEE_RATE = 0.004             # Kraken Taker-Gebühr (0,40 %), bewusst pessimistisch
SLIPPAGE = 0.001             # 0,1 % schlechterer Kurs als angezeigt (realistischer)
BREAKEVEN_AT_R = 1.0         # Stop auf Einstand ziehen, sobald 1x Risiko im Plus
MAX_DRAWDOWN_STOP = 0.25     # Not-Aus: bei -25 % vom Höchststand keine neuen Trades mehr

STRATEGIES = ["smc", "trend"]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(ROOT, "state")
STATUS_FILE = os.path.join(ROOT, "docs", "data", "status.json")
