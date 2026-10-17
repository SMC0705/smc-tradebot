"""Revolut X (Krypto-Börse, MiCA-Lizenz Zypern): öffentliche Kurse, kein API-Schlüssel nötig.
Pro Lauf EIN Abruf aller Ticker (Geld/Brief). Daraus ergibt sich, welche Coins dort eng genug gehandelt
werden und wie groß der Kursabschlag ist. Ist Revolut X nicht erreichbar, rechnen die Bots wie früher mit Kraken."""
from . import http

API = "https://revx.revolut.com/api"
_quotes = None   # Ergebnis dieses Laufs


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def symbol(pair):
    """Kraken-Name -> Revolut-X-Name, z. B. XBTEUR -> BTC/EUR."""
    base, quote = pair[:-3], pair[-3:]
    return f"{ {'XBT': 'BTC', 'XDG': 'DOGE'}.get(base, base) }/{quote}"


def load(errors):
    """Alle Ticker holen (einmal pro Lauf)."""
    global _quotes
    try:
        data = http.get_json(f"{API}/1.0/public/tickers?region=EEA", "revx", gap=1.1).get("data", [])
        out = {}
        for x in data:
            bid, ask = _f(x.get("bid")), _f(x.get("ask"))
            if bid > 0 and ask >= bid:
                out[x.get("symbol")] = {"bid": bid, "ask": ask, "spread": (ask - bid) / ((ask + bid) / 2),
                                        "vol": _f(x.get("quote_volume_24h"))}
        _quotes = out
    except Exception as e:
        _quotes = {}
        errors.append(f"Revolut X nicht erreichbar ({e}) – Krypto diesen Lauf mit Kraken-Gebühren")
    return _quotes


def quote(pair):
    """Geld/Brief/Spanne eines Werts bei Revolut X oder None (nicht gelistet / nicht geladen)."""
    return (_quotes or {}).get(symbol(pair))
