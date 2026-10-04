"""Konto & Ausführung (Paper-Trading): Kauf-Orders, Positionsgröße, Stop-Loss, Ziel, Trailing-Stop,
Zeit-Ausstiege und Gebühren wie bei Kraken. Alle Beträge im Konto in EUR. Kurse von USD/JPY/...-Paaren
werden mit `rate` (EUR je Einheit) umgerechnet.

Weg eines Trades (identisch in Demo und Lern-Konten):
  1. Signal bei Kerzenschluss -> Gebühren-Filter -> eigene Regeln (Pause, Abkühlung, Limits) -> Team
  2. Kauf-Order:
     - Limit (Standard): etwas unter dem Signalkurs. Gefüllt, sobald der Kurs darunter fällt -> Maker-Gebühr,
       kein Kursabschlag. Kommt der Kurs nicht zurück, wird die Order nach 2 Kerzen gelöscht.
     - Market (schnelle Ausbrüche): zum Eröffnungskurs der nächsten Kerze -> Taker-Gebühr + Kursabschlag.
     Orders werden auch gegen die gerade laufende Kerze geprüft: ein Kauf erscheint im selben Lauf.
  3. Jede Kerze: Stop (Market), Ziel (Limit-Verkauf), Zeitablauf, Tagesende, Signal-Ausstieg, Stop nachziehen.
Vorsichtig gerechnet: In der Kerze eines Limit-Kaufs zählt nur der Stop, nicht das Ziel (Reihenfolge unbekannt).
"""
from .. import settings as S
from ..markets import FOREX, display, us_session
from ..strategies import EXITS, SIGNALS, WINDOW, patterns


def new_account(cash=0.0):
    return {"cash": cash, "net_in": cash, "halted": False, "positions": {},
            "trades": [], "pending": {}, "last_t": {}, "marks": {}, "equity_curve": []}


def equity(acc):
    return acc["cash"] + sum(p["qty"] * acc["marks"].get(pair, p["entry"] * p["rate"])
                             for pair, p in acc["positions"].items())


# --- Gebühren ----------------------------------------------------------------------------
def fee_class(bot, pair):
    if bot.get("source") == "pumpfun":
        return "dex"
    if pair in FOREX:
        return "fx"
    if pair.endswith("xUSD"):      # Kraken xStocks (Aktien-Token)
        return "xstocks"
    return "crypto"


def fees(bot, pair):
    """(Maker, Taker) je Richtung für diesen Wert – siehe settings.FEES."""
    f = S.FEES[fee_class(bot, pair)]
    return f["maker"], f["taker"]


def order_type(bot, params=None):
    return (params or {}).get("entry") or bot.get("entry", "limit")


def costs(bot, pair, typ):
    """Kauf + Verkauf als Anteil vom Kurs. Verkauf im ungünstigen Fall per Stop (= Market)."""
    maker, taker = fees(bot, pair)
    buy = maker if typ == "limit" else taker + bot["slip"]
    return buy + taker + bot["slip"]


def min_stop(bot, pair, typ):
    """So weit muss der Stop mindestens entfernt sein (Anteil vom Kurs), damit sich ein Trade lohnen kann."""
    return S.MIN_RISK_FEE_MULT * costs(bot, pair, typ)


def worth_it(bot, pair, sig, price, typ="market"):
    """Gebühren-Filter: Ist der Stop zu nah, fressen die Kosten den größten Teil des Risikos."""
    return (price - sig["stop"]) / price >= min_stop(bot, pair, typ)


