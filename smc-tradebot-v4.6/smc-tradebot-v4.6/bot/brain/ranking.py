"""Rangliste für den Fokus-Bot: Jede frische Kauf-Gelegenheit aller Bots bekommt eine Note von 0,00 bis 1,00.
Regelbasiert und nachvollziehbar (kein KI-Modell im Betrieb – das kostet bei jedem Lauf Geld und lässt sich
nicht ehrlich zurücktesten). Teilnoten (Gewichte in settings.FOCUS_RULES):
  Bilanz        – wie hat genau dieses Setup bisher nach Gebühren abgeschnitten? (Lern-Konto des Bots, in R)
  Trend         – Marktlage passt? Größerer Trend dagegen -> halbiert
  Chance/Risiko – Abstand zum Ziel geteilt durch Abstand zum Stop (ab 3 : 1 volle Punkte)
  Kosten        – Gebühren + Kursabschlag im Verhältnis zum Risiko (je kleiner, desto besser)
  Nachrichten   – Nachrichtenlage, Gier am Kryptomarkt
  Liquidität    – Geld-Brief-Spanne an der Börse
  Aktualität    – Signal stammt aus der gerade abgeschlossenen Kerze
Warnmuster kosten 0,10, ein bestätigendes gelerntes Kaufmuster bringt 0,05. Fehlende Daten zählen wenig.
Ausgeschlossen: Setups, die bisher klar verlieren, Nachrichten-Sperren, unpassende Marktlage, Klumpenrisiko."""
from .. import settings as S
from ..bots import BOTS
from ..data import kraken
from ..markets import display
from ..strategies.indicators import atr, ema, rsi
from ..trading import account as A
from ..trading import venues as V
from . import analyst, learning as L, news_analyst, risk

FR = S.FOCUS_RULES
W = FR["weights"]


def _lin(x, lo, hi):
    """0 bei lo, 1 bei hi, dazwischen linear."""
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))


def _edge(sig, st):
    """Bisherige Bilanz des Setups: (Lern-Score, Anzahl Tests, Ø R)."""
    pat = sig.get("pattern")
    if pat:
        ps = L.pattern_stats(st).get(pat) or {"score": 0.0, "trades": 0, "avg_r": 0.0}
        return ps["score"], ps["trades"], ps["avg_r"]
    return L.score(st["shadows"][st["active"]]["trades"])


def _liquidity(bot, pair):
    cls = V.fee_class(bot, pair)
    if cls == "fx":
        return 1.0
    if cls == "xstocks":
        return 0.6          # Spanne nicht bekannt -> mittlere Note
    v = V.venue(bot, pair)
    if v.get("spread") is None:
        return 0.5
    return 1 - _lin(v["spread"], 0.0005, S.MAX_SPREAD)


def evaluate(c, team, states, now):
    bid, pair = c["bot"], c["pair"]
    bot, st, sig = BOTS[bid], states[bid], c["sig"]
    block = []
    m, why, _ = news_analyst.factor(team.news, bot, pair, c["t"])
    if m <= 0:
        block.append(why)
    r = team.regimes.get(bot["regime_src"]) if bot["regime_src"] else None
    if r and bot["regime_rules"].get(r["label"], 1.0) <= 0:
        block.append(f"Marktlage „{r['label']}“ passt nicht zur Strategie")
    sc, n, avg = _edge(sig, st)
    if n >= 10 and sc <= FR["bad_edge"]:
        block.append(f"Setup verliert bisher (Ø {avg:+.2f} R aus {n} Tests)")
    msg = risk.exposure_block(team, "focus", pair)
    if msg:
        block.append(msg)
    price, stop, target = c["price"], sig["stop"], sig["target"]
    rr = None if target >= price * 5 else (target - price) / (price - stop)   # ohne festes Ziel: nachgezogener Stop
    htf = analyst.htf_against(bot, pair, c["t"])
    parts = {
        "edge": _lin(sc, FR["bad_edge"], 0.20) if n >= 5 else 0.3,
        "trend": ({"Aufwärts": 1.0, "Seitwärts": 0.5, "Abwärts": 0.0}.get(r["label"], 0.5) if r else 0.5)
                 * (0.5 if htf else 1.0),
        "rr": 0.7 if rr is None else _lin(rr, 1.0, 3.0),
        "cost": 1 - _lin(c["cost_r"], 0.1, 0.6),
        "news": max(0.0, min(1.0, m)),
        "liq": _liquidity(bot, pair),
        "fresh": 1.0 if now - c["t"] <= max(bot["tf"] * 60, 3600) + 1800 else 0.0,
    }
    s = sum(W[k] * parts[k] for k in W)
    if sig.get("warn"):
        s -= 0.10
    if not sig.get("pattern") and set(sig.get("confirm") or []) & L.learned_patterns(st):
        s += 0.05
    return {"pair": pair, "name": display(pair), "bot": bid, "bot_name": bot["name"],
            "score": round(max(0.0, min(1.0, s)), 3), "parts": {k: round(v, 2) for k, v in parts.items()},
            "edge": f"Ø {avg:+.2f} R aus {n} Tests", "rr": round(rr, 2) if rr else None,
            "block": "; ".join(block) or None, "cand": c}


