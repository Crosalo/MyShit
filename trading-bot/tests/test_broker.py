from types import SimpleNamespace as NS

import pytest

from bot.broker import LIVE_CONFIRM_ENV, LIVE_CONFIRM_VALUE, Broker, BrokerError, LiveTradingBlocked
from bot.config import DEFAULTS
from tests.fake_mt5 import FakeMT5


def make(mt5=None, **cfg):
    return Broker(mt5 or FakeMT5(), {**DEFAULTS["mt5"], **cfg})


def test_demo_account_connects():
    b = make()
    b.connect()
    assert b.is_demo()


def test_real_account_blocked_by_default():
    with pytest.raises(LiveTradingBlocked):
        make(FakeMT5(trade_mode=2)).connect()


def test_real_account_needs_config_and_env(monkeypatch):
    monkeypatch.delenv(LIVE_CONFIRM_ENV, raising=False)
    with pytest.raises(LiveTradingBlocked):
        make(FakeMT5(trade_mode=2), allow_live=True).connect()
    monkeypatch.setenv(LIVE_CONFIRM_ENV, LIVE_CONFIRM_VALUE)
    make(FakeMT5(trade_mode=2), allow_live=True).connect()


def test_password_comes_from_env(monkeypatch):
    monkeypatch.setenv("MT5_PASSWORD", "geheim")
    mt5 = FakeMT5()
    make(mt5, login="123", server="FusionMarkets-Demo").connect()
    assert mt5.init_args[1] == {"login": 123, "password": "geheim", "server": "FusionMarkets-Demo"}


def test_buy_request_uses_ask_and_relative_stops():
    b = make()
    spec = b.spec("EURUSD")
    req = b.build_market_request("EURUSD", "buy", 0.05, 0.0020, 0.0040, spec)
    assert req["price"] == 1.10002
    assert req["sl"] == round(1.10002 - 0.0020, 5) and req["tp"] == round(1.10002 + 0.0040, 5)
    assert req["type_filling"] == FakeMT5.ORDER_FILLING_IOC
    assert req["magic"] == DEFAULTS["mt5"]["magic"]


def test_sell_request_uses_bid():
    b = make(FakeMT5(filling_mode=1))
    req = b.build_market_request("EURUSD", "sell", 0.05, 0.0020, 0.0040, b.spec("EURUSD"))
    assert req["price"] == 1.10000 and req["sl"] > req["price"] > req["tp"]
    assert req["type_filling"] == FakeMT5.ORDER_FILLING_FOK


def test_stop_below_broker_minimum_is_rejected():
    b = make(FakeMT5(stops_level=500))
    with pytest.raises(BrokerError):
        b.build_market_request("EURUSD", "buy", 0.05, 0.0020, 0.0040, b.spec("EURUSD"))


def test_positions_filtered_by_magic():
    mt5 = FakeMT5()
    mt5.positions = [NS(symbol="EURUSD", magic=DEFAULTS["mt5"]["magic"]), NS(symbol="EURUSD", magic=1)]
    assert len(make(mt5).positions()) == 1


def test_server_offset_and_rates_in_utc():
    b = make(FakeMT5(server_offset_h=3))
    assert b.server_offset_hours(["EURUSD"]) == 3
    df = b.rates("EURUSD", "M15", 5, 3)
    assert str(df["time"].dt.tz) == "UTC" and len(df) == 5
    assert df["time"].iloc[0].timestamp() == 1_791_000_000 - 3 * 3600


def test_unknown_symbol_returns_none():
    assert make().spec("NOPE") is None
