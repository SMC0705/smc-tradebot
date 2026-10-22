"""Trend-Aktien nach Mark Minervini (Tageskerzen).
"Trend Template" – alle Punkte müssen erfüllt sein:
  1. Kurs über 150- und 200-Tage-Durchschnitt   2. 150er über 200er   3. 200er steigt seit ≥ 1 Monat
  4. 50er über 150er und 200er   5. Kurs über 50er   6. Kurs ≥ 30 % über 52-Wochen-Tief
  7. Kurs höchstens 25 % unter 52-Wochen-Hoch
Kauf beim Ausbruch über das Hoch der letzten "pivot" Tage. Verlust wird bei max. 6–10 % begrenzt
(Minervinis Regel: Verluste klein halten). Verkauf, wenn der Kurs unter den 50-Tage-Durchschnitt fällt.
Hinweis: Kraken-xStocks haben auch am Wochenende Kerzen – "Tage" sind hier Kalendertage.
"""
from .indicators import sma


def signal(c, p):
    if len(c) < 253:
        return None
    cl = [x["c"] for x in c]
    price = cl[-1]
    s50, s150, s200 = sma(cl, 50)[-1], sma(cl, 150)[-1], sma(cl, 200)
    hi52, lo52 = max(x["h"] for x in c[-252:]), min(x["l"] for x in c[-252:])
    template = (price > s150 and price > s200[-1] and s150 > s200[-1] and s200[-1] > s200[-22]
                and s50 > s150 and price > s50 and price >= 1.3 * lo52 and price >= 0.75 * hi52)
    if not template:
        return None
    n = p.get("pivot", 20)
    pivot = max(x["h"] for x in c[-n - 1:-1])
    if not (price > pivot and cl[-2] <= pivot):
        return None
    max_loss = p.get("max_loss", 0.08)
    stop = max(price * (1 - max_loss), min(x["l"] for x in c[-10:]))
    if stop >= price * 0.995:
        stop = price * (1 - max_loss)
    return {"stop": stop, "target": price * 10, "exit": "minervini", "exit_p": {"ma": 50},
            "reason": f"Trend-Template erfüllt, Ausbruch über {n}-Tage-Hoch"}


def exit_signal(c, p):
    cl = [x["c"] for x in c]
    return len(cl) > 50 and cl[-1] < sma(cl, p.get("ma", 50))[-1]
