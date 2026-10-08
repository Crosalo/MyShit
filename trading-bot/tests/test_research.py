import numpy as np
import pandas as pd
import pytest

from research.engine import Signals, force_exit_mask, simulate, stats
from research.instruments import BY_NAME
from research.run import evaluate
from research.strategies import STRATEGIES, Context
from tests.helpers import make_ohlc


def flat_bars(n, price=1.0):
    o = np.full(n, price)
    return o.copy(), o.copy(), o.copy(), o.copy()


def one_signal(n, at=0, long=True, sl=0.01, tp=0.02, hold=10):
    lg, sh = np.zeros(n, bool), np.zeros(n, bool)
    (lg if long else sh)[at] = True
    return Signals(lg, sh, np.full(n, sl), np.full(n, tp), hold)


def test_long_tp_with_spread_and_commission():
    o, h, l, c = flat_bars(20)
    h[3] = 1.05
    spread = np.full(20, 0.001)
    trades, _ = simulate(o, h, l, c, spread, np.zeros(20, bool), one_signal(20), 0.0005, min_cost_ratio=1)
    t = trades.iloc[0]
    assert t.reason == "TP" and t.entry == pytest.approx(1.001)
    assert t.r == pytest.approx((0.02 - 0.0005) / 0.01)


def test_sl_wins_when_both_hit_same_bar():
    o, h, l, c = flat_bars(20)
    h[3], l[3] = 1.05, 0.95
    trades, _ = simulate(o, h, l, c, np.zeros(20), np.zeros(20, bool), one_signal(20), 0.0, min_cost_ratio=1)
    assert trades.iloc[0].reason == "SL" and trades.iloc[0].r == pytest.approx(-1)


def test_gap_through_stop_fills_worse():
    o, h, l, c = flat_bars(20)
    o[4], h[4], l[4], c[4] = 0.97, 0.97, 0.97, 0.97
    trades, _ = simulate(o, h, l, c, np.zeros(20), np.zeros(20, bool), one_signal(20), 0.0, min_cost_ratio=1)
    assert trades.iloc[0].r == pytest.approx(-3)


def test_short_exit_pays_spread():
    o, h, l, c = flat_bars(20)
    spread = np.full(20, 0.002)
    trades, _ = simulate(o, h, l, c, spread, np.zeros(20, bool), one_signal(20, long=False, hold=5), 0.0,
                         min_cost_ratio=1)
    t = trades.iloc[0]
    assert t.reason == "Zeit" and t.r == pytest.approx(-0.2)


def test_forced_exit_and_cost_filter():
    o, h, l, c = flat_bars(20)
    fx = np.zeros(20, bool)
    fx[5] = True
    trades, _ = simulate(o, h, l, c, np.zeros(20), fx, one_signal(20, hold=15), 0.0, min_cost_ratio=1)
    assert trades.iloc[0].reason == "Zwang" and trades.iloc[0].exit_bar == 5
    trades, skipped = simulate(o, h, l, c, np.full(20, 0.005), fx, one_signal(20), 0.0, min_cost_ratio=5)
    assert len(trades) == 0 and skipped == 1


def test_one_position_at_a_time():
    n = 30
    o, h, l, c = flat_bars(n)
    lg = np.zeros(n, bool)
    lg[[0, 2, 4, 20]] = True
    sig = Signals(lg, np.zeros(n, bool), np.full(n, 0.01), np.full(n, 0.02), 10)
    trades, _ = simulate(o, h, l, c, np.zeros(n), np.zeros(n, bool), sig, 0.0, min_cost_ratio=1)
    assert list(trades.signal) == [0, 20]


def test_force_exit_mask_rollover_and_weekend():
    t = pd.Series(pd.to_datetime(["2026-10-07 20:54", "2026-10-07 20:55", "2026-10-07 22:10",
                                  "2026-10-09 20:30", "2026-10-11 22:15"], utc=True))
    assert list(force_exit_mask(t)) == [False, True, False, True, False]


def test_stats_basic():
    s = stats(np.array([1.0, -1.0, 2.0, -1.0]), 1)
    assert s["trades"] == 4 and s["avg_r"] == 0.25 and s["pf"] == 1.5 and s["max_dd_r"] == 1.0


def _m1(n=6000, seed=5):
    return make_ohlc(n=n, start=1.10, noise=0.00008, seed=seed, freq="1min", t0="2026-03-02 00:00")


