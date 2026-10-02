"""ALLE BOTS UND TEAMS.
Ein Bot = Markt + Kerzen-Takt + Strategie + 3 Varianten (zwischen denen er selbst lernt) + Team.
Neuen Bot anlegen: Eintrag hier ergänzen, Strategie in bot/strategies/ wählen, Gewicht in
config/allocation.json eintragen. Mehr ist nicht nötig.

Felder: tf = Kerzenlänge in Minuten · risk = Anteil des Bot-Geldes, der pro Trade verloren gehen darf ·
max_pos = gleichzeitige Positionen · frac = max. Anteil des Bot-Geldes pro Position · fee/slip = Kosten je Richtung ·
cooldown = Kerzen Pause nach einem Verkauf · regime_src = Markt, nach dem der Analyst die Lage beurteilt
"""
from .markets import CRISIS, CRYPTO, FOREX, MEMES, STOCKS
from .settings import REGIME_DEFAULT, REGIME_TREND

TEAMS = {
    "krypto": "Krypto-Team",
    "meme": "Memecoin-Team",
    "markt": "Aktien & Devisen",
    "makro": "Makro & Krisen",
}

_BASE = dict(risk=0.02, max_pos=3, frac=0.33, fee=0.004, slip=0.001, aclass=None, cooldown=3,
             team="krypto", regime_src="XBTEUR", regime_rules=REGIME_DEFAULT)
_STOCK = dict(aclass="tokenized_asset", team="markt", regime_src="SPYxUSD")

BOTS = {
    # --- Krypto-Team -------------------------------------------------------------
    "scalp": dict(_BASE, name="Scalping", style="Minuten", tf=5, market="Krypto", pairs=CRYPTO,
                  strategy="scalp", variants=[
                      {"rr": 1.5, "min_stop": 0.004, "hold": 24},
                      {"rr": 2.0, "min_stop": 0.006, "hold": 36, "adx_min": 30},   # "Holy Grail" (L. Raschke)
                      {"rr": 2.5, "min_stop": 0.008, "hold": 48}]),
    "day": dict(_BASE, name="Daytrading", style="15 Minuten", tf=15, market="Krypto", pairs=CRYPTO,
                strategy="day", variants=[
                    {"range": 16, "vol": 1.5, "rr": 2.0},
                    {"mode": "williams", "k": 0.5, "rr": 2.0},                    # Larry Williams
                    {"mode": "williams", "k": 0.7, "rr": 2.0}]),
    "smc": dict(_BASE, name="SMC", style="Stunden", tf=60, market="Krypto", pairs=CRYPTO,
                strategy="smc", variants=[{"rr": 2.5}, {"rr": 2.0}, {"rr": 3.0}]),
    "trend": dict(_BASE, name="Trendfolge", style="Stunden", tf=60, market="Krypto", pairs=CRYPTO,
                  strategy="trend", regime_rules=REGIME_TREND, variants=[
                      {"fast": 20, "slow": 50, "rr": 2.0},
                      {"fast": 10, "slow": 30, "rr": 2.0},
                      {"fast": 20, "slow": 50, "rr": 3.0}]),
    "swing": dict(_BASE, name="Swing (Turtle)", style="Tage", tf=1440, market="Krypto", pairs=CRYPTO,
                  strategy="swing", regime_rules=REGIME_TREND, variants=[
                      {"n": 20, "trail": 10}, {"n": 55, "trail": 20}, {"n": 10, "trail": 5}]),
    # --- Memecoin-Team -----------------------------------------------------------
    "meme": dict(_BASE, name="Memecoins", style="15 Minuten", tf=15, market="Memecoins", pairs=MEMES,
                 strategy="meme", team="meme", regime_src="SOLEUR", risk=0.01, max_pos=2, frac=0.25, slip=0.003,
                 variants=[{"n": 24, "vol": 2.0, "rr": 3.0}, {"n": 48, "vol": 2.5, "rr": 3.0},
                           {"n": 24, "vol": 3.0, "rr": 4.0}]),
    "pump": dict(_BASE, name="pump.fun", style="5 Minuten", tf=5, market="Solana", pairs=[], source="pumpfun",
                 strategy="meme", team="meme", regime_src="SOLEUR", risk=0.01, max_pos=4, frac=0.10,
                 fee=0.01, slip=0.01, variants=[
                     {"stop": 0.15, "target": 0.40, "trail": 12},
                     {"stop": 0.25, "target": 0.80, "trail": 24},
                     {"stop": 0.10, "target": 0.25, "trail": 6}]),
    # --- Aktien & Devisen --------------------------------------------------------
    "stocks": dict(_BASE, **_STOCK, name="Aktien", style="Stunden", tf=60, market="Aktien", pairs=STOCKS,
                   strategy="trend", max_pos=5, frac=0.2, variants=[
                       {"fast": 20, "slow": 50, "rr": 2.0},
                       {"fast": 10, "slow": 30, "rr": 2.0},
                       {"fast": 20, "slow": 50, "rr": 3.0}]),
    "minervini": dict(_BASE, **_STOCK, name="Trend-Aktien (Minervini)", style="Tage", tf=1440, market="Aktien",
                      pairs=STOCKS, strategy="minervini", regime_rules=REGIME_TREND, max_pos=4, frac=0.25,
                      variants=[{"pivot": 20, "max_loss": 0.08}, {"pivot": 10, "max_loss": 0.06},
                                {"pivot": 50, "max_loss": 0.10}]),
    "rsi2": dict(_BASE, **_STOCK, name="Rücksetzer (Connors)", style="Tage", tf=1440, market="Aktien",
                 pairs=STOCKS, strategy="rsi2", max_pos=4, frac=0.25,
                 variants=[{"rsi": 10}, {"rsi": 5}, {"rsi": 15}]),
    "fx": dict(_BASE, name="Forex", style="4 Stunden", tf=240, market="Währungen", pairs=FOREX,
               strategy="trend", team="markt", regime_src=None, fee=0.002, slip=0.0002, variants=[
                   {"fast": 20, "slow": 50, "rr": 2.0},
                   {"fast": 10, "slow": 30, "rr": 2.0},
                   {"fast": 20, "slow": 50, "rr": 3.0}]),
    # --- Makro & Krisen ----------------------------------------------------------
    # Kauft nur, wenn der Nachrichten-Analyst ein passendes Thema meldet (Krieg, Öl, Börsen-Stress)
    # UND der Kurs es bestätigt. Gold, Energie- und Rüstungswerte.
    "krise": dict(_BASE, name="Krisen-Bot", style="Stunden", tf=60, market="Gold, Energie, Rüstung", pairs=CRISIS,
                  strategy="momentum", aclass="tokenized_asset", team="makro", regime_src=None, needs_theme=True,
                  risk=0.015, max_pos=3, frac=0.25, variants=[
                      {"n": 24, "trail": 12, "hold": 168},
                      {"n": 48, "trail": 24, "hold": 336},
                      {"n": 12, "trail": 8, "hold": 96}]),
}
