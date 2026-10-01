# SMC Tradebot – Demo-Phase

Vollautomatischer Krypto-Trading-Bot für **Kraken**. Er handelt aktuell mit **Spielgeld** (je 1.000 € pro Strategie) und echten Live-Kursen.
Er läuft kostenlos auf **GitHub Actions** (alle 30 Minuten). Die Handy-App läuft über **GitHub Pages**.

## Was der Bot macht
- Paare: BTC, ETH, LTC, SOL (jeweils gegen EUR), 1-Stunden-Kerzen
- Zwei Strategien laufen parallel mit getrenntem Spielgeld:
  - **SMC**: Strukturbruch nach oben + Fair Value Gap → Kauf beim ersten Retest des Order Blocks. Ziel ist das 2,5-fache Risiko.
  - **Trendfolge**: EMA20 kreuzt EMA50 nach oben, Kurs über EMA200, RSI zwischen 45 und 70
- Risiko: 2 % pro Trade, immer mit Stop-Loss, nur Kauf (Long), **kein Hebel**. Maximal 3 Positionen gleichzeitig.
- Stop wird auf Einstand gezogen, sobald der Trade 1x Risiko im Plus ist
- Not-Aus: bei −25 % vom Höchststand macht der Bot keine neuen Trades mehr
- Gebühren (0,4 %) und Slippage sind eingerechnet

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

## Nach 1–2 Monaten
Komm zu Claude zurück und sag „Demo auswerten“. Dann werten wir beide Strategien aus. Nur wenn die Ergebnisse überzeugen, kommt der Echtgeld-Teil dazu:
- Kraken-Konto mit API-Schlüssel (nur Handeln, **keine** Auszahlungsrechte)
- Du zahlst Litecoin ein, der Bot wandelt es in EUR-Handelsguthaben um
- Das Repository wird privat und die Schlüssel kommen in GitHub Secrets

Kein Bot kann Gewinne garantieren. Setz später nur Geld ein, dessen Verlust du verkraften kannst.