# --- Kaufen & Verkaufen --------------------------------------------------------------------
def open_position(acc, bot, pair, sig, px, t, rate, mult, maker=False):
    """Kauft. maker=True: Limit-Order zum Preis px. Sonst Market (mit Kursabschlag).
    Gibt None zurück, wenn gekauft wurde – sonst den Grund, warum nicht."""
    f_maker, f_taker = fees(bot, pair)
    fee = f_maker if maker else f_taker
    fill = px if maker else px * (1 + bot["slip"])
    if fill <= sig["stop"] or fill >= sig["target"]:
        return "Kurs schon unter dem Stop bzw. über dem Ziel"
    mult *= sig.get("risk_mult", 1.0)
    eq = equity(acc)
    risk_unit = (fill - sig["stop"]) * rate
    qty = eq * bot["risk"] * mult / risk_unit
    # Team-Faktor < 1 verkleinert auch die Obergrenze, sonst hätte er bei engen Stops keine Wirkung
    max_notional = min(eq * bot["frac"] * min(mult, 1.0), acc["cash"] / (1 + fee))
    qty = min(qty, max_notional / (fill * rate))
    cost = qty * fill * rate * (1 + fee)
    if qty <= 0 or cost < S.MIN_ORDER_EUR:
        if acc["cash"] < S.MIN_ORDER_EUR * (1 + fee):
            return "kein freies Geld"
        return f"Position wäre kleiner als die Mindestgröße von {S.MIN_ORDER_EUR:.0f} € (Risiko x{mult:.2f})"
    acc["cash"] -= cost
    acc["positions"][pair] = {
        "pair": pair, "qty": qty, "entry": fill, "rate": rate, "cost": cost,
        "risk_eur": qty * (fill - sig["stop"]) * rate + cost - qty * fill * rate,
        "stop": sig["stop"], "init_stop": sig["stop"], "target": sig["target"],
        "be": fill * (1 + fee) / ((1 - f_taker) * (1 - bot["slip"])),   # Einstand nach allen Kosten
        "maker_in": maker, "trail_n": sig.get("trail_n"), "max_hold": sig.get("max_hold"), "eod": sig.get("eod"),
        "opened_t": t, "bars": 0, "reason": sig["reason"], "variant": sig.get("variant", 0),
        "exit": sig.get("exit"), "exit_p": sig.get("exit_p"), "pattern": sig.get("pattern"),
    }
    return None


def close_position(acc, bot, pair, px, t, rate, result, maker=False):
    """Verkauft. maker=True: Limit-Verkauf (Ziel), sonst Market."""
    p = acc["positions"].pop(pair)
    acc.setdefault("cool", {})[pair] = t  # Abkühlphase: kein sofortiger Wiedereinstieg
    f_maker, f_taker = fees(bot, pair)
    proceeds = p["qty"] * px * rate * (1 - (f_maker if maker else f_taker))
    acc["cash"] += proceeds
    pnl = proceeds - p["cost"]
    if acc.get("lean"):  # Schatten-Konten speichern nur das Nötigste (kleine Dateien)
        rec = {"pair": pair, "r": round(pnl / max(p["risk_eur"], 1e-9), 3), "closed_t": t}
        if p.get("pattern"):
            rec["pattern"] = p["pattern"]
        acc["trades"] = (acc["trades"] + [rec])[-300 if acc.get("muster") else -150:]
        return
    acc["trades"].append({
        "pair": pair, "entry": p["entry"], "exit": px, "pnl": round(pnl, 2),
        "pnl_pct": round(pnl / p["cost"] * 100, 2), "r": round(pnl / max(p["risk_eur"], 1e-9), 3),
        "opened_t": p["opened_t"], "closed_t": t, "result": result, "reason": p["reason"],
        "variant": p["variant"], "pattern": p.get("pattern"),
    })
    acc["trades"] = acc["trades"][-400:]


def _eod_due(p, k, tf_s):
    if p["eod"] == "us":    # Aktien: zum Schluss der US-Börse
        sess = us_session(k["t"])
        return sess is None or k["t"] + tf_s >= sess[1]
    return (k["t"] + tf_s) % 86400 == 0


