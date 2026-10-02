"""Nachrichten-Daten aus vertrauenswürdigen, kostenlosen Quellen (holt nur – bewertet nichts):
- RSS-Feeds offizieller Redaktionen und Notenbanken (Liste in settings.NEWS_FEEDS)
- GDELT: weltweites Nachrichten-Monitoring, gefiltert auf seriöse Redaktionen (settings.NEWS_DOMAINS)
- Crypto Fear & Greed Index (alternative.me)
- Wirtschaftstermine aus config/termine.json (Fed, EZB, US-Inflation, US-Arbeitsmarkt)
Bewertet wird in brain/news_analyst.py.
"""
import json
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from .. import settings as S
from . import http

GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"


def _ts(text):
    """Datum aus RSS/Atom/GDELT/termine.json -> Unix-Zeit (ohne Zeitzone = UTC)."""
    if not text:
        return 0
    text = text.strip()
    try:
        return int(parsedate_to_datetime(text).timestamp())
    except Exception:
        pass
    try:
        d = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return int((d if d.tzinfo else d.replace(tzinfo=timezone.utc)).timestamp())
    except Exception:
        pass
    try:
        return int(datetime.strptime(text, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).timestamp())
    except Exception:
        return 0


def _local(tag):
    return tag.rsplit("}", 1)[-1].lower()


def parse_feed(xml_bytes, source):
    """RSS 2.0, RSS 1.0 (RDF) und Atom -> [{src, title, link, t}]"""
    out = []
    root = ET.fromstring(xml_bytes)
    for el in root.iter():
        if _local(el.tag) not in ("item", "entry"):
            continue
        title = link = date = ""
        for ch in el:
            name = _local(ch.tag)
            if name == "title":
                title = (ch.text or "").strip()
            elif name == "link":
                link = (ch.text or "").strip() or ch.attrib.get("href", "")
            elif name in ("pubdate", "date", "updated", "published"):
                date = date or (ch.text or "")
        if title:
            out.append({"src": source, "title": title, "link": link, "t": _ts(date)})
    return out


def rss_headlines(errors, ok, failed):
    items = []
    for name, url in S.NEWS_FEEDS:
        try:
            items += parse_feed(http.fetch(url, "rss", gap=0.5), name)
            ok.append(name)
        except Exception as e:
            failed.append(name)
            errors.append(f"Nachrichtenquelle {name}: {str(e)[:80]}")
    return items


def _domains():
    return "(" + " OR ".join(f"domainis:{d}" for d in S.NEWS_DOMAINS) + ")"


def _gdelt(params):
    url = GDELT + "?" + urllib.parse.urlencode(dict(params, format="json"))
    raw = http.fetch(url, "gdelt", gap=6.0, timeout=30)   # GDELT bittet um max. 1 Anfrage je 5 Sek.
    return json.loads(raw.decode("utf-8"))


def gdelt_spikes(errors, ok, failed):
    """Wie viel wird gerade über ein Thema berichtet – im Vergleich zu den letzten 7 Tagen?
    spike = Artikel der letzten 6 Std. / üblicher 6-Std.-Wert (Median)."""
    out = {}
    for theme, q in S.GDELT_QUERIES.items():
        try:
            d = _gdelt({"query": f"{q} {_domains()}", "mode": "timelinevolraw", "timespan": "7d"})
            series = (d.get("timeline") or [{}])[0].get("data", [])
            vals = [float(x.get("value", 0)) for x in series]
            if len(vals) < 48:
                continue
            step = 24 if len(vals) > 300 else max(len(vals) // 28, 1)   # 15-Min.- oder Stunden-Raster
            recent = sum(vals[-step:])
            windows = sorted(sum(vals[i:i + step]) for i in range(0, len(vals) - step, step))
            base = windows[len(windows) // 2] if windows else 0
            out[theme] = {"recent": int(recent), "base": round(base, 1), "spike": round(recent / max(base, 1.0), 2)}
            ok.append(f"GDELT {theme}")
        except Exception as e:
            failed.append(f"GDELT {theme}")
            errors.append(f"GDELT ({theme}): {str(e)[:80]}")
    return out


def gdelt_articles(errors, ok, failed):
    """Aktuelle Schlagzeilen seriöser Redaktionen zu Krieg, Öl, Zöllen, Sanktionen."""
    q = "(war OR invasion OR missile OR oil OR opec OR tariffs OR sanctions OR crash)"
    try:
        d = _gdelt({"query": f"{q} {_domains()}", "mode": "artlist", "maxrecords": 30,
                    "timespan": "12h", "sort": "datedesc"})
        ok.append("GDELT Schlagzeilen")
        return [{"src": a.get("domain", "GDELT"), "title": a.get("title", ""), "link": a.get("url", ""),
                 "t": _ts(a.get("seendate", ""))} for a in d.get("articles", []) if a.get("title")]
    except Exception as e:
        failed.append("GDELT Schlagzeilen")
        errors.append(f"GDELT (Schlagzeilen): {str(e)[:80]}")
        return []


def fear_greed(errors):
    try:
        d = http.get_json("https://api.alternative.me/fng/?limit=1", "fng")["data"][0]
        return {"value": int(d["value"]), "label": d.get("value_classification", "")}
    except Exception as e:
        errors.append(f"Fear & Greed: {str(e)[:60]}")
        return None


def load_termine():
    """Wirtschaftstermine aus config/termine.json -> [{name, t}] (Zeiten in UTC)."""
    try:
        with open(S.TERMINE_FILE) as f:
            data = json.load(f)
        return sorted(({"name": x["name"], "t": _ts(x["utc"])} for x in data.get("termine", [])),
                      key=lambda x: x["t"])
    except Exception:
        return []


def collect(errors):
    """Alles in einem Rutsch holen (ca. 30 Sek.)."""
    ok, failed = [], []
    headlines = rss_headlines(errors, ok, failed)
    spikes = gdelt_spikes(errors, ok, failed)
    headlines += gdelt_articles(errors, ok, failed)
    return {"headlines": headlines, "gdelt": spikes, "fear_greed": fear_greed(errors),
            "termine": load_termine(), "ok": ok, "failed": failed, "fetched": int(time.time())}
