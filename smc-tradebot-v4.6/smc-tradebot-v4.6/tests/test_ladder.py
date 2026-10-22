"""Prüft Inkubations-Leiter und Decay-Check mit erfundenen Trades: python -m tests.test_ladder
(Start auf Probe, kein Aufstieg durch Zeit, Aufstieg ¼ -> ½ -> voll, Abstieg, Variantenwechsel, Ersatzbank und Rückkehr,
Mindestgröße bei kleinem Risiko, keine Käufe auf der Ersatzbank)."""
from bot import settings as S
from bot.bots import BOTS
from bot.brain import ladder
from bot.trading import account as A
from bot.trading import runner

LR = S.LADDER_RULES
T0 = 1_790_000_000
BOT = BOTS["trend"]
LAB = runner.labels(BOT)


def fresh():
    st = runner.new_state(BOT)
    st["real"]["cash"] = st["real"]["net_in"] = 1000.0
    runner.prepare(st, BOT)
    return st


def add(acc, *rs):
    """Hängt abgeschlossene Trades mit Ergebnis r an – mit laufender Nummer wie close_position."""
    for r in rs:
        acc["n_closed"] = acc.get("n_closed", 0) + 1
        acc["trades"].append({"pair": "XBTEUR", "r": r, "pnl": r, "closed_t": T0, "seq": acc["n_closed"]})


def step(st, now=T0):
    ladder.update(st, LAB, now=now)
    return st["ladder"]["stage"]


def test_start_and_time():
    st = fresh()
    assert st["ladder"]["stage"] == "probe" and ladder.factor(st) == 0.25
    for d in range(60):   # 60 Tage ohne Trades: kein Aufstieg
        assert step(st, T0 + d * 86400) == "probe"
    add(st["real"], *[0.5] * (LR["probe_n"] - 1))   # 9 Gewinner reichen noch nicht
    assert step(st) == "probe"
    return "Start auf Probe (¼ Risiko), kein Aufstieg durch Zeit oder zu wenige Trades"


def test_old_trades_dont_count():
    st = runner.new_state(BOT)
    st["real"]["trades"] = [{"pair": "XBTEUR", "r": 2.0, "pnl": 5.0, "closed_t": T0} for _ in range(40)]   # vor v4.6
    runner.prepare(st, BOT)
    assert step(st) == "probe" and ladder.status(st, LAB)["next"]["have"] == 0
    return "Trades aus der Zeit vor v4.6 zählen nicht für die Leiter"


def test_climb():
    st = fresh()
    add(st["real"], *[0.6, -1.0] * 5)        # 10 Trades, Ø −0,2 R -> bleibt
    assert step(st) == "probe"
    add(st["real"], *[1.5] * 4)              # jetzt 14 Trades auf Probe, Ø > 0 -> ½
    assert step(st) == "halb" and ladder.factor(st) == 0.5
    add(st["real"], *[0.4] * (LR["halb_n"] - 1))
    assert step(st) == "halb"                # 19 auf ½: noch nicht
    add(st["real"], 0.4)
    assert step(st) == "voll" and ladder.factor(st) == 1.0
    return "Aufstieg ¼ -> ½ (10 Trades im Plus) -> voll (20 Trades auf ½, letzte 30 im Plus)"


def test_decay_replace_and_weak():
    st = fresh()
    st["ladder"].update(stage="voll", since_n=0, review_n=0)
    st["active"] = 0
    add(st["shadows"][2], *[0.8] * 12)       # Variante C läuft im Hintergrund klar im Plus
    add(st["real"], *[-0.5] * 15)            # 15 neue Trades, alle verloren
    assert step(st) == "halb" and st["active"] == 2 and st["ladder"]["health"] == "ersatz"
    # schwächeln: Note fällt um mehr als 5 Punkte, bleibt aber im Plus -> eine Stufe runter
    st["ladder"].update(stage="voll", note=80)
    add(st["real"], *[0.15] * 15)
    assert step(st) == "halb" and st["ladder"]["health"] == "schwach", st["ladder"]
    # gesund: gleiche Note wie zuvor
    st["ladder"].update(stage="voll")
    add(st["real"], *[0.15] * 15)
    assert step(st) == "voll" and st["ladder"]["health"] == "gesund"
    return "Decay-Check: verliert -> eine Stufe runter + beste Variante übernimmt; Note −5 -> runter; sonst gesund"