@pytest.mark.parametrize("name", list(STRATEGIES))
def test_strategies_have_no_lookahead(name):
    df = _m1()
    inst = BY_NAME["EURUSD"]
    cut = 4500
    full = STRATEGIES[name](Context(df, inst))
    part = STRATEGIES[name](Context(df.iloc[:cut].reset_index(drop=True), inst))
    for arr in ("long", "short"):
        assert np.array_equal(getattr(full, arr)[:cut], getattr(part, arr)), arr
    both = part.long | part.short
    assert np.allclose(full.sl_dist[:cut][both], part.sl_dist[both])


def test_evaluate_smoke():
    df = _m1(n=20000)
    inst = BY_NAME["EURUSD"]
    spread = np.full(len(df), 0.00002)
    split = df["time"].iloc[13000]
    rows, trades = evaluate(inst, df, spread, "test", split, 19.0)
    assert {r["strategy"] for r in rows} == set(STRATEGIES)
    for t in trades:
        assert (t["exit_bar"] >= t["entry_bar"]).all() and np.isfinite(t["r"]).all()


def test_resample_m15_ohlc():
    from research.timeframes import resample
    df = _m1(n=60)
    r = resample(df, 15)
    assert len(r) == 4
    first = df.iloc[:15]
    assert r.iloc[0].open == first.open.iloc[0] and r.iloc[0].close == first.close.iloc[-1]
    assert r.iloc[0].high == first.high.max() and r.iloc[0].low == first.low.min()


def test_to_m1_enters_at_next_tf_bar_open():
    from research.timeframes import resample, to_m1
    df = _m1(n=120)
    bars = resample(df, 15)
    n = len(bars)
    lg = np.zeros(n, bool)
    lg[2] = True  # Signal auf M15-Kerze 00:30-00:45
    sig = Signals(lg, np.zeros(n, bool), np.full(n, 0.001), np.full(n, 0.002), 4)
    m1sig = to_m1(sig, bars["time"], df["time"], 15)
    s = int(np.flatnonzero(m1sig.long)[0])
    assert df["time"].iloc[s + 1] == bars["time"].iloc[3]  # Einstieg = Eröffnung der nächsten M15-Kerze
    assert m1sig.max_hold == 60 and m1sig.sl_dist[s] == 0.001


@pytest.mark.parametrize("tf", [15, 60])
@pytest.mark.parametrize("name", list(STRATEGIES))
def test_tf_strategies_have_no_lookahead(name, tf):
    from research.strategies import TF_PARAMS
    from research.timeframes import resample
    bars = resample(_m1(n=60000, seed=9), tf)
    inst = BY_NAME["EURUSD"]
    cut = int(len(bars) * 0.7)
    params = TF_PARAMS[tf][name]
    full = STRATEGIES[name](Context(bars, inst), **params)
    part = STRATEGIES[name](Context(bars.iloc[:cut].reset_index(drop=True), inst), **params)
    for arr in ("long", "short"):
        assert np.array_equal(getattr(full, arr)[:cut], getattr(part, arr)), arr


def test_evaluate_tf15_with_validation():
    df = _m1(n=40000)
    old = _m1(n=30000, seed=8)
    inst = BY_NAME["EURUSD"]
    spread = np.full(len(df), 0.00002)
    rows, trades = evaluate(inst, df, spread, "test", df["time"].iloc[26000], 19.0, tf=15,
                            val=(old, np.full(len(old), 0.00002)))
    assert all("val_trades" in r and r["tf"] == 15 for r in rows)
    for t in trades:
        assert set(t["part"]) <= {"is", "oos", "val"}


@pytest.mark.parametrize("tf", [1, 15, 60])
def test_orb_trades_on_every_timeframe(tf):
    from research.strategies import TF_PARAMS
    from research.timeframes import resample
    bars = resample(make_ohlc(n=20000, start=1.10, noise=0.0002, seed=4, freq="1min",
                              t0="2026-03-02 00:00"), tf)
    ctx = Context(bars, BY_NAME["EURUSD"])
    assert ctx.tf_min == tf
    sig = STRATEGIES["ORB"](ctx, **TF_PARAMS[tf].get("ORB", {}))
    assert (sig.long | sig.short).sum() >= 5
