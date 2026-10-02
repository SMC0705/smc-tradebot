# Architektur – wo liegt was?

Diese Datei ist die Landkarte des Projekts. Wer etwas ändern will, findet hier die richtige Stelle.
Grundidee: **Jede Schicht hat genau eine Aufgabe** – Daten holen, Signale finden, ausführen, entscheiden, anzeigen.

```
smc-tradebot/
├─ bot/                      der Bot (Python, nur Standardbibliothek – nichts zu installieren)
│  ├─ main.py                EINSTIEG: Ablauf eines Laufs (keine Logik, nur Reihenfolge)
│  ├─ settings.py            ALLE EINSTELLUNGEN: Geld, Risiko, Team- und Nachrichten-Regeln, Pfade
│  ├─ bots.py                ALLE BOTS & TEAMS: Markt, Takt, Strategie, Varianten, Team
│  ├─ markets.py             ALLE WERTE: Coin-/Aktien-/Forex-Listen, Anzeigenamen, Krisen-Themen
│  ├─ storage.py             Speichern/Laden (state/, config/, status.json)
│  ├─ report.py              baut docs/data/status.json für die App
│  ├─ data/                  1) DATEN HOLEN – entscheidet nichts
│  │  ├─ http.py             gemeinsamer Abruf mit Wartezeiten je Anbieter
│  │  ├─ kraken.py           Kerzen von Kraken + Wechselkurse nach EUR
│  │  ├─ dex.py              pump.fun-Daten (GeckoTerminal, DexScreener)
│  │  └─ news.py             RSS-Feeds, GDELT, Fear & Greed, Wirtschaftstermine
│  ├─ strategies/            2) SIGNALE – "Kaufen? Wo ist der Stop? Wo das Ziel?"
│  │  ├─ __init__.py         Verzeichnis aller Strategien (SIGNALS, EXITS)
│  │  ├─ indicators.py       EMA, SMA, RSI, ATR, ADX
│  │  └─ trend, smc, scalp, day, swing, meme, rsi2, minervini, momentum (.py)
│  ├─ trading/               3) AUSFÜHREN – Geld, Positionen, Stops
│  │  ├─ account.py          Konto: kaufen, verkaufen, Stop/Ziel/Trailing, Kerzen nachspielen
│  │  ├─ runner.py           einen Bot laufen lassen (Schatten-Varianten + echtes Konto)
│  │  ├─ pumpfun.py          Sonderfall pump.fun (Scan + Filter + Ausführung)
│  │  └─ pool.py             Sammelkonto: Aufteilung auf die Bots, Umbuchungen
│  └─ brain/                 4) ENTSCHEIDEN – über den einzelnen Bots
│     ├─ learning.py         Varianten-Lernen + Risiko je Wert
│     ├─ analyst.py          Marktlage (Aufwärts/Seitwärts/Abwärts) + größerer Trend
│     ├─ news_analyst.py     Nachrichtenlage, Termin-Sperren, Coin-Warnungen, Krisen-Themen
│     ├─ risk.py             Risiko-Manager: Team-Pausen, Kollegen-Warnung, Klumpenrisiko
│     ├─ portfolio.py        Vorschlag für die Geld-Aufteilung
│     └─ team.py             bündelt alles zu EINER Kauf-Entscheidung: gate()
├─ config/                   von DIR (oder der App) änderbar
│  ├─ allocation.json        Geld-Aufteilung und Team-Zuordnung
│  └─ termine.json           Wirtschaftstermine (Fed, EZB, US-Daten) – jährlich ergänzen
├─ state/v2/                 vom Bot geschrieben – NIE von Hand ändern (Löschen = Neustart der Demo)
│  ├─ <bot>.json             je Bot: echtes Konto, Schatten-Varianten, Lern-Protokoll
│  ├─ pool.json · team.json · news.json
├─ docs/                     die Handy-App (GitHub Pages): index.html, data/status.json
├─ tests/                    Test ohne Internet: python -m tests.simulate 40
└─ .github/workflows/bot.yml Zeitplan: alle 30 Minuten python -m bot.main
```

## Ablauf eines Laufs (bot/main.py)
1. **Zustand laden:** Konten aller Bots, Sammelkonto, Team- und Nachrichten-Zustand, Aufteilung.
2. **Daten holen:** Wechselkurse (EUR/USD …) und Nachrichten.
3. **Gehirn:** Nachrichtenlage bewerten → Marktlage je Team (Analyst) → Team-Pausen (Risiko-Manager).
4. **Bots laufen lassen** (trading/runner.py), je Wert:
   1. neue Kerzen holen
   2. Schatten-Varianten spielen sie durch (ohne Team-Regeln → ehrlicher Vergleich, zum Lernen)
   3. das echte Konto spielt sie mit der aktiven Variante durch. Vor jedem Kauf fragt es das Team: `team.gate()`
5. **Abschluss:** Sammelkonto umverteilen, alles speichern, `docs/data/status.json` für die App schreiben.

## Weg eines Trades
`Strategie.signal()` (bei Kerzenschluss) → wartet als „pending“ → nächste Kerze: `team.gate()` gibt einen Risiko-Faktor
(0 = nicht kaufen, sonst 0,25…1,5) → `account.open_position()` (Größe nach Risiko, Gebühren, Slippage) →
jede weitere Kerze `account.manage()`: Stop, Ziel, Zeitablauf, Tagesende, Signal-Ausstieg, Stop nachziehen →
`account.close_position()` → Trade wird im Konto gespeichert (Gewinn in € und in R = Vielfaches des Risikos).

Reihenfolge in `team.gate()`: Team-Pause → Nachrichten (Termin-Sperre, Coin-Warnung, Krisen-Thema, Nachrichtenlage,
Gier) → Kollegen-Warnung → Klumpenrisiko → Marktlage → größerer Trend → Konsens. Jede Entscheidung landet im Team-Protokoll.

## Rezepte
- **Neuen Bot anlegen:** Eintrag in `bot/bots.py` (Strategie wählen, 3 Varianten) + Gewicht in `config/allocation.json`.
- **Neue Strategie:** neue Datei in `bot/strategies/` mit `signal(c, p)` (optional `exit_signal`), in `strategies/__init__.py` eintragen.
- **Neue Werte:** Liste in `bot/markets.py` ergänzen. Nicht vorhandene Werte werden automatisch übersprungen.
- **Neue Nachrichtenquelle:** RSS-Adresse in `settings.NEWS_FEEDS` bzw. Redaktion in `settings.NEWS_DOMAINS`. Nur seriöse Quellen!
- **Neues Stichwort/Thema:** `settings.THEMES`. Krisen-Werte dazu in `markets.ASSET_THEMES`.
- **Termine:** `config/termine.json` (Zeit in UTC).
- **Regeln/Grenzwerte ändern:** nur in `bot/settings.py`.
- **Varianten ändern:** Das Lernen dieses Bots startet automatisch neu. Das echte Konto bleibt.

## Regeln für sauberen Code
1. `main.py` enthält nur den Ablauf. Logik gehört in die Ordner.
2. `data/` holt nur Daten, `strategies/` liefert nur Signale, `trading/` rechnet Geld, `brain/` entscheidet.
3. Einstellungen stehen nur in `settings.py`, `bots.py`, `markets.py` und `config/`, nicht verstreut im Code.
4. Jede Datei beginnt mit einer kurzen Beschreibung, was sie tut.
5. Vor jedem Upload: `python -m tests.simulate 40` muss ohne Fehler durchlaufen.
