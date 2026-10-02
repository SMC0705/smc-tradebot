"""VERZEICHNIS ALLER STRATEGIEN.
Jede Strategie-Datei hat eine Funktion signal(kerzen, parameter) -> Kaufsignal oder None.
Ein Signal ist ein dict: {"stop", "target", "reason"} und optional
  "trail_n" (Stop am Tief der letzten n Kerzen nachziehen), "max_hold" (max. Kerzen halten),
  "eod" (zum Tagesende schließen), "exit" + "exit_p" (eigene Verkaufsregel aus EXITS).
Strategien entscheiden NUR über Signale – Geld, Risiko und Team-Regeln liegen woanders.
Gekauft wird immer erst zum Eröffnungskurs der nächsten Kerze (kein Blick in die Zukunft).
"""
from . import day, meme, minervini, momentum, patterns, rsi2, scalp, smc, swing, trend

WINDOW = 260  # so viele Kerzen bekommt jede Strategie

SIGNALS = {
    "smc": smc.signal,
    "trend": trend.signal,
    "scalp": scalp.signal,
    "day": day.signal,
    "swing": swing.signal,
    "meme": meme.signal,
    "rsi2": rsi2.signal,
    "minervini": minervini.signal,
    "momentum": momentum.signal,
    "patterns": patterns.signal,   # Muster-Bibliothek (siehe patterns.py)
}

EXITS = {
    "rsi2": rsi2.exit_signal,
    "minervini": minervini.exit_signal,
}
