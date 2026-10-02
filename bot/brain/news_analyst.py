"""Nachrichten-Analyst: bewertet die gesammelten Nachrichten (data/news.py) und leitet Regeln ab.

Was er tut (alle Grenzwerte in settings.NEWS_RULES):
- Nachrichtenlage Normal / Erhöht / Hoch aus Schlagzeilen-Themen und GDELT-Volumen-Spitzen
  -> weniger Risiko für alle Bots (außer Krisen-Bot)
- Termin-Sperre: keine neuen Kurzfrist-Trades rund um Fed, EZB, US-Inflation, US-Arbeitsmarkt
- Coin-Warnung: Hack, Klage, Verbot zu einem Coin -> dieser Coin pausiert einige Stunden
- Krisen-Themen (Krieg, Öl, Börsen-Stress) schalten den Krisen-Bot frei
- Extreme Gier am Kryptomarkt -> Krypto-Bots vorsichtiger
Wichtig: Schlagzeilen werden nur nach Stichworten sortiert. Das ist grob, aber nachvollziehbar und kostenlos.
"""
import re

from .. import settings as S
from ..markets import ASSET_THEMES, COIN_WORDS, display

NR = S.NEWS_RULES
LEVEL_TEXT = {0: "Normal", 1: "Erhöht", 2: "Hoch"}


def _compile(words, whole):
    if not words:
        return None
    alt = "|".join(re.escape(w) for w in words)
    return re.compile(rf"\b(?:{alt})\b" if whole else rf"\b(?:{alt})", re.IGNORECASE)


PATTERNS = {th: (_compile(d.get("en"), True), _compile(d.get("de"), False)) for th, d in S.THEMES.items()}
COIN_PATTERNS = {pair: _compile(words, True) for pair, words in COIN_WORDS.items()}


def themes_of(title):
    return [th for th, (pe, pd) in PATTERNS.items() if (pe and pe.search(title)) or (pd and pd.search(title))]


def assess(raw, now):
    """Rohdaten -> Lagebild (wird auch so in der App angezeigt)."""
    if not raw:
        return None
    win = NR["window_h"] * 3600
    seen, recent = set(), []
    for h in sorted(raw["headlines"], key=lambda x: -x["t"]):
        key = h["title"].lower()[:90]
        if key in seen or not h["t"] or not (now - win <= h["t"] <= now + 900):
            continue   # ohne Datum lässt sich nicht prüfen, ob die Meldung aktuell ist
        seen.add(key)
        recent.append(dict(h, themes=themes_of(h["title"])))
    counts = {th: sum(1 for h in recent if th in h["themes"]) for th in S.THEMES}
    spikes = {th: (raw["gdelt"].get(th) or {}).get("spike") for th in S.GDELT_QUERIES}
    max_spike = max([v for v in spikes.values() if v] or [0.0])

    def reached(rule):
        hits = [f"{S.THEMES[th]['label']}: {counts[th]} Meldungen" for th, n in rule.items()
                if th != "spike" and counts.get(th, 0) >= n]
        if max_spike >= rule.get("spike", 99):
            hits.append(f"weltweit {max_spike:.1f}× so viele Berichte wie üblich")
        return hits

    reasons = reached(NR["level2"])
    level = 2 if reasons else 0
    if not reasons:
        reasons = reached(NR["level1"])
        level = 1 if reasons else 0
    if level and counts.get("frieden", 0) >= 2:
        level -= 1
        reasons.append("aber Meldungen über Waffenruhe/Gespräche")
    active = [th for th in S.THEMES if th not in ("frieden", "zinsen", "krypto_risiko")
              and (counts[th] >= NR["theme_count"] or (spikes.get(th) or 0) >= NR["theme_spike"])]

    pauses = {}
    for h in recent:
        if "krypto_risiko" not in h["themes"]:
            continue
        until = h["t"] + NR["coin_pause_h"] * 3600
        for pair, pat in COIN_PATTERNS.items():
            if until > now and pat.search(h["title"]) and pair not in pauses:
                pauses[pair] = {"until": until, "title": h["title"], "src": h["src"]}

    termine = raw.get("termine", [])
    before, after = NR["event_before_min"] * 60, NR["event_after_min"] * 60
    upcoming = [e for e in termine if e["t"] + after >= now][:6]
    event_now = next((e for e in termine if e["t"] - before <= now <= e["t"] + after), None)
    hint = None
    if termine and termine[-1]["t"] < now + 14 * 86400:
        hint = "Die Terminliste (config/termine.json) läuft bald aus – bitte neue Termine eintragen."
    if not termine:
        hint = "Keine Wirtschaftstermine geladen (config/termine.json fehlt oder ist leer)."

    return {
        "level": level, "level_text": LEVEL_TEXT[level], "reasons": reasons,
        "themes": [{"id": th, "label": S.THEMES[th]["label"], "count": counts[th], "spike": spikes.get(th),
                    "active": th in active} for th in S.THEMES],
        "active": active, "pauses": pauses, "termine": termine, "upcoming": upcoming, "event_now": event_now,
        "fear_greed": raw.get("fear_greed"), "hint": hint,
        "headlines": [h for h in recent if h["themes"]][:25],
        "sources": {"ok": raw.get("ok", []), "failed": raw.get("failed", [])},
    }


