# SMC Tradebot – Demo-Phase

Vollautomatische Trading-Bots für **Kraken** (Krypto, Aktien als xStocks, Devisen, Gold) und **pump.fun** (Solana).
Sie handeln mit **Spielgeld** (8.000 € im Sammelkonto) und echten Live-Kursen. Gestartet werden sie alle 30 Minuten
kostenlos über **GitHub Actions**. Die Handy-App läuft über **GitHub Pages**.
Wie der Code aufgebaut ist und wo was liegt, steht in **[ARCHITEKTUR.md](ARCHITEKTUR.md)**.

## Die Bots (16) in 4 Teams

| Team | Bot | Takt | Idee (Vorbild) |
|---|---|---|---|
| Krypto (25 Coins: BTC, ETH, LTC, SOL, XRP, ADA, DOT, LINK, AVAX, ATOM, BCH, XLM, TRX, UNI, AAVE, NEAR, SUI, ALGO, ARB, OP, POL, APT, INJ, FIL, RENDER) | Scalping | 5 Min. | Rücksetzer an EMA21; Variante „Holy Grail“ nur bei starkem Trend (Linda Raschke) |
| Krypto | Daytrading | 15 Min. | Ausbruch mit Volumen bzw. Volatilitäts-Ausbruch (Larry Williams), Schluss am Tagesende |
| Krypto | SMC | 1 Std. | Strukturbruch + Fair Value Gap → Retest des Order Blocks |
| Krypto | Trendfolge | 1 Std. | EMA-Kreuzung im Aufwärtstrend, festes Ziel |
| Krypto | Trendfolge 2 | 1 Std. | Zum Vergleich: Rücksetzer im Aufwärtstrend kaufen und Gewinne mit nachgezogenem Stop laufen lassen (Varianten: Rücksetzer + Ziel, Kreuzung + nachgezogener Stop) |
| Krypto | Ausbruch 4 Std. | 4 Std. | 20/55-Kerzen-Ausbruch mit nachgezogenem Stop – große Bewegungen, Gebühren fallen kaum ins Gewicht |
| Krypto | Swing (Turtle) | 1 Tag | 20/55-Tage-Ausbruch, 2N-Stop, Ausstieg am n-Tage-Tief (Richard Dennis) |
| Memecoin | Memecoins | 15 Min. | DOGE, SHIB, PEPE, BONK, WIF, FLOKI: Momentum mit Volumen-Explosion, 1 % Risiko |
| Memecoin | pump.fun | 5 Min. | Scannt aktive pump.fun-Coins (GeckoTerminal, DexScreener), strenge Sicherheitsfilter, 1 % Risiko |
| Memecoin | pump.fun Alles | 5 Min. | Zum Vergleich: der ganze pump.fun-Markt, auch ganz neue Coins auf der Bonding-Curve, nur Mindestfilter, 1 % Risiko |
| Aktien & Devisen | Aktien | 1 Std. | 17 KI- & Tech-Werte (Nvidia, Palantir, Microsoft …) + S&P 500, Nasdaq: Trendfolge |
| Aktien & Devisen | Aktien-Daytrading | 15 Min. | Ausbruch aus der Eröffnungsspanne (Toby Crabel) bzw. Rücksetzer im Tagestrend. Nur solange die US-Börse offen ist (meist 15:30–22:00 Uhr), alles wird zum Börsenschluss verkauft |
| Aktien & Devisen | Trend-Aktien | 1 Tag | Trend Template + Ausbruch, Verlust max. 6–10 % (Mark Minervini) |
| Aktien & Devisen | Rücksetzer | 1 Tag | RSI(2) unter 10 im Aufwärtstrend kaufen, Verkauf über 5-Tage-Linie (Larry Connors) |
| Aktien & Devisen | Forex | 4 Std. | EUR/USD, GBP/USD, USD/JPY …: Trendfolge |
| Makro & Krisen | Krisen-Bot | 1 Std. | Gold (PAXG), Öl-/Energie- und Rüstungswerte – nur bei passenden Nachrichten **und** steigendem Kurs |

Für alle gilt: nur Kauf (Long), **kein Hebel**, immer mit Stop-Loss, Gebühren und Kursabschlag eingerechnet,
Not-Aus bei −25 %, nach einem Verkauf 3 Kerzen Pause. Werte, die Kraken nicht anbietet, werden übersprungen und in der App angezeigt.

**Gebühren wie bei Kraken** (Stand Okt. 2026, je Kauf bzw. Verkauf):

| Markt | Limit-Order (wartet im Orderbuch) | sofort zum Marktpreis | Stop muss mind. so weit weg sein |
|---|---|---|---|
| Krypto (Stufe 2, ab 2.500 $ Monatsumsatz) | 0,30 % | 0,60 % | 1,5 % (Limit) bzw. 2,1 % (Market) |
| Aktien-Token (xStocks) | 0 % | 0,08 % | 0,27 % bzw. 0,54 % |
| Devisen | 0,20 % | 0,20 % | 0,66 % |
| pump.fun (Solana) | – | ca. 1 % | (eigene Regeln) |

Ganz neue Konten zahlen bei Krypto zuerst 0,40 / 0,80 % (Stufe 1). Einstellbar in `bot/settings.py` (`KRAKEN_TIER`).
**Gekauft wird meist per Limit-Order** etwas unter dem Signalkurs (halbe Gebühr, kein Kursabschlag). Kommt der Kurs
nicht zurück, verfällt die Order nach 2 Kerzen. Schnelle Ausbrüche (Memecoins, Krisen-Bot, Trend-Aktien, Forex) kaufen
sofort. Ziele werden als Limit-Verkauf ausgeführt, Stop-Loss immer sofort (Market).

