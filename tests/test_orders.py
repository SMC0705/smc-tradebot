"""Prüft Orders und Gebühren mit selbst gebauten Kerzen: python -m tests.test_orders
(Limit-Kauf, Market-Kauf, Ablauf einer Order, Kauf in der laufenden Kerze, Ziel/Stop-Gebühren, Börsenzeiten)."""
from bot import settings as S
from bot.bots import BOTS
from bot.markets import us_session
from bot.trading import account as A

T0 = 1_790_000_000 - 1_790_000_000 % 3600


def candles(rows, tf=60, t0=T0):
    return [{"t": t0 + i * tf * 60, "o": o, "h": h, "l": l, "c": c, "v": 1.0} for i, (o, h, l, c) in enumerate(rows)]


def once(at, stop, target, **extra):
    """Strategie, die genau einmal (bei Kerze mit Zeit `at`) ein Signal gibt."""
    def fn(c, p):
        if c[-1]["t"] == at:
            return dict({"stop": stop, "target": target, "reason": "Test"}, **extra)
        return None
    return fn


def run(bot, pair, cs, fn, live=None, params=None):
    acc, st = A.new_account(1000.0), A.new_stats()
    A.process(acc, bot, pair, cs, 1.0, params or {}, 0, start_from=0, fn=fn, live=live, stats=st)
    return acc, st


def close(a, b, tol=1e-9):
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def test_limit_fill_target_maker():
    bot = dict(BOTS["trend"], cooldown=0)
    maker, taker = A.fees(bot, "XBTEUR")
    assert (maker, taker) == (S.FEES["crypto"]["maker"], S.FEES["crypto"]["taker"])
    rows = [(100, 101, 99, 100)] * 3 + [(100, 100.5, 99.5, 100)]       # Signal bei Kerze 3 (Schluss 100)
    rows += [(100, 104, 99.6, 103)]    # Kerze 4: fällt unter das Limit (99.7) -> gefüllt; Ziel 104 zählt hier NICHT
    rows += [(103, 104.5, 102.5, 104)]   # Kerze 5: Ziel 104 überschritten -> Limit-Verkauf (Maker)
    cs = candles(rows)
    acc, st = run(bot, "XBTEUR", cs, once(cs[3]["t"], 97.0, 104.0))
    L = 100 - S.LIMIT_RULES["offset_r"] * (100 - 97)
    assert len(acc["trades"]) == 1, acc
    t = acc["trades"][0]
    assert t["result"] == "Ziel" and close(t["entry"], L) and t["exit"] == 104.0, t
    assert st["orders"] == 1 and st["bought"] == 1 and st["sold"] == 1, st
    qty = min(1000 * bot["risk"] / (L - 97.0), 1000 * bot["frac"] / L)      # Größe nach Risiko bzw. Obergrenze
    pnl = qty * 104.0 * (1 - maker) - qty * L * (1 + maker)                 # Kauf und Verkauf je Maker-Gebühr
    assert close(t["pnl"], round(pnl, 2), 1e-3) and close(acc["cash"], 1000 + pnl, 1e-6), (t, pnl)
    return "Limit-Kauf + Ziel als Limit-Verkauf (beides Maker-Gebühr)"


def test_stop_taker_and_fill_candle_rule():
    bot = dict(BOTS["trend"], cooldown=0)
    rows = [(100, 101, 99, 100)] * 3 + [(100, 100.5, 99.5, 100)]
    rows += [(100, 100.2, 96.5, 97)]   # Kerze 4: Limit 99.7 gefüllt, dann Stop 97 gerissen -> Stop-Loss (Taker)
    cs = candles(rows)
    acc, st = run(bot, "XBTEUR", cs, once(cs[3]["t"], 97.0, 104.0))
    t = acc["trades"][0]
    assert t["result"] == "Stop-Loss" and close(t["exit"], 97 * (1 - bot["slip"])), t
    maker, taker = A.fees(bot, "XBTEUR")
    L = t["entry"]
    qty = min(1000 * bot["risk"] / (L - 97.0), 1000 * bot["frac"] / L)
    pnl = qty * t["exit"] * (1 - taker) - qty * L * (1 + maker)             # Verkauf per Stop = Taker
    assert close(acc["cash"], 1000 + pnl, 1e-6) and t["r"] < -1.0, (t, pnl)   # Gebühren machen den Verlust > 1 R
    return "Stop-Loss in der Kauf-Kerze: Market-Verkauf (Taker + Kursabschlag), Ziel zählt dort nicht"


def test_limit_expires():
    bot = dict(BOTS["trend"], cooldown=0)
    rows = [(100, 101, 99, 100)] * 3 + [(100, 100.5, 99.5, 100)]
    rows += [(100, 102, 99.9, 101), (101, 103, 100.5, 102), (102, 103, 101, 102.5)]   # Kurs kommt nicht zurück
    cs = candles(rows)
    acc, st = run(bot, "XBTEUR", cs, once(cs[3]["t"], 97.0, 110.0))
    assert not acc["positions"] and not acc["pending"] and st["unfilled"] == 1, (acc, st)
    return "Limit-Order läuft nach 2 Kerzen ab"


