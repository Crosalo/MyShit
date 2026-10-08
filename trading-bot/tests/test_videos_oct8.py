"""Kein Zukunftswissen: Werte bis Zeitpunkt T dürfen sich nicht ändern, wenn spätere Kerzen dazukommen."""
import numpy as np
import pandas as pd

from research.videos import Bars
from research.videos_oct8 import h1_fvg_book, m15_trend, sr_channels


def _bars(n, minutes, seed=3):
    rng = np.random.default_rng(seed)
    c = 100 + np.cumsum(rng.normal(0, 0.5, n))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) + rng.uniform(0, 0.4, n)
    l = np.minimum(o, c) - rng.uniform(0, 0.4, n)
    t = pd.date_range("2024-01-02 14:30", periods=n, freq=f"{minutes}min", tz="UTC")
    df = pd.DataFrame({"time": t, "open": o, "high": h, "low": l, "close": c})
    return Bars(df, np.full(n, 0.02), 0.0, "TEST")


def _head(b, n):
    df = pd.DataFrame({"time": b.t[:n], "open": b.o[:n], "high": b.h[:n], "low": b.l[:n], "close": b.c[:n]})
    return Bars(df, b.spread[:n], 0.0, b.name)


def test_m15_trend_is_causal():
    b = _bars(600, 15)
    full, cut = m15_trend(b), m15_trend(_head(b, 400))
    assert (full.iloc[:400].to_numpy() == cut.to_numpy()).all()


def test_h1_fvg_bias_is_causal():
    b = _bars(800, 60)
    _, full = h1_fvg_book(b)
    _, cut = h1_fvg_book(_head(b, 500))
    assert (full.iloc[:len(cut)].to_numpy() == cut.to_numpy()).all()


def test_sr_channels_ignore_future_bars():
    b = _bars(700, 1440)
    i = 450
    assert sr_channels(b.h, b.l, i) == sr_channels(b.h[:i + 1], b.l[:i + 1], i)
