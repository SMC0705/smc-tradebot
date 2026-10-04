"""Testlauf ohne Internet: python -m tests.simulate 40   (40 Läufe = 20 Stunden Bot-Zeit)
Schreibt in einen Temp-Ordner – das echte state/ und die App-Daten bleiben unberührt.
Prüft nach jedem Lauf Grundregeln (kein negatives Geld, Konten stimmen, Limits eingehalten)."""
import json
import math
import os
import sys
import tempfile

from bot import settings as S
from bot.markets import us_session

from . import fake_markets as F


def check(status, k):
    bots, pool = status["bots"], status["pool"]
    total = pool["unallocated"] + sum(b["equity"] for b in bots.values())
    assert abs(total - pool["equity"]) < 0.5, f"Lauf {k}: Sammelkonto stimmt nicht ({total} vs {pool['equity']})"
    from bot.bots import BOTS
    for bid, b in bots.items():
        assert b["cash"] >= -0.01, f"Lauf {k}: {bid} hat negatives Geld"
        assert math.isfinite(b["equity"]), f"Lauf {k}: {bid} Guthaben ungültig"
        assert len(b["positions"]) <= BOTS[bid]["max_pos"], f"Lauf {k}: {bid} zu viele Positionen"
        for o in b.get("orders", []):
            assert o["type"] in ("limit", "market"), f"Lauf {k}: {bid} unbekannte Order {o}"
        if BOTS[bid].get("session") == "us":   # Börsen-Bot: nach Börsenschluss nichts mehr offen
            sess = us_session(status["updated_at"])
            if not sess or status["updated_at"] >= sess[1] + 60:
                assert not b["positions"], f"Lauf {k}: {bid} hält nach Börsenschluss noch {b['positions']}"
    assert set(status["teams"]) and status["news"] is not None


def main(runs):
    tmp = tempfile.mkdtemp(prefix="tradebot-test-")
    S.STATE_DIR = os.path.join(tmp, "state")
    S.STATUS_FILE = os.path.join(tmp, "status.json")
    F.install()
    from bot import main as M
    for k in range(runs):
        F.set_run(k)
        M.run()
        with open(S.STATUS_FILE) as f:
            check(json.load(f), k)
    with open(S.STATUS_FILE) as f:
        st = json.load(f)
    print(f"\n✓ {runs} Läufe ohne Fehler. Testdaten: {S.STATUS_FILE}")
    print(f"{'Bot':<26}{'Team':<10}{'Guthaben':>10}{'Trades':>8}  aktive Variante")
    for bid, b in st["bots"].items():
        print(f"{b['name']:<26}{b['team']:<10}{b['equity']:>10.2f}{b['stats']['trades']:>8}  {b['learning']['active']}")
    n = st["news"]
    print(f"\nNachrichtenlage: {n['level_text']} | aktive Themen: {[t['label'] for t in n['themes'] if t['active']]}")
    for tid, t in st["teams"].items():
        print(f"\n[{t['name']}] " + " | ".join(m for _, m in t["log"][:4]))
    return st


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 40)
