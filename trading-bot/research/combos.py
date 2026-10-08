"""Kombinationen der 6 Basis-Strategien. VOR dem Test festgelegt, nicht nachträglich ausgewählt.

| Kombination       | Idee                                                                 |
|-------------------|----------------------------------------------------------------------|
| ALL6              | Portfolio: alle 6 Strategien gleichzeitig (Referenz)                 |
| ORB+TREND         | Eröffnungs-Ausbruch nur in Richtung des übergeordneten Trends        |
| SQUEEZE+TREND     | Volatilitäts-Ausbruch nur in Trendrichtung                           |
| ORB+COMPRESSED    | Eröffnungs-Ausbruch nur nach enger, ruhiger Vorphase                 |
| TWAP_MR+RANGE     | Rückkehr zum Durchschnitt nur, wenn kein Trend herrscht (ADX < 20)   |
| ASIA_MR+RANGE     | Asien-Überdehnung nur ohne Trend                                     |
| FIX_FADE+STRETCH  | Fix-Konter nur, wenn der Kurs weit vom Tagesdurchschnitt entfernt ist |
| VOTE2             | Einstieg, wenn >= 2 Strategien kurz hintereinander dieselbe Richtung |
| REGIME            | Trend-Strategien bei Trend (ADX >= 25), Rückkehr-Strategien bei Seitwärts (ADX < 20) |
"""
import numpy as np
import pandas as pd

from bot.indicators import adx, ema
from .engine import Signals
from .strategies import STRATEGIES, TF_PARAMS, Context, _hhmm

ADX_RANGE, ADX_TREND = 20.0, 25.0


def _filtered(sig: Signals, long_ok: np.ndarray, short_ok: np.ndarray) -> Signals:
    return Signals(sig.long & long_ok, sig.short & short_ok, sig.sl_dist, sig.tp_dist, sig.max_hold)


def features(ctx: Context, tf: int) -> dict:
    """Marktzustand je Kerze, nur aus Vergangenheitsdaten."""
    mp = {"ema_fast": 60, "ema_slow": 240, "slope_bars": 30, **TF_PARAMS[tf].get("MOMO", {})}
    close = pd.Series(ctx.c)
    ef, es = ema(close, mp["ema_fast"]).to_numpy(), ema(close, mp["ema_slow"]).to_numpy()
    slope = es - np.roll(es, mp["slope_bars"])
    slope[: mp["slope_bars"]] = 0
    adx14 = adx(ctx.df, 14).to_numpy()
    sd20, sma20 = close.rolling(20).std(), close.rolling(20).mean()
    bw = 4 * sd20 / sma20
    lookback = TF_PARAMS[tf].get("SQUEEZE", {}).get("squeeze_lookback", 240)
    compressed = (bw.shift(1) < bw.rolling(lookback).median().shift(1) * 0.8).to_numpy()

    # Abstand zum Tagesdurchschnittspreis (Session ab London 08:00 bzw. Index-Eröffnung)
    tz, hhmm = ctx.inst.sessions[0] if ctx.inst.asset == "index" else ("Europe/London", "08:00")
    day, mins = ctx.local(tz)
    in_sess = (mins >= _hhmm(hhmm)) & (mins < _hhmm(hhmm) + 480)
    grp = np.where(in_sess, day, -1)
    typical = pd.Series(np.where(in_sess, (ctx.h + ctx.l + ctx.c) / 3, 0.0))
    twap = (typical.groupby(grp).cumsum() / (typical.groupby(grp).cumcount() + 1)).to_numpy()
    dev = np.where(in_sess, (ctx.c - twap) / ctx.atr14, 0.0)
    return {
        "trend_up": (ef > es) & (ctx.c > es) & (slope > 0),
        "trend_down": (ef < es) & (ctx.c < es) & (slope < 0),
        "ranging": adx14 < ADX_RANGE,
        "trending": adx14 >= ADX_TREND,
        "compressed": compressed,
        "dev": np.nan_to_num(dev),
    }


def _vote2(ctx: Context, base: dict, tf: int) -> Signals:
    window = max(1, 60 // tf)
    longs = np.vstack([pd.Series(s.long).rolling(window, min_periods=1).max().to_numpy() for s in base.values()])
    shorts = np.vstack([pd.Series(s.short).rolling(window, min_periods=1).max().to_numpy() for s in base.values()])
    n_long, n_short = longs.sum(axis=0), shorts.sum(axis=0)
    vote_long = (n_long >= 2) & (n_short == 0)
    vote_short = (n_short >= 2) & (n_long == 0)
    trig_long = vote_long & ~np.roll(vote_long, 1)
    trig_short = vote_short & ~np.roll(vote_short, 1)
    trig_long[0] = trig_short[0] = False
    return Signals(trig_long, trig_short, 1.5 * ctx.atr14, 3.0 * ctx.atr14, max(4, 240 // tf))


def build(ctx: Context, tf: int) -> dict[str, list[Signals]]:
    """{Kombination: [Signals, ...]}. Mehrere Signals = Portfolio, Trades werden zusammengelegt."""
    base = {name: fn(ctx, **TF_PARAMS[tf].get(name, {})) for name, fn in STRATEGIES.items()}
    f = features(ctx, tf)
    up, down, rng, trd = f["trend_up"], f["trend_down"], f["ranging"], f["trending"]
    return {
        "ALL6": list(base.values()),
        "ORB+TREND": [_filtered(base["ORB"], up, down)],
        "SQUEEZE+TREND": [_filtered(base["SQUEEZE"], up, down)],
        "ORB+COMPRESSED": [_filtered(base["ORB"], f["compressed"], f["compressed"])],
        "TWAP_MR+RANGE": [_filtered(base["TWAP_MR"], rng, rng)],
        "ASIA_MR+RANGE": [_filtered(base["ASIA_MR"], rng, rng)],
        "FIX_FADE+STRETCH": [_filtered(base["FIX_FADE"], f["dev"] < -1.0, f["dev"] > 1.0)],
        "VOTE2": [_vote2(ctx, base, tf)],
        "REGIME": [_filtered(base[n], trd, trd) for n in ("ORB", "MOMO", "SQUEEZE")]
                  + [_filtered(base[n], rng, rng) for n in ("TWAP_MR", "ASIA_MR", "FIX_FADE")],
    }
