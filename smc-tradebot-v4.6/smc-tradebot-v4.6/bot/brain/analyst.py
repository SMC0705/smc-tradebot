"""Analyst: Marktlage (Aufwärts / Seitwärts / Abwärts) aus Tageskerzen und Bär-Check im größeren
Zeitrahmen. Liefert nur Einschätzungen – was daraus folgt, entscheidet brain/team.py."""
from ..bots import BOTS
from ..data import kraken
from ..markets import REGIME_NAMES
from ..strategies.indicators import adx, atr, ema


def regime(c):
    """Marktlage aus Tageskerzen: Lage zur 50-Tage-Linie, deren Richtung, Trendstärke (ADX), Schwankung."""
    cl = [x["c"] for x in c]
    if len(cl) < 70:
        return None
    e50 = ema(cl, 50)
    slope = e50[-1] / e50[-11] - 1
    strength = adx(c[-150:])
    a = atr(c)
    atrp = [a[i] / cl[i] for i in range(len(cl))][-120:]
    vol_high = atrp[-1] > sorted(atrp)[int(len(atrp) * 0.8)]
    above = cl[-1] > e50[-1]
    if above and slope > 0:
        label = "Aufwärts"
    elif not above and slope < 0:
        label = "Abwärts"
    else:
        label = "Seitwärts"
    detail = (f"Kurs {'über' if above else 'unter'} der 50-Tage-Linie, Linie {'steigt' if slope > 0 else 'fällt'}, "
              f"Trendstärke {strength:.0f}{' (klarer Trend)' if strength >= 25 else ' (schwach)' if strength < 20 else ''}"
              f"{', hohe Schwankung' if vol_high else ''}")
    return {"label": label, "adx": round(strength, 1), "vol_high": vol_high, "detail": detail}


def market_regimes(errors):
    """Marktlage für jede Quelle, die ein Bot nutzt (Bitcoin, Solana, S&P 500)."""
    out = {}
    for src in sorted({b["regime_src"] for b in BOTS.values() if b["regime_src"]}):
        try:
            closed, _ = kraken.get_candles(src, 1440, "tokenized_asset" if src.endswith("xUSD") else None)
            r = regime(closed)
            if r:
                out[src] = r
        except Exception as e:
            errors.append(f"Analyst {REGIME_NAMES.get(src, src)}: {e}")
    return out


def htf_against(bot, pair, t_entry):
    """Bär-Check: Liegt der Wert im größeren Zeitrahmen (4 Std. bzw. 1 Tag) unter seiner 50er-Linie?
    Es zählen nur Kerzen, die zum Kaufzeitpunkt schon abgeschlossen waren."""
    if bot.get("source") == "pumpfun" or bot["tf"] > 240:
        return False
    htf = 240 if bot["tf"] <= 60 else 1440
    try:
        closed, _ = kraken.get_candles(pair, htf, bot["aclass"])
    except Exception:
        return False
    cl = [x["c"] for x in closed if x["t"] + htf * 60 <= t_entry]
    if len(cl) < 60:
        return False
    return cl[-1] < ema(cl, 50)[-1]
