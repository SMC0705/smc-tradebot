# SMC Tradebot – Demo-Phase

Vollautomatischer Krypto-Trading-Bot für **Kraken**. Er handelt aktuell mit **Spielgeld** (8.000 € im Sammelkonto) und echten Live-Kursen.
Er läuft kostenlos auf **GitHub Actions** (alle 30 Minuten). Die Handy-App läuft über **GitHub Pages**.

## Was der Bot macht (Version 2)
8 Bots handeln mit Spielgeld aus einem gemeinsamen **Sammelkonto** (8.000 €). Alle laufen über **Kraken**:

| Bot | Markt | Takt | Idee |
|---|---|---|---|
| Scalping | Krypto | 5 Minuten | Rücksetzer an EMA21 im Kurz-Trend, Ausstieg spätestens nach 2–4 Std. |
| Daytrading | Krypto | 15 Minuten | Ausbruch aus der Spanne mit Volumen, Schluss spätestens am Tagesende |
| SMC | Krypto | 1 Stunde | Strukturbruch + Fair Value Gap → Retest des Order Blocks |
| Trendfolge | Krypto | 1 Stunde | EMA-Kreuzung im Aufwärtstrend |
| Swing | Krypto | 1 Tag | 20-Tage-Ausbruch, Stop wird nachgezogen |
| Memecoins | DOGE, SHIB, PEPE, BONK, WIF, FLOKI | 15 Minuten | Momentum-Ausbruch mit Volumen-Explosion, nur 1 % Risiko |
| Forex | EUR/USD, GBP/USD, USD/JPY … | 4 Stunden | Trendfolge |
| Aktien | Apple, Nvidia, Tesla, Microsoft, S&P 500, Nasdaq (Kraken xStocks) | 1 Stunde | Trendfolge |

Für alle gilt: nur Kauf (Long), **kein Hebel**, immer mit Stop-Loss, Gebühren und Slippage eingerechnet, Not-Aus bei −25 %.
Paare, die Kraken nicht anbietet, werden automatisch übersprungen und in der App angezeigt.

**Lernen:** Jeder Bot testet 3 Varianten seiner Einstellungen parallel mit Schatten-Konten. Beim ersten Start lernen diese aus bis zu 500 vergangenen Kerzen.
Das echte Konto folgt automatisch der Variante, die nachweislich am besten läuft (mindestens 10 Trades, im Schnitt im Plus).
Paare, die oft verlieren, bekommen weniger Risiko oder werden pausiert. Gut laufende Paare bekommen leicht mehr Risiko. Jede Anpassung steht in der App unter „Lernen“.

**Sammelkonto:** Im Tab „Konto“ teilst du das Geld per Schieberegler auf die Bots auf (0 % = Bot aus).
Zum Speichern braucht die App einmalig einen GitHub-Schlüssel. Die Anleitung steht direkt in der App.

## Einrichtung (einmalig, ca. 10 Minuten)
1. Auf github.com ein **neues Repository** anlegen, z. B. `smc-tradebot`, auf **Public** stellen. Nur dann sind Pages und Actions-Minuten kostenlos.
   Hinweis: Die Demo-Ergebnisse sind dann öffentlich einsehbar. Vor dem Echtgeld-Start ändern wir das.
2. **Add file → Upload files**: den Inhalt dieses Ordners hochladen (die Ordner `bot`, `docs`, `.github` und die `README.md`). Dann „Commit changes“.
   - Falls der Ordner `.github` nicht mit hochgeladen wird (er ist versteckt): **Add file → Create new file**. Als Namen `.github/workflows/bot.yml` eintippen und den Inhalt der Datei hineinkopieren.
3. **Settings → Actions → General**: ganz unten bei „Workflow permissions“ **Read and write permissions** wählen und speichern.
4. **Settings → Pages**: Source „Deploy from a branch“, Branch `main`, Ordner `/docs`, speichern.
5. Tab **Actions** → „Trading-Bot“ → **Run workflow**. Nach etwa 1 Minute sollte der Lauf grün sein. Danach läuft der Bot von alleine alle 30 Minuten.
6. Am Handy `https://DEIN-NAME.github.io/smc-tradebot/` öffnen und **„Zum Home-Bildschirm“** wählen. Danach hast du die App wie eine normale App.

## Wichtig
- Für die Demo brauchst du **keinen** Kraken-Account und **keinen** API-Schlüssel.
- Der Bot läuft komplett ohne Claude. Während der Demo entstehen also keine Kosten.
- GitHub kann geplante Läufe verzögern (oft um 5–15 Minuten). Bei 1-Stunden-Kerzen ist das unkritisch.
- Bot pausieren: Actions → Trading-Bot → „…“ → **Disable workflow**.
- Demo neu starten: den Ordner `state` löschen.
- Für den späteren Echtgeld-Betrieb ist ein kleiner eigener Server (ca. 4–5 €/Monat) zuverlässiger als GitHub Actions. Den richten wir vor dem Start zusammen ein.

## Nach 1–2 Monaten
Komm zu Claude zurück und sag „Demo auswerten“. Dann werten wir beide Strategien aus. Nur wenn die Ergebnisse überzeugen, kommt der Echtgeld-Teil dazu:
- Kraken-Konto mit API-Schlüssel (nur Handeln, **keine** Auszahlungsrechte)
- Du zahlst Litecoin ein, der Bot wandelt es in EUR-Handelsguthaben um
- Das Repository wird privat und die Schlüssel kommen in GitHub Secrets

Kein Bot kann Gewinne garantieren. Setz später nur Geld ein, dessen Verlust du verkraften kannst.
