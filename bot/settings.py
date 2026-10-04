"""ALLE EINSTELLUNGEN AN EINEM ORT.
Geld, Risiko, Team-Regeln, Nachrichten-Regeln und Dateipfade. Wer etwas am Verhalten
ändern will, schaut zuerst hier. (Welche Bots es gibt, steht in bots.py; die Märkte in markets.py.)
"""
import os

# --- Betrieb ---------------------------------------------------------------------
MODE = os.environ.get("BOT_MODE", "paper")   # "paper" = Demo mit Spielgeld. "live" ist noch nicht eingebaut.
POOL_START_EUR = 8000.0                      # Spielgeld im Sammelkonto
MIN_ORDER_EUR = 10.0                         # kleinere Käufe lässt Kraken nicht zu
MAX_DRAWDOWN_STOP = 0.25                     # Not-Aus je Bot: −25 % vom besten Stand -> keine neuen Trades
WARMUP_CANDLES = 500                         # Schatten-Varianten lernen beim Start aus so vielen alten Kerzen
ENGINE_VERSION = "4.4"                       # ändert sich die Handelslogik, startet das Lernen neu
MIN_RISK_FEE_MULT = 1.5                      # Stop muss mind. 1,5x so weit weg sein wie Kauf + Verkauf kosten
CHECKS_KEEP = 48                             # Prüfprotokoll: so viele Läufe merken (48 = 24 Std.)
RUN_BUDGET_MIN = 11                          # GitHub bricht einen Lauf nach 15 Min. ab: nach 11 Min. werden übrige
                                             # Bots übersprungen (holen alles im nächsten Lauf nach), damit gespeichert wird

# --- Gebühren je Richtung (Kauf ODER Verkauf) ------------------------------------------
# Quelle: kraken.com/features/fee-schedule (Stand Okt. 2026).
# Maker = Limit-Order, die im Orderbuch wartet. Taker = sofort zum Marktpreis (auch jeder Stop-Loss).
# Krypto-Stufen nach 30-Tage-Umsatz: 1 = ab 0 $ (0,40 / 0,80 %), 2 = ab 2.500 $ (0,30 / 0,60 %),
# 3 = ab 10.000 $ (0,22 / 0,38 %), 4 = ab 25.000 $ (0,20 / 0,35 %). Aktive Bots erreichen Stufe 2 nach wenigen Tagen.
KRAKEN_TIER = 2
_CRYPTO_TIERS = {1: (0.0040, 0.0080), 2: (0.0030, 0.0060), 3: (0.0022, 0.0038), 4: (0.0020, 0.0035)}
FEES = {
    "crypto": {"maker": _CRYPTO_TIERS[KRAKEN_TIER][0], "taker": _CRYPTO_TIERS[KRAKEN_TIER][1]},
    "xstocks": {"maker": 0.0, "taker": 0.0008},    # Aktien-Token (ab 05.10.2026; vorher 0,10 %)
    "fx": {"maker": 0.0020, "taker": 0.0020},      # Devisen-Paare
    "dex": {"maker": 0.01, "taker": 0.01},         # pump.fun auf Solana: Swap-Gebühr + Priority Fee (geschätzt)
}
LIMIT_RULES = {
    "offset_r": 0.1,     # Limit-Kauf 10 % der Stop-Distanz unter dem Signalkurs
    "valid": 2,          # Order gilt 2 Kerzen, danach wird sie gelöscht ...
    "valid_daily": 1,    # ... bei Tageskerzen 1 Tag
}

# --- Lernen ---------------------------------------------------------------------------
LEARN_RULES = {
    "pair_pause_h": 24,         # schwacher Wert: höchstens 24 Std. Pause, danach neuer Versuch mit halbem Risiko
    "pair_pause_n": 10,         # Pause erst ab 10 Trades seit Live-Start ...
    "pair_pause_r": -0.6,       # ... wenn sie im Schnitt mehr als 0,6 R verloren haben
    "pattern_min_trades": 12,   # ein Muster gilt als "gelernt" ab 12 Test-Trades ...
    "pattern_min_score": 0.08,  # ... mit klar positivem Ergebnis (Summe R / (Anzahl + 5))
    "pattern_risk": 0.5,        # gelernte Muster handelt das echte Konto zusätzlich mit halbem Risiko
    "pattern_confirm": 1.2,     # Signal + gelerntes Kaufmuster gleichzeitig -> 1,2x Risiko
    "pattern_warn": 0.5,        # Warnmuster (z. B. Doppeltop) beim Kauf -> halbes Risiko
}

# --- Marktlage (Analyst): Risiko-Faktor je Marktlage --------------------------------
REGIME_DEFAULT = {"Aufwärts": 1.0, "Seitwärts": 0.75, "Abwärts": 0.5}
REGIME_TREND = {"Aufwärts": 1.0, "Seitwärts": 0.5, "Abwärts": 0.0}   # Trendfolger kaufen nicht gegen den Markt

# --- Team-Regeln (Risiko-Manager, Konsens) -------------------------------------------
TEAM_RULES = {
    "pair_warning_h": 2,        # nach Stop-Loss eines Kollegen: Wert 2 Std. für das Team gesperrt
    "sl_guard_count": 6,        # 6 Stop-Losses im Team ...
    "sl_guard_h": 6,            # ... innerhalb von 6 Std. ...
    "sl_guard_pause_h": 4,      # ... -> 4 Std. Pause für neue Trades
    "dd_limit": 0.08,           # Team verliert in 24 Std. mehr als 8 % ...
    "dd_pause_h": 12,           # ... -> 12 Std. Pause
    "max_pair_exposure": 0.20,  # max. 20 % des Sammelkontos im selben Wert (über alle Bots)
    "max_team_exposure": 0.80,  # max. 80 % des Team-Geldes gleichzeitig investiert
    "consensus_boost": 1.25,    # Kollege hält denselben Wert im Plus -> 1,25x Risiko
    "htf_against": 0.5,         # größerer Trend dagegen -> halbes Risiko
    "max_factor": 1.5,          # mehr als 1,5x Risiko gibt es nie
}

