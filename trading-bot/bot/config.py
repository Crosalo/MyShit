"""Konfiguration laden: config.yaml wird über DEFAULTS gelegt."""
import copy
from pathlib import Path

import yaml

DEFAULTS = {
    "mt5": {
        "bridge": "native",  # native = Windows + MetaTrader5-Paket, rpyc = Linux/VPS via mt5linux
        "rpyc_host": "localhost",
        "rpyc_port": 18812,
        "path": None,
        "login": None,
        "server": None,
        "allow_live": False,
        "magic": 20261007,
        "deviation_points": 20,
        "server_utc_offset_hours": "auto",
    },
    "symbols": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "XAUUSD"],
    "strategy": {
        "timeframe": "M15",
        "ema_fast": 20,
        "ema_slow": 50,
        "ema_trend": 200,
        "adx_period": 14,
        "adx_min": 20.0,
        "atr_period": 14,
        "sl_atr": 1.5,
        "rr": 2.0,
    },
    "scanner": {
        "max_spread_atr_ratio": 0.15,
    },
    "risk": {
        "risk_per_trade_pct": 1.0,
        "max_daily_loss_pct": 3.0,
        "max_open_positions": 2,
        "max_trades_per_day": 6,
        "commission_per_lot": 4.5,
    },
    "session": {
        # Alle Zeiten in UTC
        "trade_start": "07:00",
        "trade_end": "19:00",
        "flat_time": "20:45",
        "friday_flat_time": "19:30",
    },
    "news": {
        "enabled": True,
        "url": "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
        "impacts": ["High"],
        "minutes_before": 30,
        "minutes_after": 30,
        "refresh_minutes": 240,
        "max_age_hours": 24,
        "fail_closed": True,
        "symbol_currencies": {},
    },
    "telegram": {
        "enabled": False,
    },
    "loop": {
        "poll_seconds": 20,
    },
    "state_dir": "state",
    "log_dir": "logs",
}


def deep_merge(base: dict, override: dict) -> dict:
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def load_config(path: str | None = "config.yaml") -> dict:
    cfg = copy.deepcopy(DEFAULTS)
    if path is None:
        return cfg
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"{path} fehlt. Kopiere config.example.yaml nach config.yaml und passe sie an."
        )
    with p.open(encoding="utf-8") as f:
        deep_merge(cfg, yaml.safe_load(f) or {})
    return cfg
