# Architektur – wo liegt was?

Diese Datei ist die Landkarte des Projekts. Wer etwas ändern will, findet hier die richtige Stelle.
Grundidee: **Jede Schicht hat genau eine Aufgabe** – Daten holen, Signale finden, ausführen, entscheiden, anzeigen.

```
smc-tradebot/
├─ bot/                      der Bot (Python, nur Standardbibliothek – nichts zu installieren)
│  ├─ main.py                EINSTIEG: Ablauf eines Laufs (keine Logik, nur Reihenfolge)
│  ├─ settings.py            ALLE EINSTELLUNGEN: Geld, Risiko, Gebühren (FEES), Limit-Orders, Team-/Nachrichten-Regeln, Pfade
│  ├─ bots.py                ALLE BOTS & TEAMS: Markt, Takt, Strategie, Varianten, Kaufart (Limit/Market), Standard-Anteil
│  ├─ markets.py             ALLE WERTE: Coin-/Aktien-/Forex-Listen, Anzeigenamen, Krisen-Themen, US-Börsenzeiten
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
│  │  ├─ patterns.py         MUSTER-BIBLIOTHEK: 12 Kauf- und 7 Warnmuster (Kerzen + Chartformationen)
│  │  ├─ stockday.py         Aktien-Daytrading (Eröffnungsspanne / Rücksetzer, nur zur US-Börsenzeit)
│  │  └─ trend, smc, scalp, day, swing, meme, rsi2, minervini, momentum (.py)
│  ├─ trading/               3) AUSFÜHREN – Geld, Positionen, Stops
│  │  ├─ account.py          Konto: Gebühren, Kauf-Orders (Limit/Market), Stop/Ziel/Trailing, Prüfprotokoll-Zähler
│  │  ├─ runner.py           einen Bot laufen lassen (Schatten-Varianten + echtes Konto), Prüfprotokoll speichern
│  │  ├─ pumpfun.py          Sonderfall pump.fun (Scan + Filter + Ausführung), Profile "safe" und "all"
│  │  └─ pool.py             Sammelkonto: Aufteilung auf die Bots, Umbuchungen
│  └─ brain/                 4) ENTSCHEIDEN – über den einzelnen Bots
│     ├─ learning.py         Lernen: Varianten, Muster (gelernt/verworfen), Risiko je Wert (Pause max. 24 Std.)
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
├─ tests/                    Tests ohne Internet: python -m tests.simulate 44 · python -m tests.test_orders
└─ .github/workflows/bot.yml Zeitplan: alle 30 Minuten python -m bot.main
```

## Ablauf eines Laufs (bot/main.py)
1. **Zustand laden:** Konten aller Bots, Sammelkonto, Team- und Nachrichten-Zustand, Aufteilung.
2. **Daten holen:** Wechselkurse (EUR/USD …) und Nachrichten.
3. **Gehirn:** Nachrichtenlage bewerten → Marktlage je Team (Analyst) → Team-Pausen (Risiko-Manager).
4. **Bots laufen lassen** (trading/runner.py), je Wert:
   1. neue Kerzen holen
   2. Schatten-Varianten spielen sie durch (ohne Team-Regeln → ehrlicher Vergleich, zum Lernen)
   3. das Muster-Schattenkonto testet alle Muster der Bibliothek auf diesem Markt und Takt
   4. das echte Konto spielt sie mit der aktiven Variante durch und handelt zusätzlich die *gelernten* Muster
      (halbes Risiko). Vor jeder Kauf-Order fragt es das Team: `team.gate()`
   5. wartende Orders werden gegen die laufende Kerze geprüft (Kauf im selben Lauf)
5. **Abschluss:** Prüfprotokoll je Bot, Sammelkonto umverteilen, alles speichern, `docs/data/status.json` schreiben.

Zeitlimit: GitHub bricht einen Lauf nach 15 Min. ab. Dauert ein Lauf länger als `settings.RUN_BUDGET_MIN` (11 Min.),
werden die übrigen Bots übersprungen und holen im nächsten Lauf alles nach – der Zustand wird immer gespeichert.

