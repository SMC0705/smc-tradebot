"""ALLE BOTS UND TEAMS.
Ein Bot = Markt + Kerzen-Takt + Strategie + 3 Varianten (zwischen denen er selbst lernt) + Team.
Neuen Bot anlegen: Eintrag hier ergänzen, Strategie in bot/strategies/ wählen. Mehr ist nicht nötig.

Felder: tf = Kerzenlänge in Minuten · risk = Anteil des Bot-Geldes, der pro Trade verloren gehen darf ·
max_pos = gleichzeitige Positionen · frac = max. Anteil des Bot-Geldes pro Position · slip = Kursabschlag bei
Market-Orders · entry = "limit" (Kauf per Limit-Order, halbe Gebühr) oder "market" (sofort, für schnelle Ausbrüche;
eine Variante kann das mit "entry" überschreiben) · cooldown = Kerzen Pause nach einem Verkauf ·
regime_src = Markt, nach dem der Analyst die Lage beurteilt · session = "us": nur zur US-Börsenzeit ·
scan = pump.fun-Profil ("safe" = strenge Filter, "all" = ganzer Markt inkl. Bonding-Curve, siehe trading/pumpfun.py) ·
weight = Standard-Anteil am Sammelkonto in %, solange config/allocation.json nichts anderes sagt.
Die Gebühren stehen in settings.FEES (je Markt: Krypto, Aktien-Token, Devisen, pump.fun).
"""
from .markets import CRISIS, CRYPTO, FOREX, MEMES, STOCKS
from .settings import REGIME_DEFAULT, REGIME_TREND

TEAMS = {
    "krypto": "Krypto-Team",
    "meme": "Memecoin-Team",
    "markt": "Aktien & Devisen",
    "makro": "Makro & Krisen",
}

_BASE = dict(risk=0.02, max_pos=3, frac=0.33, slip=0.001, aclass=None, cooldown=3, entry="limit", weight=5,
             team="krypto", regime_src="XBTEUR", regime_rules=REGIME_DEFAULT)
_STOCK = dict(aclass="tokenized_asset", team="markt", regime_src="SPYxUSD")

