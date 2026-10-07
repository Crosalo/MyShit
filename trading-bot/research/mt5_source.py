"""M1-Daten direkt aus dem MT5-Terminal (Windows-PC): echte Broker-Kurse und -Spreads.

Kosten werden exakt aus der Symbol-Spezifikation berechnet (tick_value in Kontowährung).
Kommission: config risk.commission_per_lot für Forex/Metalle, 0 für alles andere.
"""
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from bot.broker import Broker, load_mt5_module
from bot.export_history import ny_close_offset_now, server_to_utc
from .instruments import BY_NAME, LDN, NY_CASH, NY_FX, Instrument

SYMBOL_TRADE_MODE_FULL = 4


def _asset_from_path(path: str) -> str:
    p = path.lower()
    if "forex" in p or "fx" in p:
        return "fx"
    if "metal" in p:
        return "metal"
    if "indic" in p or "index" in p:
        return "index"
    if "energ" in p or "oil" in p or "commod" in p:
        return "energy"
    return "other"


def tradable_symbols(mt5) -> list[str]:
    return sorted(s.name for s in mt5.symbols_get() if s.trade_mode == SYMBOL_TRADE_MODE_FULL)


def iter_mt5(cfg: dict, days: int, symbols: list[str] | None):
    mt5 = load_mt5_module(cfg["mt5"])
    broker = Broker(mt5, {**cfg["mt5"], "allow_live": True})  # liest nur, handelt nicht
    broker.connect()
    names = symbols or tradable_symbols(mt5)
    offset = broker.server_offset_hours(names[:10])
    ny_close = abs(offset - ny_close_offset_now()) < 0.01
    end = datetime.now(timezone.utc) + timedelta(days=1)
    start = end - timedelta(days=days + 1)
    commission_cfg = cfg["risk"]["commission_per_lot"]
    print(f"{len(names)} handelbare Symbole, Serverzeit UTC{offset:+g}", flush=True)
    for name in names:
        if not mt5.symbol_select(name, True):
            continue
        info = mt5.symbol_info(name)
        raw = mt5.copy_rates_range(name, mt5.TIMEFRAME_M1, start, end)
        if info is None or raw is None or len(raw) < 5000:
            print(f"{name}: zu wenig M1-Daten ({0 if raw is None else len(raw)})", flush=True)
            continue
        df = pd.DataFrame(raw)
        df["time"] = server_to_utc(df["time"], offset, ny_close)
        df = df.dropna(subset=["time"]).reset_index(drop=True)
        spread = df["spread"].to_numpy(float) * info.point
        asset = _asset_from_path(getattr(info, "path", ""))
        tick_value = getattr(info, "trade_tick_value_loss", 0) or info.trade_tick_value
        value_per_price_lot = tick_value / (info.trade_tick_size or info.point)
        commission = commission_cfg if asset in ("fx", "metal") else 0.0
        base = BY_NAME.get(name)
        sessions = base.sessions if base else ((NY_CASH,) if asset == "index" else (LDN, NY_FX))
        inst = Instrument(
            name=name, histdata="", dukascopy="", asset=asset,
            quote=getattr(info, "currency_profit", "USD"), contract_size=info.trade_contract_size,
            commission_usd=commission, sessions=sessions, fallback_spread=float(np.median(spread)),
            commission_price_override=commission / value_per_price_lot if value_per_price_lot else 0.0,
            minlot_value_override=info.volume_min * value_per_price_lot,
        )
        yield inst, df[["time", "open", "high", "low", "close"]], spread, "MT5"
    broker.shutdown()
