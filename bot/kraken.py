"""Öffentliche Kraken-Marktdaten (kein API-Schlüssel nötig)."""
import json
import time
import urllib.request

API = "https://api.kraken.com/0/public"


def _get(path, retries=3):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(API + path, headers={"User-Agent": "smc-tradebot/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read().decode())
            if data.get("error"):
                raise RuntimeError(", ".join(data["error"]))
            return data["result"]
        except Exception as e:  # Netzwerkfehler -> kurz warten, erneut versuchen
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"Kraken nicht erreichbar: {last}")


def get_candles(pair_code, interval_min):
    """Liefert NUR abgeschlossene Kerzen als Liste von Dicts (älteste zuerst)."""
    res = _get(f"/OHLC?pair={pair_code}&interval={interval_min}")
    key = next(k for k in res if k != "last")
    rows = res[key]
    candles = [
        {"t": int(r[0]), "o": float(r[1]), "h": float(r[2]), "l": float(r[3]), "c": float(r[4]), "v": float(r[6])}
        for r in rows
    ]
    # Die letzte Kerze ist noch offen -> nicht für Signale verwenden
    return candles[:-1], candles[-1]
