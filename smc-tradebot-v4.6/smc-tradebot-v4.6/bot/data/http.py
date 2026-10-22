"""Gemeinsamer Internet-Abruf für alle Datenquellen: Wartezeit je Anbieter (damit wir nie
gesperrt werden), einheitlicher Absender, Zeitlimit."""
import json
import time
import urllib.request

UA = "smc-tradebot/3.0 (Demo-Trading-Bot; github.com)"
_last = {}


def fetch(url, key, gap=1.0, timeout=20, headers=None):
    """Lädt eine Adresse. key = Anbieter (z. B. "kraken"), gap = Mindestabstand in Sekunden."""
    wait = gap - (time.time() - _last.get(key, 0.0))
    if wait > 0:
        time.sleep(wait)
    _last[key] = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def get_json(url, key, gap=1.0, **kw):
    return json.loads(fetch(url, key, gap, **kw).decode("utf-8"))
