import numpy as np
import pandas as pd

from bot.config import DEFAULTS
from bot.indicators import adx, atr, ema
from bot.strategy import TrendPullback
from tests.helpers import append_bars, make_ohlc, uptrend_with_pullback


def test_ema_matches_recursive_definition():
    s = pd.Series([1.0, 2.0, 3.0, 4.0])
    alpha = 2 / (3 + 1)
    expected = [1.0]
    for x in s[1:]:
        expected.append(alpha * x + (1 - alpha) * expected[-1])
    assert np.allclose(ema(s, 3), expected)


def test_atr_constant_range():
    df = pd.DataFrame({"open": [1.0] * 50, "high": [1.5] * 50, "low": [0.5] * 50, "close": [1.0] * 50})
    assert np.isclose(atr(df, 14).iloc[-1], 1.0)


def test_adx_high_in_trend_low_in_noise():
    trend = make_ohlc(n=400, drift=0.0003, noise=0.0001)
    noise = make_ohlc(n=400, drift=0.0, noise=0.0004, seed=7)
    a_trend, a_noise = adx(trend, 14).iloc[-1], adx(noise, 14).iloc[-1]
    assert 0 <= a_noise <= 100 and 0 <= a_trend <= 100
    assert a_trend > 40 > a_noise


def test_long_signal_on_pullback_in_uptrend():
    strat = TrendPullback(DEFAULTS["strategy"])
    d = strat.prepare(uptrend_with_pullback())
    sig = strat.signal_at(d, len(d) - 1)
    assert sig is not None and sig.side == "buy"
    assert np.isclose(sig.tp_distance, sig.sl_distance * DEFAULTS["strategy"]["rr"])
    assert np.isclose(sig.sl_distance, DEFAULTS["strategy"]["sl_atr"] * d["atr"].iloc[-1])


def test_no_signal_before_warmup_and_no_lookahead():
    strat = TrendPullback(DEFAULTS["strategy"])
    df = uptrend_with_pullback()
    i = len(df) - 1
    d_now = strat.prepare(df)
    assert not d_now["long_sig"].iloc[: strat.min_bars].any()
    # Spätere Kerzen dürfen das Signal auf Kerze i nicht nachträglich ändern
    later = append_bars(df, [(1.2, 1.3, 1.0, 1.05)] * 5)
    d_later = strat.prepare(later)
    cols = ["long_sig", "short_sig", "atr", "adx", "ema_f"]
    assert d_now[cols].iloc[: i + 1].equals(d_later[cols].iloc[: i + 1])
    assert d_now["long_sig"].iloc[i]