def test_limit_expires_over_gap():
    bot = dict(BOTS["stocks"], cooldown=0)
    cs = candles([(100, 101, 99, 100)] * 4)
    gap = cs[-1]["t"] + 3 * 86400                 # nächste Kurse erst nach dem Wochenende
    cs += [{"t": gap, "o": 99, "h": 99.5, "l": 98.5, "c": 99, "v": 1}]
    acc, st = run(bot, "AAPLxUSD", cs, once(cs[3]["t"], 98.0, 106.0))
    assert not acc["positions"] and st["unfilled"] == 1, (acc, st)
    return "Abgelaufene Limit-Order wird nach einer Kurslücke nicht mehr gefüllt"


def test_market_fill_and_live():
    bot = dict(BOTS["minervini"], cooldown=0)          # Market-Bot, Aktien-Token
    maker, taker = A.fees(bot, "NVDAxUSD")
    assert (maker, taker) == (0.0, 0.0008)
    rows = [(100, 101, 99, 100)] * 4
    cs = candles(rows, tf=1440)
    live = {"t": cs[-1]["t"] + 86400, "o": 100.4, "h": 101, "l": 100.2, "c": 100.8, "v": 1}
    acc, st = run(bot, "NVDAxUSD", cs, once(cs[3]["t"], 92.0, 1000.0), live=live)
    p = acc["positions"]["NVDAxUSD"]
    assert close(p["entry"], 100.4 * (1 + bot["slip"])) and p["opened_t"] == live["t"] and not p["maker_in"], p
    assert close(p["cost"], p["qty"] * p["entry"] * (1 + taker)), p
    return "Market-Kauf sofort in der laufenden Kerze (Taker-Gebühr)"


def test_live_limit_fill():
    bot = dict(BOTS["stocks"], cooldown=0)
    rows = [(100, 101, 99, 100)] * 4
    cs = candles(rows)
    live = {"t": cs[-1]["t"] + 3600, "o": 100, "h": 100.3, "l": 99.5, "c": 99.9, "v": 1}
    acc, st = run(bot, "AAPLxUSD", cs, once(cs[3]["t"], 98.0, 106.0), live=live)
    p = acc["positions"]["AAPLxUSD"]
    assert p["maker_in"] and close(p["entry"], 100 - 0.1 * 2.0) and close(p["cost"], p["qty"] * p["entry"]), p
    return "Limit-Kauf in der laufenden Kerze (Aktien-Token: 0 % Maker)"


def test_fee_filter():
    crypto, stock = BOTS["trend"], BOTS["stocks"]
    assert close(A.min_stop(crypto, "XBTEUR", "limit"), 1.5 * (0.003 + 0.006 + 0.001))
    assert close(A.min_stop(stock, "AAPLxUSD", "limit"), 1.5 * (0.0 + 0.0008 + 0.001))
    assert not A.worth_it(crypto, "XBTEUR", {"stop": 99.0}, 100.0, "limit")      # 1 % < 1,5 %
    assert A.worth_it(stock, "AAPLxUSD", {"stop": 99.0}, 100.0, "limit")        # 1 % > 0,27 %
    return "Gebühren-Filter je Markt"


def test_us_session_eod():
    bot = dict(BOTS["stockday"], cooldown=0)
    sess = None
    day = T0
    while not sess:      # nächster Börsentag
        day += 86400
        sess = us_session(day - day % 86400 + 15 * 3600)
    open_t, close_t = sess
    t0 = open_t - 8 * 900
    n = (close_t - t0) // 900 + 4
    cs = candles([(100, 100.2, 99.9, 100)] * n, tf=15, t0=t0)
    sig_t = open_t + 4 * 900          # Signal-Kerze 10:30–10:45 New Yorker Zeit
    for k in cs:                      # Kerze danach fällt unter das Limit
        if k["t"] == sig_t + 900:
            k["l"] = 99.5
    acc, st = run(bot, "AAPLxUSD", cs, once(sig_t, 99.0, 110.0))
    t = acc["trades"][0]
    assert t["result"] == "Tagesende" and t["closed_t"] + 900 == close_t, (t, close_t)
    # Signal außerhalb der Börsenzeit wird ignoriert
    acc2, st2 = run(bot, "AAPLxUSD", cs, once(t0 + 900, 99.0, 110.0))
    assert st2["signals"] == 0 and not acc2["trades"], st2
    return "Aktien-Daytrading: nur zur Börsenzeit, Verkauf zum Börsenschluss"


def main():
    tests = [test_limit_fill_target_maker, test_stop_taker_and_fill_candle_rule, test_limit_expires, test_limit_expires_over_gap,
             test_market_fill_and_live, test_live_limit_fill, test_fee_filter, test_us_session_eod]
    for t in tests:
        print("✓", t())
    print(f"\n{len(tests)} Order-Tests bestanden.")


if __name__ == "__main__":
    main()
