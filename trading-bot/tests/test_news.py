from datetime import datetime, timezone

import pytest

from bot.config import DEFAULTS
from bot.news import NewsCalendar, symbol_currencies

RAW = [
    {"title": "FOMC Meeting Minutes", "country": "USD", "date": "2026-10-07T14:00:00-04:00",
     "impact": "High", "forecast": "", "previous": ""},
    {"title": "BOE Gov Bailey Speaks", "country": "GBP", "date": "2026-10-08T08:15:00-04:00",
     "impact": "High", "forecast": "", "previous": ""},
    {"title": "German Industrial Production", "country": "EUR", "date": "2026-10-07T02:00:00-04:00",
     "impact": "Low", "forecast": "", "previous": ""},
    {"title": "OPEC Meeting", "country": "All", "date": "2026-10-09T05:00:00-04:00",
     "impact": "High", "forecast": "", "previous": ""},
]


class FakeResp:
    def __init__(self, data, status=200):
        self.data, self.status = data, status

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")

    def json(self):
        return self.data


def make_calendar(tmp_path, data=RAW, status=200, now=1_000_000.0, **cfg_over):
    calls = []

    def http_get(url, **kw):
        calls.append(url)
        return FakeResp(data, status)

    cfg = {**DEFAULTS["news"], **cfg_over}
    cal = NewsCalendar(cfg, tmp_path / "cal.json", http_get=http_get, clock=lambda: now)
    return cal, calls


def utc(*a):
    return datetime(*a, tzinfo=timezone.utc)


@pytest.mark.parametrize("symbol,expected", [
    ("EURUSD", ["EUR", "USD"]), ("XAUUSD", ["USD"]), ("GER40", ["EUR"]),
    ("US100", ["USD"]), ("GBPJPY", ["GBP", "JPY"]), ("EURUSD.r", ["EUR", "USD"]),
])
def test_symbol_currencies(symbol, expected):
    assert symbol_currencies(symbol) == expected


def test_blocks_around_high_impact_event(tmp_path):
    cal, _ = make_calendar(tmp_path)
    cal.refresh()
    # FOMC: 18:00 UTC
    assert cal.blocking_event("EURUSD", utc(2026, 10, 7, 17, 31)).title == "FOMC Meeting Minutes"
    assert cal.blocking_event("XAUUSD", utc(2026, 10, 7, 18, 29)) is not None
    assert cal.blocking_event("EURUSD", utc(2026, 10, 7, 17, 29)) is None
    assert cal.blocking_event("GBPJPY", utc(2026, 10, 7, 18, 0)) is None  # kein USD
    assert cal.blocking_event("EURUSD", utc(2026, 10, 7, 6, 0)) is None  # Low impact
    assert cal.blocking_event("AUDJPY", utc(2026, 10, 9, 9, 0)).title == "OPEC Meeting"  # "All"


def test_fail_closed_without_data(tmp_path):
    cal, _ = make_calendar(tmp_path, data=None, status=429)
    cal.refresh()
    assert cal.blocking_event("EURUSD", utc(2026, 10, 7, 12, 0)) == "Kalender veraltet/nicht verfügbar"
    cal_open, _ = make_calendar(tmp_path / "b", data=None, status=429, fail_closed=False)
    cal_open.refresh()
    assert cal_open.blocking_event("EURUSD", utc(2026, 10, 7, 12, 0)) is None


def test_refresh_is_rate_limited_and_cached(tmp_path):
    cal, calls = make_calendar(tmp_path)
    cal.refresh()
    cal.refresh()
    assert len(calls) == 1
    # Neustart liest den Cache statt erneut zu laden
    cal2, calls2 = make_calendar(tmp_path)
    cal2.refresh()
    assert calls2 == [] and len(cal2.events) == len(RAW)
