"""EINSTIEG: ein Durchlauf aller Bots (GitHub Actions startet ihn alle 30 Minuten: python -m bot.main).
Diese Datei enthält nur den Ablauf – die Logik steckt in den Ordnern (siehe ARCHITEKTUR.md).

Ablauf:
  1. Zustand laden (Konten, Sammelkonto, Teams)
  2. Daten holen: Wechselkurse, Nachrichten
  3. Gehirn: Nachrichtenlage bewerten, Marktlage (Analyst), Team-Pausen (Risiko-Manager)
  4. Jeden Bot laufen lassen (Kerzen nachspielen, kaufen/verkaufen)
  5. Sammelkonto umverteilen, Zustand speichern, Übersicht für die App schreiben
"""
import sys
import time

from . import report, settings as S, storage
from .bots import BOTS
from .brain import news_analyst, portfolio
from .brain.team import Team, new_state as new_team_state
from .data import kraken, news
from .trading import account as A
from .trading import pool as P
from .trading import runner


def run():
    if S.MODE != "paper":
        sys.exit("Echtgeld-Modus ist noch nicht freigeschaltet. Erst Demo auswerten!")
    now, errors = int(time.time()), []

    # 1) Zustand
    weights, teams_map = P.load_weights(), P.load_teams()
    pool = storage.read("pool") or P.new_pool()
    states = {b: runner.prepare(storage.read(b) or runner.new_state(bot), bot) for b, bot in BOTS.items()}
    nstate = storage.read("news") or {}

    # 2) Daten
    rates = kraken.eur_rates(errors)
    situation = news_analyst.assess(news.collect(errors), now)
    news_analyst.track(nstate, situation, now)

    # 3) Gehirn
    team = Team(storage.read("team") or new_team_state(), states, teams_map, pool, now, errors, situation)
    team.analyse()
    team.guard()

    # 4) Bots
    scores, unavailable = {}, {}
    for b, bot in BOTS.items():
        unavailable[b] = []
        gate = (lambda bid: (lambda pair, sig, t: team.gate(bid, pair, sig, t)))(b)
        scores[b] = runner.run(b, bot, states[b], rates, weights[b] > 0, errors, unavailable[b], gate)

    # 5) Sammelkonto, Speichern, Übersicht
    for b, amount in P.rebalance(pool, {b: s["real"] for b, s in states.items()}, weights):
        print(f"Umbuchung {b}: {amount:+.2f} EUR")
    total = pool["unallocated"]
    for b, s in states.items():
        eq = A.update_risk(s["real"])
        total += eq
        s["real"]["equity_curve"] = (s["real"]["equity_curve"] + [[now, round(eq - s["real"]["net_in"], 2)]])[-3000:]
        for sh in s["shadows"]:
            sh["equity_curve"] = []
        storage.write(b, s)
    pool["curve"] = (pool["curve"] + [[now, round(total, 2)]])[-3000:]
    storage.write("pool", pool)
    storage.write("team", team.ts)
    storage.write("news", nstate)

    storage.write_status(report.build(
        now, errors, pool, total, weights, portfolio.suggestion(states, weights), team.status(),
        {b: report.bot_status(BOTS[b], states[b], weights[b], teams_map[b], scores[b], unavailable[b]) for b in BOTS},
        report.news_status(situation, nstate)))
    print(f"Sammelkonto: {total:.2f} EUR | Nachrichtenlage: {situation['level_text'] if situation else '–'} | "
          f"Hinweise: {len(errors)}")


if __name__ == "__main__":
    run()
