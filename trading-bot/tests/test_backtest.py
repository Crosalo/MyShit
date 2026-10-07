import copy

import pytest

from bot.backtest import load_spec, run_backtest
from bot.config import DEFAULTS
from bot.strategy import TrendPullback
from tests.helpers import append_bars, make_ohlc, uptrend_with_pullback


def _signal_then(bars):
    df = uptrend_with_pullback()
    strat = TrendPullback(DEFAULTS["strategy"])
    atr_ = strat.prepare(df)["atr"].iloc[-1]
    entry_open = df["close"].iloc[-1]
    return append_bars(df, bars(entry_open, atr_)), atr_


def test_sl_counts_first_when_bar_hits_both():
    df, atr_ = _signal_then(lambda o, a: [(o, o + 10 * a, o - 10 * a, o)] + [(o, o, o, o)] * 3)
    spec, _ = load_spec("EURUSD", None)
    res = run_backtest(df, spec, DEFAULTS, 10_000, spread=0.0)
    assert len(res.trades) == 1
    t = res.trades[0]
    assert t.exit_reason == "SL"
    assert t.r_multiple == pytest.approx(-1.0, abs=0.01)


def test_tp_hit_and_commission_charged():
    df, atr_ = _signal_then(lambda o, a: [(o, o + 4 * a, o - 0.1 * a, o + 3 * a)] + [(o, o, o, o)] * 3)
    spec, _ = load_spec("EURUSD", None)
    res = run_backtest(df, spec, DEFAULTS, 10_000, spread=0.0)
    t = res.trades[0]
    assert t.exit_reason == "TP"
    gross = (t.exit - t.entry) / spec.tick_size * spec.tick_value * t.lots
    assert t.pnl == pytest.approx(gross - DEFAULTS["risk"]["commission_per_lot"] * t.lots)
    assert res.final_equity == pytest.approx(10_000 + sum(x.pnl for x in res.trades))


def test_small_account_skips_trades():
    df, _ = _signal_then(lambda o, a: [(o, o + 4 * a, o, o)] * 3)
    spec, _ = load_spec("EURUSD", None)
    res = run_backtest(df, spec, DEFAULTS, 19, spread=0.00002)
    assert res.trades == [] and res.skipped == 1
    assert "Mindestlot" in res.skip_reason


def test_equity_bookkeeping_on_random_data():
    cfg = copy.deepcopy(DEFAULTS)
    df = make_ohlc(n=5000, drift=0.0, noise=0.0004, seed=11)
    spec, spread = load_spec("EURUSD", None)
    res = run_backtest(df, spec, cfg, 1000, spread=spread)
    assert res.final_equity == pytest.approx(1000 + sum(t.pnl for t in res.trades))
    assert all(t.exit_reason in {"SL", "TP", "Handelsende", "Datenende"} for t in res.trades)
    per_day = {}
    for t in res.trades:
        per_day[t.entry_time.date()] = per_day.get(t.entry_time.date(), 0) + 1
    assert max(per_day.values(), default=0) <= cfg["risk"]["max_trades_per_day"]
