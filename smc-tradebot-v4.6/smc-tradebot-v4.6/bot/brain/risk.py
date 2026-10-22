"""Risiko-Manager eines Teams (Ideen von freqtrade "Protections" und ai-hedge-fund):
- Pause nach Verlustserie (StoplossGuard) und nach großem Tagesverlust (MaxDrawdown)
- Kollegen-Warnung: wurde ein Bot bei einem Wert ausgestoppt, meidet das Team ihn eine Weile
- Klumpenrisiko: begrenzt Geld im selben Wert und den investierten Anteil des Teams
"""
from .. import settings as S
from ..bots import BOTS
from ..trading import account as A

R = S.TEAM_RULES


def _value_at(curve, t):
    v = 0.0
    for ts, pnl in curve:
        if ts > t:
            break
        v = pnl
    return v


def guard(team):
    """Einmal pro Lauf: Team-Pausen setzen."""
    for tid in team.team_ids():
        t, mem = team.ts["teams"][tid], team.members(tid)
        if not mem:
            continue
        stops = [tr for b in mem for tr in team.real(b)["trades"]
                 if tr.get("result") == "Stop-Loss" and tr["closed_t"] > t["guard_since"]
                 and team.now - tr["closed_t"] <= R["sl_guard_h"] * 3600]
        if len(stops) >= R["sl_guard_count"] and t["pause_until"] < team.now:
            t["pause_until"] = team.now + R["sl_guard_pause_h"] * 3600
            t["guard_since"] = team.now
            team.log(tid, f"Risiko-Manager: {len(stops)} Stop-Losses in {R['sl_guard_h']} Std. – "
                          f"Team macht {R['sl_guard_pause_h']} Std. Pause (offene Trades laufen weiter)")
        cap = sum(team.real(b)["net_in"] for b in mem)
        pnl_now = sum(A.equity(team.real(b)) - team.real(b)["net_in"] for b in mem)
        pnl_24 = sum(_value_at(team.real(b)["equity_curve"], team.now - 86400) for b in mem)
        if cap > 100 and pnl_now - pnl_24 < -R["dd_limit"] * cap and team.now - t["dd_since"] > 86400:
            t["pause_until"] = max(t["pause_until"], team.now + R["dd_pause_h"] * 3600)
            t["dd_since"] = team.now
            team.log(tid, f"Risiko-Manager: Team hat in 24 Std. {abs(pnl_now - pnl_24) / cap * 100:.1f} % verloren – "
                          f"{R['dd_pause_h']} Std. Pause")


def stops_recent(team, tid):
    T = team.ts["teams"][tid]
    return sum(1 for b in team.members(tid) for tr in team.real(b)["trades"]
               if tr.get("result") == "Stop-Loss" and tr["closed_t"] > T["guard_since"]
               and team.now - tr["closed_t"] <= R["sl_guard_h"] * 3600)


def colleague_stopped(team, bid, pair, t_entry):
    """Text, falls ein Team-Kollege bei diesem Wert gerade ausgestoppt wurde, sonst None."""
    for b in team.members(team.map[bid]):
        if b == bid:
            continue
        for tr in reversed(team.real(b)["trades"][-20:]):
            if tr["pair"] == pair and tr.get("result") == "Stop-Loss" \
                    and 0 <= t_entry - tr["closed_t"] <= R["pair_warning_h"] * 3600:
                return f"{BOTS[b]['name']} wurde dort gerade ausgestoppt"
    return None


def exposure_block(team, bid, pair):
    """Text, falls zu viel Geld im selben Wert oder das Team schon voll investiert ist, sonst None."""
    pool_eq = team.pool["unallocated"] + sum(A.equity(s["real"]) for s in team.states.values())
    pair_val = sum(s["real"]["positions"][pair]["qty"] * s["real"]["marks"].get(pair, 0)
                   for s in team.states.values() if pair in s["real"]["positions"])
    if pool_eq > 0 and pair_val >= R["max_pair_exposure"] * pool_eq:
        return f"schon {pair_val / pool_eq * 100:.0f} % des Kontos darin (Klumpenrisiko)"
    inv, eq = team.invested(team.map[bid])
    if eq > 0 and inv >= R["max_team_exposure"] * eq:
        return f"Team ist zu {inv / eq * 100:.0f} % investiert"
    return None