def manage(acc, bot, pair, c, i, rate):
    """Prüft eine offene Position gegen Kerze c[i]: Stop, Ziel, Zeit, Signal-Ausstieg, Nachziehen."""
    p, k = acc["positions"][pair], c[i]
    p["bars"] += 1
    slip = bot["slip"]
    if k["l"] <= p["stop"]:   # Stop-Loss = Market-Verkauf
        px = min(p["stop"], k["o"]) * (1 - slip)
        if p["stop"] > p["entry"]:
            res = "Trailing-Stop" if p["trail_n"] else "Einstand"
        else:
            res = "Stop-Loss"
        return close_position(acc, bot, pair, px, k["t"], rate, res)
    if p.get("maker_in") and k["t"] == p["opened_t"]:
        return   # Kauf-Kerze eines Limit-Kaufs: nur der Stop zählt
    if fee_class(bot, pair) == "dex":   # pump.fun: Swaps gibt es nur zum Marktpreis
        if k["h"] >= p["target"]:
            return close_position(acc, bot, pair, max(p["target"], k["o"]) * (1 - slip), k["t"], rate, "Ziel")
    elif k["h"] > p["target"]:  # Ziel = Limit-Verkauf, gefüllt sobald der Kurs darüber handelt
        return close_position(acc, bot, pair, p["target"], k["t"], rate, "Ziel", maker=True)
    if p["max_hold"] and p["bars"] >= p["max_hold"]:
        return close_position(acc, bot, pair, k["c"] * (1 - slip), k["t"], rate, "Zeitablauf")
    if p["eod"] and _eod_due(p, k, bot["tf"] * 60):
        return close_position(acc, bot, pair, k["c"] * (1 - slip), k["t"], rate, "Tagesende")
    if p.get("exit") and EXITS[p["exit"]](c[max(0, i - WINDOW + 1):i + 1], p.get("exit_p") or {}):
        return close_position(acc, bot, pair, k["c"] * (1 - slip), k["t"], rate, "Signal-Ausstieg")
    # Stop auf Einstand (nach allen Kosten), sobald 1x Risiko im Plus
    if k["h"] >= p["entry"] + (p["entry"] - p["init_stop"]):
        be = p.get("be") or p["entry"] * (1 + costs(bot, pair, "market"))
        p["stop"] = max(p["stop"], be)
    if p["trail_n"] and i + 1 >= p["trail_n"]:
        p["stop"] = max(p["stop"], min(x["l"] for x in c[i - p["trail_n"] + 1:i + 1]))


# --- Prüfprotokoll (nur echtes Konto) ------------------------------------------------------
PRIO = {"bought": 0, "orders": 1, "team": 2, "unfilled": 3, "own": 4, "too_small": 5}


def new_stats():
    return {"pairs": 0, "candles": 0, "signals": 0, "too_small": 0, "own": 0, "team": 0, "orders": 0,
            "unfilled": 0, "bought": 0, "sold": 0, "notes": []}


def _count(stats, key, t=None, pair=None, note=None):
    if stats is None:
        return
    stats[key] += 1
    if note:
        stats["notes"].append([PRIO.get(key, 9), t, f"{display(pair)}: {note}"])


def _pct(x):
    return f"{x * 100:.2f}".rstrip("0").rstrip(".").replace(".", ",") + " %"


def _num(x):
    txt = f"{x:.10f}".rstrip("0") if abs(x) < 0.001 else f"{x:.6g}"
    return txt.replace(".", ",")


# --- Orders --------------------------------------------------------------------------------
def _own_block(acc, bot, pair, t, ctx):
    """Eigene Regeln des Bots vor einer Order: Text = Grund, None = alles in Ordnung."""
    if not ctx["can_open"]:
        return "Bot ist ausgeschaltet (0 %)"
    if ctx["mult"] <= 0:
        return "Wert pausiert (Lernen)"
    if acc["halted"]:
        return "Not-Aus aktiv"
    if t - acc.get("cool", {}).get(pair, -10 ** 12) < bot.get("cooldown", 0) * bot["tf"] * 60:
        return "Abkühlphase nach dem letzten Verkauf"
    if len(acc["positions"]) >= bot["max_pos"]:
        return f"schon {bot['max_pos']} Positionen offen"
    return None