# --- Nachrichten (nur vertrauenswürdige, kostenlose Quellen) ------------------------
NEWS_FEEDS = [  # offizielle RSS-Feeds: öffentlich-rechtliche Sender, Notenbanken, Fach-Redaktion
    ("Tagesschau", "https://www.tagesschau.de/xml/rss2/"),
    ("Tagesschau Wirtschaft", "https://www.tagesschau.de/wirtschaft/index~rss2.xml"),
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("Deutsche Welle", "https://rss.dw.com/rdf/rss-en-all"),
    ("Federal Reserve", "https://www.federalreserve.gov/feeds/press_all.xml"),
    ("EZB", "https://www.ecb.europa.eu/rss/press.html"),
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
]
# GDELT durchsucht weltweit Nachrichten – wir lassen nur diese Redaktionen zu:
NEWS_DOMAINS = ["reuters.com", "apnews.com", "bbc.co.uk", "bbc.com", "dw.com", "tagesschau.de",
                "ft.com", "bloomberg.com", "cnbc.com", "wsj.com", "theguardian.com", "aljazeera.com"]
GDELT_QUERIES = {   # Volumen-Spitzen zu diesen Themen = Unruhe in der Welt
    "krieg": "(war OR invasion OR airstrike OR missile OR bombing)",
    "oel": "(oil OR crude OR opec) (attack OR sanctions OR supply OR hormuz)",
}
# Themen-Erkennung in Schlagzeilen. "en" = ganzes Wort, "de" = Wortanfang (erkennt auch Ölpreis, Kriegsgefahr)
THEMES = {
    "krieg": {"label": "Krieg & Konflikte",
              "en": ["war", "invasion", "airstrike", "airstrikes", "missile", "missiles", "military strike", "bombing",
                     "troops", "drone attack", "shelling", "escalation"],
              "de": ["krieg", "angriff", "luftangriff", "raketenangriff", "drohnenangriff", "rakete", "invasion",
                     "truppen", "militär", "eskalation", "beschuss"]},
    "oel": {"label": "Öl & Energie",
            "en": ["oil", "crude", "opec", "brent", "hormuz", "refinery", "pipeline", "gas supply"],
            "de": ["öl", "opec", "raffinerie", "pipeline", "gaspreis", "energiepreis"]},
    "zinsen": {"label": "Zinsen & Notenbanken",
               "en": ["rate decision", "rate hike", "rate cut", "interest rate", "interest rates", "inflation", "fomc",
                      "powell", "lagarde", "cpi"],
               "de": ["leitzins", "zinsentscheid", "zinserhöhung", "zinssenkung", "inflation", "notenbank", "ezb"]},
    "zoelle": {"label": "Zölle & Sanktionen",
               "en": ["tariff", "tariffs", "trade war", "sanctions", "embargo", "export ban"],
               "de": ["zoll", "zölle", "handelskrieg", "sanktion", "embargo"]},
    "crash": {"label": "Börsen-Stress",
              "en": ["crash", "plunge", "plunges", "selloff", "sell-off", "recession", "bank run", "bankruptcy"],
              "de": ["crash", "kurssturz", "rezession", "insolvenz", "pleite", "börsenbeben", "ausverkauf"]},
    "krypto_risiko": {"label": "Krypto-Warnungen",
                      "en": ["hack", "hacked", "exploit", "stolen", "lawsuit", "sues", "ban", "depeg", "delisting",
                             "outage"],
                      "de": ["hack", "gestohlen", "klage", "verbot", "betrug"]},
    "frieden": {"label": "Entspannung",
                "en": ["ceasefire", "peace talks", "truce", "peace deal"],
                "de": ["waffenruhe", "waffenstillstand", "friedensgespräch", "friedensabkommen"]},
}
NEWS_RULES = {
    "window_h": 6,                 # gezählt werden Schlagzeilen der letzten 6 Std.
    "event_before_min": 60,        # keine neuen Kurzfrist-Trades 60 Min. vor ...
    "event_after_min": 60,         # ... bis 60 Min. nach wichtigen Terminen (Fed, EZB, US-Daten)
    "level1": {"spike": 1.6, "krieg": 3, "crash": 2, "zoelle": 3},   # "erhöht", wenn eins davon erreicht
    "level2": {"spike": 2.5, "krieg": 6, "crash": 4},                # "hoch"
    "level_factor": {0: 1.0, 1: 0.75, 2: 0.5},                       # Risiko-Faktor für alle (außer Krisen-Bot)
    "greed_limit": 80, "greed_factor": 0.75,   # Krypto "extreme Gier" -> vorsichtiger
    "coin_pause_h": 6,                         # Hack/Klage zu einem Coin -> 6 Std. Pause für diesen Coin
    "theme_count": 3, "theme_spike": 1.6,      # ab hier gilt ein Thema als aktiv (Krisen-Bot)
}

# --- Dateien ------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(ROOT, "state", "v2")            # vom Bot geschrieben – nie von Hand ändern
ALLOC_FILE = os.path.join(ROOT, "config", "allocation.json")   # Aufteilung & Teams (App schreibt hier)
TERMINE_FILE = os.path.join(ROOT, "config", "termine.json")    # Wirtschaftstermine (jährlich ergänzen)
STATUS_FILE = os.path.join(ROOT, "docs", "data", "status.json")  # das liest die App
