"""Öffentliche Kraken-Marktdaten (kein API-Schlüssel nötig)."""
import json
import time
import urllib.parse
import urllib.request

API = "https://api.kraken.com/0/public"
_cache = {}
_last_call = [0.0]


def _get(path, params, retries=3):
    url = f"{API}/{path}?{urllib.parse.urlencode(params)}"
    last = None
    for i in range(retries):
        wait = 1.1 - (time.time() - _last_call[0])  # Kraken-Limit: ca. 1 Anfrage pro Sekunde
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "smc-tradebot/2.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read().decode())
            if data.get("error"):
                msg = ", ".join(data["error"])
                if "Unknown asset pair" in msg or "Invalid arguments" in msg:
                    raise ValueError(msg)  # dauerhaft -> nicht wiederholen
                raise RuntimeError(msg)
            return data["result"]
        except ValueError:
            raise
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"Kraken nicht erreichbar: {last}")


def get_candles(pair, interval, aclass=None):
    """Gibt (abgeschlossene Kerzen, aktuelle offene Kerze) zurück. Ergebnisse werden pro Lauf zwischengespeichert."""
    key = (pair, interval)
    if key in _cache:
        if isinstance(_cache[key], Exception):
            raise _cache[key]
        return _cache[key]
    params = {"pair": pair, "interval": interval}
    try:
        if aclass:
            try:
                res = _get("OHLC", dict(params, asset_class=aclass))
            except ValueError:
                res = _get("OHLC", params)
        else:
            res = _get("OHLC", params)
        k = next(x for x in res if x != "last")
        cs = [{"t": int(r[0]), "o": float(r[1]), "h": float(r[2]), "l": float(r[3]),
               "c": float(r[4]), "v": float(r[6])} for r in res[k]]
        if len(cs) < 2:
            raise ValueError("keine Kursdaten")
        _cache[key] = (cs[:-1], cs[-1])
    except Exception as e:
        _cache[key] = e
        raise
    return _cache[key]