def _place(acc, bot, pair, s, window, k, params, variant, ctx, tag_patterns):
    """Signal -> Gebühren-Filter -> eigene Regeln -> Team -> Kauf-Order (gilt ab der nächsten Kerze)."""
    stats, tf = ctx["stats"], bot["tf"] * 60
    t = k["t"] + tf
    if bot.get("session") == "us":   # Börsen-Bot: nur zur US-Handelszeit, Verkauf spätestens zum Börsenschluss
        sess = us_session(k["t"])
        if not sess or k["t"] < sess[0] or t > sess[1] - 30 * 60:
            return
        s["eod"] = "us"
    _count(stats, "signals")
    typ = order_type(bot, params)
    price = k["c"] - S.LIMIT_RULES["offset_r"] * (k["c"] - s["stop"]) if typ == "limit" else k["c"]
    if price <= s["stop"]:
        return
    if not worth_it(bot, pair, s, price, typ):
        _count(stats, "too_small", t, pair, f"Signal zu klein – Stop {_pct((price - s['stop']) / price)} entfernt, "
                                            f"nötig {_pct(min_stop(bot, pair, typ))} (Gebühren)")
        return
    why = _own_block(acc, bot, pair, t, ctx)
    if why:
        _count(stats, "own", t, pair, f"Signal, aber {why}")
        return
    s["variant"] = variant
    if tag_patterns:   # für das Team: passende Kauf- bzw. Warnmuster zum Signal
        s["confirm"] = [x["pattern"] for x in patterns.find(window)]
        s["warn"] = patterns.bearish_names(window)
    m, gate = ctx["mult"], ctx["gate"]
    if gate:
        m *= gate(pair, s, t)
        if m <= 0:
            _count(stats, "team", t, pair, f"Team sagt nein – {getattr(gate, 'reason', None) or 'Team-Regel'}")
            return
    valid = S.LIMIT_RULES["valid_daily" if bot["tf"] >= 1440 else "valid"]
    acc["pending"][pair] = {"sig": s, "type": typ, "price": price, "from": t, "until": t + valid * tf, "m": m}
    _count(stats, "orders", t, pair, f"Limit-Kauf bei {_num(price)} gelegt ({s['reason']})" if typ == "limit"
                                     else f"Kauf zum Marktpreis ({s['reason']})")


def _fill(acc, bot, pair, k, rate, ctx, final):
    """Prüft eine wartende Kauf-Order gegen Kerze k. final=False: laufende, noch offene Kerze."""
    o = acc["pending"].get(pair)
    if not o or k["t"] < o["from"]:
        return
    stats, tf = ctx["stats"], bot["tf"] * 60
    if o["type"] == "limit" and k["t"] >= o["until"]:   # Lücke in den Kursdaten (z. B. Wochenende): Order ist abgelaufen
        del acc["pending"][pair]
        _count(stats, "unfilled", o["until"], pair, "Limit-Kauf nicht gefüllt – der Kurs kam nicht zurück")
        return
    stop_why = ("Bot ist ausgeschaltet (0 %)" if not ctx["can_open"] else "Not-Aus aktiv" if acc["halted"]
                else "keine freie Position mehr" if pair in acc["positions"] or len(acc["positions"]) >= bot["max_pos"]
                else None)
    if stop_why:
        del acc["pending"][pair]
        _count(stats, "own", k["t"], pair, f"Order gelöscht – {stop_why}")
        return
    m = o.get("m")
    if m is None:   # Order aus der Zeit vor v4.3: Team jetzt fragen
        gate = ctx["gate"]
        m = ctx["mult"] * (gate(pair, o["sig"], k["t"]) if gate else 1.0)
        if m <= 0:
            del acc["pending"][pair]
            _count(stats, "team", k["t"], pair, f"Team sagt nein – {getattr(gate, 'reason', None) or 'Team-Regel'}")
            return
    if o["type"] == "market":
        del acc["pending"][pair]
        why = open_position(acc, bot, pair, o["sig"], k["o"], k["t"], rate, m)
    elif k["l"] < o["price"]:
        del acc["pending"][pair]
        why = open_position(acc, bot, pair, o["sig"], o["price"], k["t"], rate, m, maker=True)
    else:
        if final and k["t"] + tf >= o["until"]:
            del acc["pending"][pair]
            _count(stats, "unfilled", k["t"] + tf, pair, "Limit-Kauf nicht gefüllt – der Kurs kam nicht zurück")
        return
    if why is None:
        p = acc["positions"][pair]
        _count(stats, "bought", k["t"], pair, f"gekauft zu {_num(p['entry'])} ({'Limit' if p['maker_in'] else 'Market'})")
    else:
        _count(stats, "own", k["t"], pair, f"Kauf nicht möglich – {why}")


