"""Portfolio-Manager: Vorschlag für die Geld-Aufteilung nach den bisherigen Ergebnissen.
Mehr Geld für Bots mit besserem Ergebnis pro Risiko (Ø R), je Bot 5–30 %. Bots auf 0 % bleiben aus.
Es ist nur ein Vorschlag – übernommen wird er erst, wenn du ihn in der App bestätigst."""

NEEDED_TRADES = 20


def _units(raw, total=20, lo=1, hi=6):
    keys, s = list(raw), sum(raw.values()) or 1.0
    u = {k: lo for k in keys}
    for _ in range(max(total - lo * len(keys), 0)):
        cand = [k for k in keys if u[k] < hi] or keys
        k = max(cand, key=lambda k: raw[k] / s * total - u[k])
        u[k] += 1
    return u


def suggestion(states, weights):
    scores, n_total = {}, 0
    for b, st in states.items():
        tr = st["real"]["trades"]
        n_total += len(tr)
        if len(tr) >= 5:
            scores[b] = sum(t["r"] for t in tr) / (len(tr) + 10)
        else:  # zu wenig echte Trades -> vorsichtig die Schatten-Ergebnisse nutzen
            sh = st["shadows"][st["active"]]["trades"]
            scores[b] = 0.5 * sum(t["r"] for t in sh) / (len(sh) + 10)
    enabled = [b for b in weights if weights[b] > 0]
    units = _units({b: max(0.25, 1 + 2 * scores[b]) for b in enabled}) if enabled else {}
    return {"ready": n_total >= NEEDED_TRADES, "trades": n_total, "needed": NEEDED_TRADES,
            "weights": {b: units.get(b, 0) * 5 for b in weights},
            "scores": {b: round(v, 3) for b, v in scores.items()}}