def rank(cands, team, states, now):
    """Alle Kandidaten bewerten, je Wert die beste Gelegenheit, sortiert: erlaubte zuerst, dann nach Note."""
    best = {}
    for c in cands:
        e = evaluate(c, team, states, now)
        old = best.get(c["pair"])
        if old is None or (e["block"] is None, e["score"]) > (old["block"] is None, old["score"]):
            best[c["pair"]] = e
    return sorted(best.values(), key=lambda e: (e["block"] is None, e["score"]), reverse=True)


# --- Markt-Karte (für die Kugel in der App) -------------------------------------------------
# Je Marktgruppe ein Bot, dessen Kerzen ohnehin geladen sind (kein zusätzlicher Abruf).
MAP_BOTS = {"trend": "Krypto", "meme": "Memecoins", "stocks": "Aktien", "krise": "Krisen-Werte", "fx": "Devisen"}


def market_state(bot, pair, closed):
    """Wie gut sieht ein Markt gerade für Käufe aus? Trend 40 %, Schwung 20 %, Bewegung vs. Kosten 20 %, Liquidität 20 %."""
    cl = [x["c"] for x in closed]
    if len(cl) < 210:
        return None
    e20, e50 = ema(cl, 20), ema(cl, 50)
    trend = 0.4 * (cl[-1] > e50[-1]) + 0.3 * (e20[-1] > e50[-1]) + 0.3 * (e50[-1] > e50[-11])
    r = rsi(cl)[-1]
    mom = 1.0 if 50 <= r <= 70 else 0.5 if 40 <= r < 50 or 70 < r <= 80 else 0.0
    move = atr(closed)[-1] / cl[-1]
    vol = _lin(move / A.min_stop(bot, pair, A.order_type(bot)), 0.5, 1.5)
    liq = _liquidity(bot, pair)
    return {"score": round(0.4 * trend + 0.2 * mom + 0.2 * vol + 0.2 * liq, 3),
            "trend": "Aufwärts" if trend >= 0.7 else "Abwärts" if trend <= 0.3 else "Seitwärts",
            "rsi": round(r), "move": round(move * 100, 2), "venue": V.label(V.venue(bot, pair)["name"])}


def market_map(ranked):
    """Alle Märkte mit Note, dazu: gibt es gerade ein Kaufsignal, und wer ist die Nr. 1?"""
    top = next((e for e in ranked if e["block"] is None), None)
    cands = {e["pair"]: e for e in ranked}
    out = []
    for bid, group in MAP_BOTS.items():
        bot = BOTS[bid]
        for pair in bot["pairs"]:
            got = kraken.peek(pair, bot["tf"])
            ms = market_state(bot, pair, got[0]) if got else None
            if not ms:
                continue
            e = cands.get(pair)
            out.append(dict(ms, id=pair, name=display(pair), group=group, signal=e is not None,
                            setup=e["score"] if e else None, setup_bot=e["bot_name"] if e else None,
                            blocked=e["block"] if e else None, top=bool(top and top["pair"] == pair)))
    return out