def factor(sit, bot, pair, t_entry):
    """Risiko-Faktor aus der Nachrichtenlage: (faktor, begründung, schlüssel_fürs_protokoll)."""
    if not sit:
        return 1.0, None, None
    if bot["tf"] < 1440:   # Tages-Bots sind von kurzen Termin-Ausschlägen kaum betroffen
        before, after = NR["event_before_min"] * 60, NR["event_after_min"] * 60
        for e in sit["termine"]:
            if e["t"] - before <= t_entry <= e["t"] + after:
                return 0.0, f"Termin-Sperre ({e['name']})", f"ev{e['t']}"
    p = sit["pauses"].get(pair)
    if p and t_entry <= p["until"]:
        return 0.0, f"Warnmeldung zu {display(pair)}: „{p['title'][:70]}“ ({p['src']})", f"cp{pair}"
    if bot.get("needs_theme"):
        th = [t for t in ASSET_THEMES.get(pair, []) if t in sit["active"]]
        if not th:
            return 0.0, "kein passendes Krisen-Thema in den Nachrichten", "nt"
        return 1.0, "Thema aktiv: " + ", ".join(S.THEMES[t]["label"] for t in th), None
    f, why = NR["level_factor"][sit["level"]], []
    if f != 1:
        why.append(f"Nachrichtenlage {sit['level_text']} x{f:g}")
    fg = sit.get("fear_greed")
    if fg and fg["value"] >= NR["greed_limit"] and bot["team"] in ("krypto", "meme"):
        f *= NR["greed_factor"]
        why.append(f"extreme Gier am Kryptomarkt ({fg['value']}) x{NR['greed_factor']:g}")
    return f, (", ".join(why) or None), None


def track(nstate, sit, now):
    """Protokoll der Nachrichtenlage: nur Änderungen werden notiert."""
    if not sit:
        return
    log = nstate.setdefault("log", [])

    def add(msg):
        log.append([now, msg])

    if nstate.get("level") != sit["level"]:
        add(f"Nachrichtenlage jetzt „{sit['level_text']}“" + (f" – {'; '.join(sit['reasons'])}" if sit["reasons"] else ""))
        nstate["level"] = sit["level"]
    for th in set(sit["active"]) - set(nstate.get("active", [])):
        add(f"Thema aktiv: {S.THEMES[th]['label']}")
    for th in set(nstate.get("active", [])) - set(sit["active"]):
        add(f"Thema wieder ruhig: {S.THEMES[th]['label']}")
    nstate["active"] = sit["active"]
    known = nstate.setdefault("pauses", {})
    for pair, p in sit["pauses"].items():
        if known.get(pair) != p["title"]:
            add(f"{display(pair)} pausiert: „{p['title'][:80]}“ ({p['src']})")
            known[pair] = p["title"]
    nstate["pauses"] = {k: v for k, v in known.items() if k in sit["pauses"]}
    nstate["log"] = log[-40:]
