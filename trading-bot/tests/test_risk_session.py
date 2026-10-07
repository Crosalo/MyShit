from datetime import datetime, timezone

import pytest

from bot.config import DEFAULTS
from bot.risk import DailyGuard, SymbolSpec, position_size
from bot.session import in_trade_window, must_be_flat

EURUSD = SymbolSpec("EURUSD", 0.00001, 5, 0.00001, 1.0, 0.01, 100.0, 0.01, 0)


def test_position_size_rounds_down():
    # 1 % von 1000 = 10; 20 Pips = 200 Ticks * 1.0 = 200/Lot + 4.5 Kommission -> 0.0488 -> 0.04
    size = position_size(1000, 1.0, 0.0020, EURUSD, commission_per_lot=4.5)
    assert size.lots == 0.04
    assert size.risk_money == pytest.approx(0.04 * 204.5)
    assert size.risk_pct <= 1.0


def test_position_size_refuses_below_min_lot_for_tiny_account():
    size = position_size(19, 1.0, 0.0020, EURUSD, commission_per_lot=4.5)
    assert size.lots == 0
    assert "Mindestlot" in size.reason and "10.8%" in size.reason


def test_position_size_caps_at_volume_max():
    spec = SymbolSpec("X", 0.00001, 5, 0.00001, 1.0, 0.01, 0.5, 0.01, 0)
    assert position_size(1_000_000, 1.0, 0.0020, spec).lots == 0.5


def test_daily_guard_loss_and_rollover(tmp_path):
    g = DailyGuard(3.0, 2, tmp_path / "daily.json")
    assert g.roll_day("2026-10-07", 1000)
    assert not g.loss_breached(975)
    assert g.loss_breached(970)
    g.record_trade()
    g.record_trade()
    assert g.can_open() == (False, "max. 2 Trades/Tag erreicht")
    g.halt("Limit")

    reloaded = DailyGuard(3.0, 2, tmp_path / "daily.json")
    assert not reloaded.roll_day("2026-10-07", 900)  # gleicher Tag: Start-Equity bleibt
    assert reloaded.start_equity == 1000 and reloaded.halted
    assert reloaded.roll_day("2026-10-08", 970)
    assert reloaded.can_open() == (True, "")


def test_manual_stop_survives_new_day(tmp_path):
    g = DailyGuard(3.0, 5, tmp_path / "daily.json")
    g.roll_day("2026-10-07", 100)
    g.manual_stop = True
    g.save()
    g.roll_day("2026-10-08", 100)
    assert g.can_open() == (False, "manuell gestoppt")


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def test_session_windows():
    s = DEFAULTS["session"]
    assert not in_trade_window(utc(2026, 10, 7, 6, 59), s)
    assert in_trade_window(utc(2026, 10, 7, 7, 0), s)
    assert not in_trade_window(utc(2026, 10, 7, 19, 0), s)
    assert not in_trade_window(utc(2026, 10, 9, 19, 30), s)  # Freitag
    assert not in_trade_window(utc(2026, 10, 10, 12, 0), s)  # Samstag
    assert must_be_flat(utc(2026, 10, 7, 20, 45), s)
    assert not must_be_flat(utc(2026, 10, 7, 20, 44), s)
    assert must_be_flat(utc(2026, 10, 9, 19, 30), s)
