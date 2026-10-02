"""Team: bündelt Analyst, Nachrichten-Analyst, Risiko-Manager und Konsens zu EINER Entscheidung
vor jedem Kauf des echten Kontos: gate() -> Risiko-Faktor (0 = nicht kaufen, max. 1,5).
Reihenfolge: Team-Pause -> Nachrichten -> Kollegen-Warnung -> Klumpenrisiko -> Marktlage -> größerer Trend -> Konsens.
Die Schatten-Varianten (Lernen) laufen ohne diese Regeln – so lässt sich später vergleichen, ob sie helfen.
"""
from .. import settings as S
from ..bots import BOTS, TEAMS
from ..markets import REGIME_NAMES, display
from ..trading import account as A
from . import analyst, news_analyst, risk

R = S.TEAM_RULES


def new_state():
    return {"teams": {}, "seen": {}}


class Team:
    def __init__(self, tstate, states, teams_map, pool, now, errors, news=None):
        self.ts, self.states, self.map, self.pool = tstate, states, teams_map, pool
        self.now, self.errors, self.news, self.regimes = now, errors, news, {}
        for tid in TEAMS:
            tstate["teams"].setdefault(tid, {"pause_until": 0, "guard_since": 0, "dd_since": 0, "log": [], "regimes": {}})
        tstate["seen"] = {k: v for k, v in tstate["seen"].items() if now - v < 6 * 3600}

    # --- Hilfen ---------------------------------------------------------------
    def team_ids(self):
        return list(TEAMS)

    def members(self, tid):
        return [b for b in BOTS if self.map.get(b) == tid]

    def real(self, b):
        return self.states[b]["real"]

    def invested(self, tid):
        mem = self.members(tid)
        inv = sum(p["qty"] * self.real(b)["marks"].get(pp, 0) for b in mem for pp, p in self.real(b)["positions"].items())
        return inv, sum(A.equity(self.real(b)) for b in mem)

    def log(self, tid, msg, key=None, every=2 * 3600):
        if key:
            if self.now - self.ts["seen"].get(key, 0) < every:
                return
            self.ts["seen"][key] = self.now
        t = self.ts["teams"][tid]
        t["log"] = (t["log"] + [[self.now, msg]])[-40:]

    def disp(self, bid, pair):
        if BOTS[bid].get("source") == "pumpfun":
            return self.states[bid].get("names", {}).get(pair, pair[:6] + "…")
        return display(pair)

    # --- einmal pro Lauf -------------------------------------------------------
    def analyse(self):
        self.regimes = analyst.market_regimes(self.errors)
        for tid in TEAMS:
            t = self.ts["teams"][tid]
            for src in sorted({BOTS[b]["regime_src"] for b in self.members(tid) if BOTS[b]["regime_src"]}):
                r = self.regimes.get(src)
                if r and t["regimes"].get(src) != r["label"]:
                    self.log(tid, f"Analyst: {REGIME_NAMES.get(src, src)} jetzt „{r['label']}“ – {r['detail']}")
                    t["regimes"][src] = r["label"]

    def guard(self):
        risk.guard(self)

    # --- Entscheidung vor jedem Kauf --------------------------------------------
    def gate(self, bid, pair, sig, t_entry):
        bot, tid = BOTS[bid], self.map[bid]
        name, disp = bot["name"], self.disp(bid, pair)

        def block(reason, key):
            self.log(tid, f"{name}: {disp} übersprungen – {reason}", key=key)
            return 0.0

        if self.now < self.ts["teams"][tid]["pause_until"]:
            return block("Team pausiert", f"p{bid}{pair}")
        m, why_news, nkey = news_analyst.factor(self.news, bot, pair, t_entry)
        if m <= 0:
            return block(why_news, f"n{bid}{pair}{nkey}")
        why = [why_news] if why_news else []
        msg = risk.colleague_stopped(self, bid, pair, t_entry) or risk.exposure_block(self, bid, pair)
        if msg:
            return block(msg, f"r{bid}{pair}")
        r = self.regimes.get(bot["regime_src"]) if bot["regime_src"] else None
        if r:
            f = bot["regime_rules"].get(r["label"], 1.0)
            calm_market = bot["team"] != "meme"   # Memecoins leben von Schwankung
            if r["vol_high"] and calm_market:
                f *= 0.75
            if f <= 0:
                return block(f"Marktlage „{r['label']}“ passt nicht zur Strategie", f"g{bid}{pair}")
            if f != 1:
                why.append(f"Markt {r['label']}{' + hohe Schwankung' if r['vol_high'] and calm_market else ''} x{f:g}")
            m *= f
        if analyst.htf_against(bot, pair, t_entry):
            m *= R["htf_against"]
            why.append(f"größerer Trend dagegen x{R['htf_against']:g}")
        for b in self.members(tid):
            p = self.real(b)["positions"].get(pair) if b != bid else None
            if p and self.real(b)["marks"].get(pair, 0) > p["entry"] * p["rate"]:
                m *= R["consensus_boost"]
                why.append(f"{BOTS[b]['name']} liegt hier im Plus x{R['consensus_boost']:g}")
                break
        m = min(m, R["max_factor"])
        if why:
            self.log(tid, f"{name}: Kauf {disp} mit Risiko x{m:.2f} ({', '.join(why)})", key=f"m{bid}{pair}{t_entry}")
        return m

    # --- Übersicht für die App ---------------------------------------------------
    def status(self):
        out = {}
        for tid, tname in TEAMS.items():
            mem, T = self.members(tid), self.ts["teams"][tid]
            inv, eq = self.invested(tid)
            net = sum(self.real(b)["net_in"] for b in mem)
            srcs = sorted({BOTS[b]["regime_src"] for b in mem if BOTS[b]["regime_src"]})
            out[tid] = {
                "name": tname, "members": mem, "equity": round(eq, 2), "net_in": round(net, 2),
                "pnl": round(eq - net, 2), "pnl_pct": round((eq / net - 1) * 100, 2) if net > 1 else 0.0,
                "regimes": [dict(self.regimes[s], src=REGIME_NAMES.get(s, s)) for s in srcs if s in self.regimes],
                "paused_until": T["pause_until"] if T["pause_until"] > self.now else 0,
                "stops": risk.stops_recent(self, tid), "stops_limit": R["sl_guard_count"],
                "exposure_pct": round(inv / eq * 100, 1) if eq > 0 else 0.0,
                "exposure_limit": round(R["max_team_exposure"] * 100),
                "log": list(reversed(T["log"][-15:])),
            }
        return out
