"""Konto & Ausführung (Paper-Trading): Positionsgröße, Stop-Loss, Ziel, Trailing-Stop, Zeit-Ausstiege, Gebühren.
Alle Beträge im Konto in EUR. Kurse von USD/JPY/...-Paaren werden mit `rate` (EUR je Einheit) umgerechnet.

Ablauf pro neuer, abgeschlossener Kerze (identisch in Demo und Backtest):
  1. Signal der vorigen Kerze wird zum Eröffnungskurs dieser Kerze ausgeführt
  2. offene Position wird gegen Hoch/Tief dieser Kerze geprüft
  3. Strategie bewertet die Kerze -> evtl. Signal für die nächste Kerze
"""
from .. import settings as S
from ..strategies import EXITS, SIGNALS, WINDOW, patterns


def new_account(cash=0.0):
    return {"cash": cash, "net_in": cash, "halted": False, "positions": {},
            "trades": [], "pending": {}, "last_t": {}, "marks": {}, "equity_curve": []}


def equity(acc):
    return acc["cash"] + sum(p["qty"] * acc["marks"].get(pair, p["entry"] * p["rate"])
                             for pair, p in acc["positions"].items())


def open_position(acc, bot, pair, sig, px, t, rate, mult):
    fill = px * (1 + bot["slip"])
    if fill <= sig["stop"] or fill >= sig["target"]:
        return
    mult *= sig.get("risk_mult", 1.0)
    eq = equity(acc)
    risk_unit = (fill - sig["stop"]) * rate
    qty = eq * bot["risk"] * mult / risk_unit
    # Team-Faktor < 1 verkleinert auch die Obergrenze, sonst hätte er bei engen Stops keine Wirkung
    max_notional = min(eq * bot["frac"] * min(mult, 1.0), acc["cash"] / (1 + bot["fee"]))
    qty = min(qty, max_notional / (fill * rate))
    cost = qty * fill * rate * (1 + bot["fee"])
    if qty <= 0 or cost < S.MIN_ORDER_EUR:
        return
    acc["cash"] -= cost
    acc["positions"][pair] = {
        "pair": pair, "qty": qty, "entry": fill, "rate": rate, "cost": cost,
        "risk_eur": qty * (fill - sig["stop"]) * rate + cost - qty * fill * rate,
        "stop": sig["stop"], "init_stop": sig["stop"], "target": sig["target"],
        "trail_n": sig.get("trail_n"), "max_hold": sig.get("max_hold"), "eod": sig.get("eod"),
        "opened_t": t, "bars": 0, "reason": sig["reason"], "variant": sig.get("variant", 0),
        "exit": sig.get("exit"), "exit_p": sig.get("exit_p"), "pattern": sig.get("pattern"),
    }


def close_position(acc, bot, pair, px, t, rate, result):
    p = acc["positions"].pop(pair)
    acc.setdefault("cool", {})[pair] = t  # Abkühlphase: kein sofortiger Wiedereinstieg
    proceeds = p["qty"] * px * rate * (1 - bot["fee"])
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


def manage(acc, bot, pair, c, i, rate):
    """Prüft eine offene Position gegen Kerze c[i]: Stop, Ziel, Zeit, Signal-Ausstieg, Nachziehen."""
    p, k = acc["positions"][pair], c[i]
    p["bars"] += 1
    slip = bot["slip"]
    if k["l"] <= p["stop"]:
        px = min(p["stop"], k["o"]) * (1 - slip)
        if p["stop"] > p["entry"]:
            res = "Trailing-Stop" if p["trail_n"] else "Einstand"
        else:
            res = "Stop-Loss"
        return close_position(acc, bot, pair, px, k["t"], rate, res)
    if k["h"] >= p["target"]:
        return close_position(acc, bot, pair, max(p["target"], k["o"]) * (1 - slip), k["t"], rate, "Ziel")
    if p["max_hold"] and p["bars"] >= p["max_hold"]:
        return close_position(acc, bot, pair, k["c"] * (1 - slip), k["t"], rate, "Zeitablauf")
    if p["eod"] and (k["t"] + bot["tf"] * 60) % 86400 == 0:
        return close_position(acc, bot, pair, k["c"] * (1 - slip), k["t"], rate, "Tagesende")
    if p.get("exit") and EXITS[p["exit"]](c[max(0, i - WINDOW + 1):i + 1], p.get("exit_p") or {}):
        return close_position(acc, bot, pair, k["c"] * (1 - slip), k["t"], rate, "Signal-Ausstieg")
    # Stop auf Einstand (inkl. Gebühren), sobald 1x Risiko im Plus
    if k["h"] >= p["entry"] + (p["entry"] - p["init_stop"]):
        p["stop"] = max(p["stop"], p["entry"] * (1 + 2 * bot["fee"]))
    if p["trail_n"] and i + 1 >= p["trail_n"]:
        p["stop"] = max(p["stop"], min(x["l"] for x in c[i - p["trail_n"] + 1:i + 1]))


def worth_it(bot, sig, price):
    """Gebühren-Filter: Lohnt sich der Trade? Der Stop muss weit genug weg sein, sonst fressen
    Kauf- und Verkaufsgebühren den größten Teil des Risikos (bei Kraken 2 x 0,4 %)."""
    return (price - sig["stop"]) / price >= S.MIN_RISK_FEE_MULT * 2 * bot["fee"]


def process(acc, bot, pair, closed, rate, params, variant, mult=1.0, can_open=True, start_from=None, gate=None,
            fn=None, tag_patterns=False):
    """Verarbeitet alle neuen abgeschlossenen Kerzen eines Paares für ein Konto.
    gate(pair, signal, t) -> Faktor fürs Risiko (0 = Team blockiert); nur fürs echte Konto.
    fn = eigene Signal-Funktion (sonst die Strategie des Bots). tag_patterns = Muster-Hinweise an Signale hängen."""
    fn = fn or SIGNALS[bot["strategy"]]
    last = acc["last_t"].get(pair)
    if last is None:
        if start_from is None:  # echtes Konto: ab jetzt handeln, keine Vergangenheit
            acc["last_t"][pair] = closed[-1]["t"]
            acc["marks"][pair] = closed[-1]["c"] * rate
            return
        last = closed[max(start_from, 0)]["t"] - 1
    for i, k in enumerate(closed):
        if k["t"] <= last:
            continue
        sig = acc["pending"].pop(pair, None)
        cooling = k["t"] - acc.get("cool", {}).get(pair, -10 ** 12) < bot.get("cooldown", 0) * bot["tf"] * 60
        if sig and can_open and mult > 0 and not cooling and not acc["halted"] and pair not in acc["positions"] \
                and len(acc["positions"]) < bot["max_pos"]:
            m = mult * (gate(pair, sig, k["t"]) if gate else 1.0)
            if m > 0:
                open_position(acc, bot, pair, sig, k["o"], k["t"], rate, m)
        acc["marks"][pair] = k["c"] * rate
        if pair in acc["positions"]:
            manage(acc, bot, pair, closed, i, rate)
        if pair not in acc["positions"] and i >= 1:
            window = closed[max(0, i - WINDOW + 1):i + 1]
            s = fn(window, params)
            if s and worth_it(bot, s, k["c"]):
                s["variant"] = variant
                if tag_patterns:   # für das Team: passende Kauf- bzw. Warnmuster zum Signal
                    s["confirm"] = [x["pattern"] for x in patterns.find(window)]
                    s["warn"] = patterns.bearish_names(window)
                acc["pending"][pair] = s
        acc["last_t"][pair] = k["t"]


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