BOTS = {
    # --- Krypto-Team -------------------------------------------------------------
    # Hinweis: Bei Krypto kostet Kauf + Verkauf mind. 0,9 % – auf 5/15-Min.-Kerzen lohnt sich ein Trade nur bei
    # großen Bewegungen. Diese Bots handeln deshalb selten (der Gebühren-Filter sortiert Mini-Trades aus).
    "scalp": dict(_BASE, name="Scalping", style="Minuten", tf=5, market="Krypto", pairs=CRYPTO, weight=2,
                  strategy="scalp", variants=[
                      {"rr": 1.5, "min_stop": 0.004, "hold": 24},
                      {"rr": 2.0, "min_stop": 0.006, "hold": 36, "adx_min": 30},   # "Holy Grail" (L. Raschke)
                      {"rr": 2.5, "min_stop": 0.008, "hold": 48}]),
    "day": dict(_BASE, name="Daytrading", style="15 Minuten", tf=15, market="Krypto", pairs=CRYPTO, weight=3,
                strategy="day", variants=[
                    {"range": 16, "vol": 1.5, "rr": 2.0},
                    {"mode": "williams", "k": 0.5, "rr": 2.0},                    # Larry Williams
                    {"mode": "williams", "k": 0.7, "rr": 2.0}]),
    "smc": dict(_BASE, name="SMC", style="Stunden", tf=60, market="Krypto", pairs=CRYPTO, weight=7,
                strategy="smc", variants=[{"rr": 2.5}, {"rr": 2.0}, {"rr": 3.0}]),
    "trend": dict(_BASE, name="Trendfolge", style="Stunden", tf=60, market="Krypto", pairs=CRYPTO, weight=9,
                  strategy="trend", regime_rules=REGIME_TREND, variants=[
                      {"fast": 20, "slow": 50, "rr": 2.0},
                      {"fast": 10, "slow": 30, "rr": 2.0},
                      {"fast": 20, "slow": 50, "rr": 3.0}]),
    # Zweiter Trendfolger zum Vergleich: kauft Rücksetzer im Trend und lässt Gewinne mit nachgezogenem Stop laufen
    "trend2": dict(_BASE, name="Trendfolge 2", style="Stunden", tf=60, market="Krypto", pairs=CRYPTO, weight=9,
                   strategy="trend", regime_rules=REGIME_TREND, variants=[
                       {"mode": "pullback", "trail": 10},               # Rücksetzer + nachgezogener Stop
                       {"mode": "pullback", "rr": 2.0},                 # Rücksetzer + festes Ziel
                       {"fast": 20, "slow": 50, "trail": 10}]),         # Kreuzung wie Trendfolge 1 + nachgezogener Stop
    # Größere Bewegungen: hier fallen die Gebühren kaum ins Gewicht
    "breakout": dict(_BASE, name="Ausbruch 4 Std.", style="4 Stunden", tf=240, market="Krypto", pairs=CRYPTO,
                     weight=8, strategy="swing", regime_rules=REGIME_TREND, variants=[
                         {"n": 20, "trail": 10}, {"n": 20, "trail": 10, "entry": "market"}, {"n": 55, "trail": 20}]),
    "swing": dict(_BASE, name="Swing (Turtle)", style="Tage", tf=1440, market="Krypto", pairs=CRYPTO, weight=9,
                  strategy="swing", regime_rules=REGIME_TREND, variants=[
                      {"n": 20, "trail": 10}, {"n": 55, "trail": 20}, {"n": 20, "trail": 10, "entry": "market"}]),
    # --- Memecoin-Team -----------------------------------------------------------
    "meme": dict(_BASE, name="Memecoins", style="15 Minuten", tf=15, market="Memecoins", pairs=MEMES,
                 strategy="meme", team="meme", regime_src="SOLEUR", risk=0.01, max_pos=2, frac=0.25, slip=0.003,
                 entry="market", weight=4,
                 variants=[{"n": 24, "vol": 2.0, "rr": 3.0}, {"n": 24, "vol": 2.0, "rr": 3.0, "entry": "limit"},
                           {"n": 48, "vol": 2.5, "rr": 3.0}]),
    "pump": dict(_BASE, name="pump.fun", style="5 Minuten", tf=5, market="Solana", pairs=[], source="pumpfun",
                 strategy="meme", team="meme", regime_src="SOLEUR", risk=0.01, max_pos=4, frac=0.10,
                 slip=0.01, entry="market", weight=5, scan="safe", variants=[
                     {"stop": 0.15, "target": 0.40, "trail": 12},
                     {"stop": 0.25, "target": 0.80, "trail": 24},
                     {"stop": 0.10, "target": 0.25, "trail": 6}]),
    # Zweiter pump.fun-Bot zum Vergleich: handelt den ganzen pump.fun-Markt (auch die Bonding-Curve), nur Mindestfilter
    "pump2": dict(_BASE, name="pump.fun Alles", style="5 Minuten", tf=5, market="Solana", pairs=[], source="pumpfun",
                  strategy="meme", team="meme", regime_src="SOLEUR", risk=0.01, max_pos=5, frac=0.08,
                  slip=0.02, entry="market", weight=5, scan="all", variants=[
                      {"stop": 0.15, "target": 0.40, "trail": 12},
                      {"stop": 0.25, "target": 1.00, "trail": 24},
                      {"stop": 0.10, "target": 0.30, "trail": 6}]),
    # --- Aktien & Devisen --------------------------------------------------------
    "stocks": dict(_BASE, **_STOCK, name="Aktien", style="Stunden", tf=60, market="Aktien", pairs=STOCKS,
                   strategy="trend", max_pos=5, frac=0.2, weight=10, variants=[
                       {"fast": 20, "slow": 50, "rr": 2.0},
                       {"fast": 10, "slow": 30, "rr": 2.0},
                       {"fast": 20, "slow": 50, "rr": 3.0}]),
    # Aktien-Token kosten nur 0,08 % (Limit 0 %) – hier lohnen sich auch kleine Tagesbewegungen
    "stockday": dict(_BASE, **_STOCK, name="Aktien-Daytrading", style="15 Minuten", tf=15, market="Aktien",
                     pairs=STOCKS, strategy="stockday", session="us", risk=0.01, max_pos=3, frac=0.25, weight=10,
                     variants=[{"mode": "orb", "or": 2, "stop": "mid", "rr": 2.0},     # Opening Range Breakout
                               {"mode": "pullback", "rr": 2.0},                        # Rücksetzer im Tagestrend
                               {"mode": "orb", "or": 4, "stop": "low", "rr": 1.5}]),
    "minervini": dict(_BASE, **_STOCK, name="Trend-Aktien (Minervini)", style="Tage", tf=1440, market="Aktien",
                      pairs=STOCKS, strategy="minervini", regime_rules=REGIME_TREND, max_pos=4, frac=0.25,
                      entry="market", weight=6,
                      variants=[{"pivot": 20, "max_loss": 0.08}, {"pivot": 10, "max_loss": 0.06},
                                {"pivot": 50, "max_loss": 0.10}]),
    "rsi2": dict(_BASE, **_STOCK, name="Rücksetzer (Connors)", style="Tage", tf=1440, market="Aktien",
                 pairs=STOCKS, strategy="rsi2", max_pos=4, frac=0.25, weight=6,
                 variants=[{"rsi": 10}, {"rsi": 5}, {"rsi": 15}]),
    "fx": dict(_BASE, name="Forex", style="4 Stunden", tf=240, market="Währungen", pairs=FOREX,
               strategy="trend", team="markt", regime_src=None, slip=0.0002, entry="market", weight=3, variants=[
                   {"fast": 20, "slow": 50, "rr": 2.0},
                   {"fast": 10, "slow": 30, "rr": 2.0},
                   {"fast": 20, "slow": 50, "rr": 3.0}]),
    # --- Makro & Krisen ----------------------------------------------------------
    # Kauft nur, wenn der Nachrichten-Analyst ein passendes Thema meldet (Krieg, Öl, Börsen-Stress)
    # UND der Kurs es bestätigt. Gold, Energie- und Rüstungswerte.
    "krise": dict(_BASE, name="Krisen-Bot", style="Stunden", tf=60, market="Gold, Energie, Rüstung", pairs=CRISIS,
                  strategy="momentum", aclass="tokenized_asset", team="makro", regime_src=None, needs_theme=True,
                  risk=0.015, max_pos=3, frac=0.25, entry="market", weight=4, variants=[
                      {"n": 24, "trail": 12, "hold": 168},
                      {"n": 48, "trail": 24, "hold": 336},
                      {"n": 12, "trail": 8, "hold": 96}]),
}
