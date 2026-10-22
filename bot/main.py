"""EINSTIEG: ein Durchlauf aller Bots (GitHub Actions startet ihn alle 30 Minuten: python -m bot.main).
Diese Datei enthält nur den Ablauf – die Logik steckt in den Ordnern (siehe ARCHITEKTUR.md).

Ablauf:
  1. Zustand laden (Konten, Sammelkonto, Teams)
  2. Daten holen: Wechselkurse, Nachrichten
  3. Gehirn: Nachrichtenlage bewerten, Marktlage (Analyst), Team-Pausen (Risiko-Manager)
  4. Jeden Bot laufen lassen (Kerzen nachspielen, kaufen/verkaufen), danach Inkubations-Leiter + Decay-Check
  5. Sammelkonto umverteilen, Zustand speichern, Übersicht für die App schreiben
"""
import sys
import time

from . import report, settings as S, storage
from .bots import BOTS
from .brain import ladder, news_analyst, portfolio, ranking
from .brain.team import Team, new_state as new_team_state
from .data import kraken, news, revolutx
from .trading import account as A
from .trading import focus
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
    if S.CRYPTO_VENUE == "revolutx":
        revolutx.load(errors)          # Geld/Brief aller Coins bei Revolut X (ein Abruf)
    situation = news_analyst.assess(news.collect(errors, nstate.setdefault("cache", {})), now)
    news_analyst.track(nstate, situation, now)

    # 3) Gehirn
    team = Team(storage.read("team") or new_team_state(), states, teams_map, pool, now, errors, situation)
    team.analyse()
    team.guard()

    # 4) Bots
    scores, unavailable, skipped, cands = {}, {}, [], []
    for b, bot in BOTS.items():
        unavailable[b] = []
        if bot.get("source") == "focus":
            continue                                      # kommt zum Schluss: braucht die Signale aller Bots
        if time.time() - now > S.RUN_BUDGET_MIN * 60:   # Zeitlimit: Rest im nächsten Lauf
            skipped.append(bot["name"])
            scores[b] = runner.scores_only(bot, states[b])
            continue
        scores[b] = runner.run(b, bot, states[b], rates, weights[b] > 0, errors, unavailable[b], team.gate_for(b),
                               candidates=cands)
    if skipped:
        errors.append(f"Zeitlimit erreicht – im nächsten Lauf dran: {', '.join(skipped)}")
    # 4b) Fokus-Bot: alle frischen Signale bewerten (Rangliste) und nur das beste handeln
    ranked = ranking.rank(cands, team, states, now)
    for b, bot in BOTS.items():
        if bot.get("source") == "focus":
            scores[b] = focus.run(bot, states[b], ranked, rates, weights[b] > 0, now)
    markets = ranking.market_map(ranked)
    # 4c) Inkubations-Leiter + Decay-Check: Aufstieg nur durch Trades, Abstieg bei schwachen Ergebnissen
    for b, bot in BOTS.items():
        ladder.update(states[b], runner.labels(bot))

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
        report.news_status(situation, nstate), markets, report.council_status(team.ts, states)))
    print(f"Sammelkonto: {total:.2f} EUR | Nachrichtenlage: {situation['level_text'] if situation else '–'} | "
          f"Hinweise: {len(errors)}")


if __name__ == "__main__":
    run()
