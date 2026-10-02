# SMC Tradebot – Demo-Phase

Vollautomatische Trading-Bots für **Kraken** (Krypto, Aktien als xStocks, Devisen, Gold) und **pump.fun** (Solana).
Sie handeln mit **Spielgeld** (8.000 € im Sammelkonto) und echten Live-Kursen. Gestartet werden sie alle 30 Minuten
kostenlos über **GitHub Actions**. Die Handy-App läuft über **GitHub Pages**.
Wie der Code aufgebaut ist und wo was liegt, steht in **[ARCHITEKTUR.md](ARCHITEKTUR.md)**.

## Die Bots (12) in 4 Teams

| Team | Bot | Takt | Idee (Vorbild) |
|---|---|---|---|
| Krypto | Scalping | 5 Min. | Rücksetzer an EMA21; Variante „Holy Grail“ nur bei starkem Trend (Linda Raschke) |
| Krypto | Daytrading | 15 Min. | Ausbruch mit Volumen bzw. Volatilitäts-Ausbruch (Larry Williams), Schluss am Tagesende |
| Krypto | SMC | 1 Std. | Strukturbruch + Fair Value Gap → Retest des Order Blocks |
| Krypto | Trendfolge | 1 Std. | EMA-Kreuzung im Aufwärtstrend |
| Krypto | Swing (Turtle) | 1 Tag | 20/55-Tage-Ausbruch, 2N-Stop, Ausstieg am n-Tage-Tief (Richard Dennis) |
| Memecoin | Memecoins | 15 Min. | DOGE, SHIB, PEPE, BONK, WIF, FLOKI: Momentum mit Volumen-Explosion, 1 % Risiko |
| Memecoin | pump.fun | 5 Min. | Scannt aktive pump.fun-Coins (GeckoTerminal, DexScreener), strenge Sicherheitsfilter, 1 % Risiko |
| Aktien & Devisen | Aktien | 1 Std. | 17 KI- & Tech-Werte (Nvidia, Palantir, Microsoft …) + S&P 500, Nasdaq: Trendfolge |
| Aktien & Devisen | Trend-Aktien | 1 Tag | Trend Template + Ausbruch, Verlust max. 6–10 % (Mark Minervini) |
| Aktien & Devisen | Rücksetzer | 1 Tag | RSI(2) unter 10 im Aufwärtstrend kaufen, Verkauf über 5-Tage-Linie (Larry Connors) |
| Aktien & Devisen | Forex | 4 Std. | EUR/USD, GBP/USD, USD/JPY …: Trendfolge |
| Makro & Krisen | Krisen-Bot | 1 Std. | Gold (PAXG), Öl-/Energie- und Rüstungswerte – nur bei passenden Nachrichten **und** steigendem Kurs |

Für alle gilt: nur Kauf (Long), **kein Hebel**, immer mit Stop-Loss, Gebühren und Slippage eingerechnet,
Not-Aus bei −25 %, nach einem Verkauf 3 Kerzen Pause. Werte, die Kraken nicht anbietet, werden übersprungen und in der App angezeigt.

**Lernen:** Jeder Bot testet 3 Varianten parallel mit Schatten-Konten (zum Start mit bis zu 500 vergangenen Kerzen).
Das echte Konto folgt der Variante, die nachweislich am besten läuft. Schwache Werte bekommen weniger Risiko.

**Teams:** Jedes Team hat einen **Analysten** (Marktlage und größerer Trend), einen **Risiko-Manager** (Pausen nach Verlustserien,
Kollegen-Warnungen, Limits gegen Klumpenrisiko) und Konsens (Kollege im Plus → etwas mehr Risiko).
Der **Portfolio-Manager** schlägt ab 20 Trades eine neue Geld-Aufteilung vor.

**Nachrichten (nur vertrauenswürdige, kostenlose Quellen):** Tagesschau, BBC, Deutsche Welle, Federal Reserve, EZB, CoinDesk,
dazu GDELT (weltweite Nachrichtenauswertung, nur Reuters, AP, BBC, FT, Bloomberg u. a.), der Crypto Fear & Greed Index und die offiziellen
Termine von Fed, EZB und US-Statistikamt (config/termine.json).
- Unruhige Weltlage → alle Bots kaufen mit weniger Risiko. Krieg, Öl oder Börsen-Stress schalten den Krisen-Bot frei.
- Rund um Zinsentscheide und US-Daten machen Kurzfrist-Bots keine neuen Trades.
- Hack- oder Klage-Meldungen zu einem Coin → dieser Coin pausiert 6 Std.
- Social Media (X/Twitter) ist bewusst **nicht** dabei: Lesezugriff kostet Geld, und die Quellen sind nicht verlässlich.

## Einrichtung (einmalig)
1. Auf github.com ein **öffentliches** Repository `smc-tradebot` anlegen (nur dann sind Pages und Actions-Minuten kostenlos).
2. **Add file → Upload files**: die Ordner `bot`, `docs`, `config`, `tests`, `.github` und die Dateien `README.md`, `ARCHITEKTUR.md` hochladen.
   Fehlt danach `.github/workflows/bot.yml`, diese Datei über **Add file → Create new file** anlegen.
3. **Settings → Actions → General** → „Read and write permissions“ → Save.
4. **Settings → Pages** → Branch `main`, Ordner `/docs` → Save.
5. **Actions → Trading-Bot → Run workflow**. Danach läuft alles alle 30 Minuten von allein.
6. Am Handy `https://DEIN-NAME.github.io/smc-tradebot/` öffnen → „Zum Startbildschirm hinzufügen“.

## Update auf eine neue Version
1. Im Repository den Ordner `bot` öffnen → oben rechts **…** → **Delete directory** → Commit (alte Dateien weg).
2. Neue Ordner hochladen (`bot`, `docs`, `config`, `tests` und `ARCHITEKTUR.md`, `README.md`) → Commit.
Die Demo läuft mit ihrem Stand weiter (`state/` nicht löschen). Neu ist nur, was sich geändert hat.

## Bedienung
- **App:** Bots (nach Teams) · News (Nachrichtenlage, Termine, Meldungen) · Konto (Aufteilung, Teams, Vorschlag des Portfolio-Managers).
- **Aufteilung ändern:** in der App (mit GitHub-Schlüssel, Anleitung in der App) oder am PC in `config/allocation.json`.
- **Bot pausieren:** Actions → Trading-Bot → „…“ → Disable workflow. **Demo neu starten:** Ordner `state` löschen.
- **Testen ohne Internet:** `python -m tests.simulate 40` (künstliche Kurse; prüft, dass alles fehlerfrei läuft).

## Nach 1–2 Monaten
„Demo auswerten“ zu Claude sagen. Erst wenn die Ergebnisse überzeugen, kommt der Echtgeld-Teil dazu
(eigener kleiner Server, Kraken-API-Schlüssel ohne Auszahlungsrechte, Litecoin-Einzahlung ins Sammelkonto).

Kein Bot kann Gewinne garantieren. Nachrichten- und Strategie-Regeln senken Risiken, verhindern Verluste aber nicht.
Setz später nur Geld ein, dessen Verlust du verkraften kannst.
