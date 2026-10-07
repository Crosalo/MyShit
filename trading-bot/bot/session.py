"""Handelszeiten (UTC). Daytrading: keine Positionen über Nacht oder übers Wochenende."""
from datetime import datetime, time


def _t(value: str) -> time:
    hours, minutes = value.split(":")
    return time(int(hours), int(minutes))


def in_trade_window(now_utc: datetime, cfg: dict) -> bool:
    """Dürfen jetzt NEUE Trades eröffnet werden?"""
    weekday, t = now_utc.weekday(), now_utc.time()
    if weekday >= 5:
        return False
    if weekday == 4 and t >= _t(cfg["friday_flat_time"]):
        return False
    return _t(cfg["trade_start"]) <= t < _t(cfg["trade_end"])


def must_be_flat(now_utc: datetime, cfg: dict) -> bool:
    """Müssen jetzt alle Positionen geschlossen sein?"""
    weekday, t = now_utc.weekday(), now_utc.time()
    if weekday >= 5:
        return True
    if weekday == 4 and t >= _t(cfg["friday_flat_time"]):
        return True
    return t >= _t(cfg["flat_time"])