def process(acc, bot, pair, closed, rate, params, variant, mult=1.0, can_open=True, start_from=None, gate=None,
            fn=None, tag_patterns=False, live=None, stats=None):
    """Verarbeitet alle neuen abgeschlossenen Kerzen eines Paares für ein Konto, danach die laufende Kerze.
    gate(pair, signal, t) -> Faktor fürs Risiko (0 = Team blockiert); nur fürs echte Konto.
    fn = eigene Signal-Funktion (sonst die Strategie des Bots). tag_patterns = Muster-Hinweise an Signale hängen.
    live = laufende Kerze (Orders werden sofort geprüft). stats = Zähler fürs Prüfprotokoll."""
    fn = fn or SIGNALS[bot["strategy"]]
    last = acc["last_t"].get(pair)
    if last is None:
        if start_from is None:  # echtes Konto: ab jetzt handeln, keine Vergangenheit
            acc["last_t"][pair] = closed[-1]["t"]
            acc["marks"][pair] = closed[-1]["c"] * rate
            return
        last = closed[max(start_from, 0)]["t"] - 1
    ctx = {"mult": mult, "can_open": can_open, "gate": gate, "stats": stats}
    for i, k in enumerate(closed):
        if k["t"] <= last:
            continue
        if stats is not None:
            stats["candles"] += 1
        _fill(acc, bot, pair, k, rate, ctx, final=True)
        acc["marks"][pair] = k["c"] * rate
        if pair in acc["positions"]:
            manage(acc, bot, pair, closed, i, rate)
            if pair not in acc["positions"]:
                _count(stats, "sold")
        if pair not in acc["positions"] and pair not in acc["pending"] and i >= 1:
            window = closed[max(0, i - WINDOW + 1):i + 1]
            s = fn(window, params)
            if s:
                _place(acc, bot, pair, s, window, k, params, variant, ctx, tag_patterns)
        acc["last_t"][pair] = k["t"]
    if live is not None and live["t"] > acc["last_t"].get(pair, -1):
        _fill(acc, bot, pair, live, rate, ctx, final=False)   # sofort ausführen, nicht erst eine Kerze später


def update_risk(acc):
    """Not-Aus: Verlust vom bisher besten Stand > 25 % des zugeteilten Kapitals.
    Gemessen am Gewinn (Guthaben minus Einzahlungen), damit Umbuchungen nicht zählen."""
    eq = equity(acc)
    pnl = eq - acc["net_in"]
    acc["peak_pnl"] = max(acc.get("peak_pnl", 0.0), pnl)
    acc["cap"] = max(acc.get("cap", 0.0), acc["net_in"])  # höchstes zugeteiltes Kapital
    if acc["net_in"] > 50 and (acc["peak_pnl"] - pnl) > S.MAX_DRAWDOWN_STOP * acc["net_in"]:
        acc["halted"] = True
    return eq