def test_bench_and_return():
    st = fresh()
    add(st["real"], *[-0.4] * 15)            # auf Probe verloren, keine Variante im Plus -> Ersatzbank
    assert step(st) == "bank" and ladder.factor(st) == 0.0 and ladder.block_reason(st)
    add(st["shadows"][1], *[0.5, -0.2] * 7)  # 14 Schatten-Trades im Plus: noch nicht
    assert step(st) == "bank"
    add(st["shadows"][1], 0.3)
    assert step(st) == "probe" and st["active"] == 1 and ladder.factor(st) == 0.25
    return "Ersatzbank, wenn nichts im Plus ist; zurück auf Probe, sobald eine Variante 15 Trades im Plus hat"


def test_probe_swap_instead_of_bench():
    st = fresh()
    add(st["shadows"][1], *[0.6] * 12)
    add(st["real"], *[-0.4] * 15)
    assert step(st) == "probe" and st["active"] == 1
    return "Auf Probe mit besserer Variante: Variante wechselt, Bot bleibt auf Probe statt Ersatzbank"


def candles(rows, tf=60, t0=T0 - T0 % 3600):
    return [{"t": t0 + i * tf * 60, "o": o, "h": h, "l": l, "c": c, "v": 1.0} for i, (o, h, l, c) in enumerate(rows)]


def once(at, stop, target):
    def fn(c, p):
        return {"stop": stop, "target": target, "reason": "Test"} if c[-1]["t"] == at else None
    return fn


def test_floor_and_bench_block():
    bot = dict(BOTS["pump"], cooldown=0)
    sig = {"stop": 85.0, "target": 140.0, "reason": "Test"}
    acc = A.new_account(300.0)
    assert A.open_position(acc, bot, "POOL", sig, 100.0, T0, 1.0, 0.25)        # ¼ Risiko: unter 10 € -> kein Kauf
    acc = A.new_account(300.0)
    assert A.open_position(acc, bot, "POOL", sig, 100.0, T0, 1.0, 0.25, floor=True) is None
    p = acc["positions"]["POOL"]
    assert S.MIN_ORDER_EUR <= p["cost"] < S.MIN_ORDER_EUR * 1.01 and p["risk_eur"] <= 300.0 * bot["risk"], p
    tiny = A.new_account(20.0)                                                   # Mindestgröße wäre über dem vollen Risiko
    assert A.open_position(tiny, bot, "POOL", sig, 100.0, T0, 1.0, 0.25, floor=True)
    # Ersatzbank: Signal wird gezählt, aber nicht gekauft
    tb = dict(BOTS["trend"], cooldown=0)
    rows = [(100, 101, 99, 100)] * 3 + [(100, 100.5, 99.5, 100), (100, 104, 99.6, 103)]
    cs = candles(rows)
    acc, stats = A.new_account(1000.0), A.new_stats()
    A.process(acc, tb, "XBTEUR", cs, 1.0, {}, 0, start_from=0, fn=once(cs[3]["t"], 97.0, 104.0), stats=stats,
              block="Ersatzbank")
    assert stats["signals"] == 1 and stats["own"] == 1 and not acc["positions"] and not acc["pending"], stats
    return "Mindestgröße bei ¼ Risiko (nie über dem vollen Risiko); auf der Ersatzbank wird nichts gekauft"


def test_seq():
    acc = A.new_account(1000.0)
    bot = dict(BOTS["trend"], cooldown=0)
    sig = {"stop": 97.0, "target": 110.0, "reason": "Test"}
    for i in range(3):
        A.open_position(acc, bot, "XBTEUR", sig, 100.0, T0 + i, 1.0, 1.0)
        A.close_position(acc, bot, "XBTEUR", 101.0, T0 + i + 1, 1.0, "Test")
    assert [t["seq"] for t in acc["trades"]] == [1, 2, 3] and acc["n_closed"] == 3
    return "Jeder abgeschlossene Trade bekommt eine laufende Nummer"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print("✓", t())
    print(f"\n{len(tests)} Leiter-Tests bestanden.")
