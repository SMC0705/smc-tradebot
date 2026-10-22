"""Sammelkonto: Ein gemeinsamer Topf, aus dem die Bots ihr Kapital bekommen.
Die Aufteilung steht in config/allocation.json (wird über die App geändert).
Umgebucht wird nur freies Geld. Steckt Geld in offenen Trades, wird der Rest
bei den nächsten Läufen nachgeholt (bis zu 24 Stunden lang).
"""
import json
import os

from .. import settings as S
from ..bots import BOTS, TEAMS
from . import account as E


def load_weights():
    w = {}
    if os.path.exists(S.ALLOC_FILE):
        try:
            with open(S.ALLOC_FILE) as f:
                w = json.load(f).get("weights", {})
        except Exception:
            w = {}
    # Bots, die (noch) nicht in der Datei stehen, bekommen ihren Standard-Anteil aus bots.py
    w = {b: max(0.0, float(w.get(b, BOTS[b].get("weight", 0)))) for b in BOTS}
    tot = sum(w.values())
    return {b: (v / tot * 100 if tot else 0.0) for b, v in w.items()}


def load_teams():
    """Team-Zuordnung der Bots (in der App änderbar), sonst Standard aus config.py."""
    t = {}
    if os.path.exists(S.ALLOC_FILE):
        try:
            with open(S.ALLOC_FILE) as f:
                t = json.load(f).get("teams", {}) or {}
        except Exception:
            t = {}
    return {b: (t.get(b) if t.get(b) in TEAMS else BOTS[b]["team"]) for b in BOTS}


def new_pool():
    return {"unallocated": S.POOL_START_EUR, "start": S.POOL_START_EUR, "applied": None,
            "pending_runs": 0, "curve": []}


def rebalance(pool, accounts, weights):
    changed = pool["applied"] != weights
    if changed:
        pool["applied"] = weights
        pool["pending_runs"] = 48
    idle_cash = any(weights[b] == 0 and a["cash"] > 1 for b, a in accounts.items())
    if pool["pending_runs"] <= 0 and pool["unallocated"] < 1 and not idle_cash:
        return []
    eqs = {b: E.equity(a) for b, a in accounts.items()}
    total = sum(eqs.values()) + pool["unallocated"]
    moves = []
    # 1) Überschuss (nur freies Geld) zurück in den Topf
    for b, a in accounts.items():
        target = total * weights[b] / 100
        excess = min(a["cash"], eqs[b] - target)
        if excess > 1:
            a["cash"] -= excess
            a["net_in"] -= excess
            pool["unallocated"] += excess
            moves.append((b, -excess))
    # 2) Topf an Bots mit zu wenig Kapital verteilen
    for b, a in accounts.items():
        target = total * weights[b] / 100
        need = min(pool["unallocated"], target - E.equity(a))
        if need > 1:
            a["cash"] += need
            a["net_in"] += need
            pool["unallocated"] -= need
            moves.append((b, need))
    gap = max(abs(total * weights[b] / 100 - E.equity(a)) for b, a in accounts.items())
    pool["pending_runs"] = 0 if gap < max(5.0, total * 0.005) else pool["pending_runs"] - 1
    return moves