**Lernen:** Jeder Bot testet 3 Varianten parallel mit Schatten-Konten (zum Start mit bis zu 500 vergangenen Kerzen).
Das echte Konto folgt der Variante, die nachweislich am besten läuft. Schwache Werte bekommen weniger Risiko oder
höchstens 24 Std. Pause (nur aufgrund von Live-Ergebnissen), danach gibt es einen neuen Versuch mit halbem Risiko.

**Muster:** Alle Bots kennen 12 klassische Kaufmuster (Doppelboden, Umgekehrte Schulter-Kopf-Schulter, Bullen-Flagge,
Aufsteigendes Dreieck, Ausbruch + Retest, RSI-Divergenz, Bollinger-Squeeze, Inside Bar, Morgenstern, Drei weiße Soldaten,
Engulfing, Hammer) und 7 Warnmuster (Doppeltop, Schulter-Kopf-Schulter, bärisches Engulfing, Sternschnuppe, Abendstern,
Drei schwarze Krähen, bärische RSI-Divergenz). Jeder Bot testet alle Muster auf seinem Markt und Takt.
Was sich nach Gebühren bewährt, handelt er zusätzlich (halbes Risiko), was verliert, wird verworfen.
Warnmuster halbieren das Risiko eines Kaufs, ein passendes gelerntes Kaufmuster erhöht es leicht.

**Gebühren-Filter:** Ein Trade wird nur gemacht, wenn der Stop mindestens 1,5× so weit weg ist wie Kauf + Verkauf
kosten (Tabelle oben). Krypto-Minuten-Trades fallen deshalb fast immer weg – sie würden fast nur Gebühren erzeugen.
Die vielen kleinen Trades macht dafür der Aktien-Daytrading-Bot, weil Aktien-Token kaum etwas kosten.

**Prüfprotokoll:** Die App zeigt, was die Bots in den letzten 24 Std. gesehen haben: wie viele Kaufsignale es gab,
wie viele davon zu klein für die Gebühren waren, was das Team abgelehnt hat, welche Limit-Orders warten oder nicht
gefüllt wurden und was gekauft wurde (Hauptseite und bei jedem Bot). Käufe erscheinen im selben Lauf, nicht eine Kerze später.

**Vergleiche:** Von den zwei bisher besten Ideen gibt es je einen zweiten Bot. „Trendfolge 2“ zeigt, ob Rücksetzer-Käufe und
nachgezogene Stops besser laufen als Kreuzung + festes Ziel. „pump.fun Alles“ zeigt, ob die Sicherheitsfilter Geld sparen
oder Chancen kosten. Achtung: Nicht einmal 2 % der pump.fun-Coins schaffen es von der Bonding-Curve weg – „Alles“ ist der
riskanteste Bot.

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
5. **Zeitgeber:** GitHubs eigener Zeitplan ist unzuverlässig. Deshalb ruft [cron-job.org](https://cron-job.org) alle 30 Minuten
   den Workflow auf: POST an `https://api.github.com/repos/DEIN-NAME/smc-tradebot/actions/workflows/bot.yml/dispatches`,
   Header `Authorization: Bearer <Token>` und `Accept: application/vnd.github+json`, Inhalt `{"ref":"main"}`.
   Token: GitHub → Settings → Developer settings → Fine-grained token, nur dieses Repository, nur **Actions: Read and write**.
   Zum Testen: **Actions → Trading-Bot → Run workflow**.
6. Am Handy `https://DEIN-NAME.github.io/smc-tradebot/` öffnen → „Zum Startbildschirm hinzufügen“.

## Update auf eine neue Version
1. **Add file → Upload files**: die Ordner `bot`, `docs`, `config`, `tests` und `ARCHITEKTUR.md`, `README.md` hochladen
   (vorhandene Dateien werden überschrieben) → Commit. Nur nötig, wenn eine Version Dateien entfernt: vorher den Ordner `bot` löschen.
2. Nichts starten – der nächste Lauf nimmt die neue Version automatisch.
Die Demo läuft mit ihrem Stand weiter (`state/` nicht löschen). Achtung: `config/allocation.json` enthält die Aufteilung –
wer sie in der App geändert hat und sie behalten will, lädt `config` nicht mit hoch.

## Bedienung
- **App:** Bots (nach Teams) · News (Nachrichtenlage, Termine, Meldungen) · Konto (Aufteilung, Teams, Vorschlag des Portfolio-Managers).
- **Aufteilung ändern:** in der App (mit GitHub-Schlüssel, Anleitung in der App) oder am PC in `config/allocation.json`.
- **Bot pausieren:** Actions → Trading-Bot → „…“ → Disable workflow. **Demo neu starten:** Ordner `state` löschen.
- **Testen ohne Internet:** `python -m tests.simulate 44` (künstliche Kurse; prüft, dass alles fehlerfrei läuft) und
  `python -m tests.test_orders` (rechnet Orders und Gebühren an Beispielen nach).

## Nach 1–2 Monaten
„Demo auswerten“ zu Claude sagen. Erst wenn die Ergebnisse überzeugen, kommt der Echtgeld-Teil dazu
(eigener kleiner Server, Kraken-API-Schlüssel ohne Auszahlungsrechte, Litecoin-Einzahlung ins Sammelkonto).

Kein Bot kann Gewinne garantieren. Nachrichten- und Strategie-Regeln senken Risiken, verhindern Verluste aber nicht.
Setz später nur Geld ein, dessen Verlust du verkraften kannst.