## Weg eines Trades
`Strategie.signal()` bzw. gelerntes Muster (bei Kerzenschluss) → Gebühren-Filter `account.worth_it()`
(Stop mind. 1,5× so weit weg wie Kauf + Verkauf kosten, je Markt aus `settings.FEES`) → eigene Regeln (Pause, Abkühlung,
max. Positionen) → `team.gate()` gibt einen Risiko-Faktor (0 = nicht kaufen, sonst 0,25…1,5) → **Kauf-Order** in `pending`:
Limit (10 % der Stop-Distanz unter dem Signalkurs, gilt 2 Kerzen, Maker-Gebühr) oder Market (nächster Eröffnungskurs,
Taker-Gebühr + Kursabschlag) → `account.open_position()` (Größe nach Risiko) → jede weitere Kerze `account.manage()`:
Stop (Market), Ziel (Limit-Verkauf), Zeitablauf, Tagesende (Aktien-Daytrading: US-Börsenschluss), Signal-Ausstieg,
Stop nachziehen → `account.close_position()` → Trade wird gespeichert (Gewinn in € und in R = Vielfaches des Risikos).
Vorsichtig gerechnet: In der Kerze eines Limit-Kaufs zählt nur der Stop. Jeder Schritt zählt im Prüfprotokoll mit
(Signale, zu klein, abgelehnt, Order, nicht gefüllt, gekauft) – zu sehen in der App.

Reihenfolge in `team.gate()`: Team-Pause → Nachrichten (Termin-Sperre, Coin-Warnung, Krisen-Thema, Nachrichtenlage,
Gier) → Kollegen-Warnung → Klumpenrisiko → Marktlage → Warnmuster (x0,5) / bestätigendes gelerntes Muster (x1,2)
→ größerer Trend → Konsens. Jede Entscheidung landet im Team-Protokoll.

## Rezepte
- **Neuen Bot anlegen:** Eintrag in `bot/bots.py` (Strategie wählen, 3 Varianten, `weight` = Standard-Anteil).
- **Neues Muster:** Funktion in `bot/strategies/patterns.py` schreiben, in `BULLISH` eintragen, Namen in `LABELS`.
  Jeder Bot testet es danach automatisch und handelt es erst, wenn es sich bewährt.
- **Neue Strategie:** neue Datei in `bot/strategies/` mit `signal(c, p)` (optional `exit_signal`), in `strategies/__init__.py` eintragen.
- **Neue Werte:** Liste in `bot/markets.py` ergänzen. Nicht vorhandene Werte werden automatisch übersprungen.
- **Neue Nachrichtenquelle:** RSS-Adresse in `settings.NEWS_FEEDS` bzw. Redaktion in `settings.NEWS_DOMAINS`. Nur seriöse Quellen!
- **Neues Stichwort/Thema:** `settings.THEMES`. Krisen-Werte dazu in `markets.ASSET_THEMES`.
- **Termine:** `config/termine.json` (Zeit in UTC). **US-Börsenfeiertage:** `markets.US_HOLIDAYS` (jährlich ergänzen).
- **Gebühren:** `settings.FEES` bzw. `settings.KRAKEN_TIER` (Krypto-Gebührenstufe). **Kaufart:** `entry` in `bots.py`.
- **Regeln/Grenzwerte ändern:** nur in `bot/settings.py`.
- **Varianten ändern:** Das Lernen dieses Bots startet automatisch neu. Das echte Konto bleibt.
- **pump.fun-Filter:** `PROFILES` in `bot/trading/pumpfun.py` ("safe" = vorsichtig, "all" = ganzer Markt); ein Bot wählt sein
  Profil mit `scan` in `bots.py`.
- **Handelslogik grundlegend ändern:** `settings.ENGINE_VERSION` erhöhen → alle Bots lernen neu (aus der Vergangenheit).

## Regeln für sauberen Code
1. `main.py` enthält nur den Ablauf. Logik gehört in die Ordner.
2. `data/` holt nur Daten, `strategies/` liefert nur Signale, `trading/` rechnet Geld, `brain/` entscheidet.
3. Einstellungen stehen nur in `settings.py`, `bots.py`, `markets.py` und `config/`, nicht verstreut im Code.
4. Jede Datei beginnt mit einer kurzen Beschreibung, was sie tut.
5. Vor jedem Upload: `python -m tests.simulate 44` und `python -m tests.test_orders` müssen ohne Fehler durchlaufen.
