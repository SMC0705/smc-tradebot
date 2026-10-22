"""Rücksetzer-Strategie nach Larry Connors (RSI 2), Tageskerzen:
Nur wenn der Kurs über dem 200-Tage-Durchschnitt liegt (Aufwärtstrend), wird ein kurzer, starker
Rücksetzer gekauft (RSI über 2 Tage unter 10). Verkauft wird, sobald der Kurs wieder über dem
5-Tage-Durchschnitt schließt. Connors nutzt keinen Stop – wir sichern trotzdem mit 3 × ATR ab
und verkaufen spätestens nach 10 Tagen.
Ergänzt die anderen Bots gut: alle anderen kaufen Stärke, dieser kauft Schwäche im Aufwärtstrend.
"""
from .indicators import atr, rsi, sma


def signal(c, p):
    if len(c) < 210:
        return None
    cl = [x["c"] for x in c]
    r = rsi(cl, 2)[-1]
    if not (cl[-1] > sma(cl, 200)[-1] and r < p.get("rsi", 10)):
        return None
    entry = cl[-1]
    stop = entry - 3 * atr(c)[-1]
    if stop <= 0:
        return None
    return {"stop": stop, "target": entry * 10, "max_hold": p.get("hold", 10),
            "exit": "rsi2", "exit_p": {"ma": 5}, "reason": f"RSI(2) bei {r:.0f} im Aufwärtstrend"}


def exit_signal(c, p):
    cl = [x["c"] for x in c]
    return len(cl) > 5 and cl[-1] > sma(cl, p.get("ma", 5))[-1]
