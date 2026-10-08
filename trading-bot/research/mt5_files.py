"""Kerzen aus den MQL5-Skripten ExportM1.mq5 / ExportBars.mq5 (Mac/Wine, wo das Python-Paket
MetaTrader5 fehlt).

Die Skripte schreiben nach MQL5\\Files\\m1export:
    meta.json            Server-Zeitversatz, Kontowährung
    <NAME>_<TF>.csv      time (Serverzeit, Epoch-Sekunden), open, high, low, close, spread (Points)
    <NAME>_spec.json     Symbol-Spezifikation (tick_value in Kontowährung, Mindestlot, ...)

    spread_profile.json  (optional, aus SpreadProfile.mq5) Spread je Serverstunde aus echten Ticks

Kosten wie in mt5_source: tick_value aus der Spezifikation, Kommission aus der Config für
Forex/Metalle. Der Bar-Spread von MT5 ist der kleinste Spread der Minute. Bei Raw-Konten steht dort
oft 0. Deshalb gilt je Kerze mindestens der gemessene Stunden-Spread aus spread_profile.json,
ersatzweise der halbe Annahme-Spread aus instruments.py.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from bot.export_history import ny_close_offset_now, server_to_utc
from .instruments import BY_NAME, LDN, NY_CASH, NY_FX, Instrument
from .mt5_source import _asset_from_path

FLOOR_SHARE = 0.5  # Untergrenze = Anteil des Annahme-Spreads
MAX_GAP_DAYS = 7  # größere Lücke = fehlende Historie (Feiertage bis ~5 Tage); nur der Block danach zählt


def server_epoch_to_utc(epoch, offset_h: float) -> pd.Series:
    """Server-Epoch (Wandzeit des Servers) -> UTC, sommerzeitrichtig. Ein fester Versatz wäre im Winter
    eine Stunde falsch (NY-Close-Server: UTC+2 im Winter, UTC+3 im Sommer)."""
    ny_close = abs(offset_h - ny_close_offset_now()) < 0.01
    return server_to_utc(pd.Series(np.asarray(epoch, dtype="int64")), offset_h, ny_close)


def _last_block(epoch: np.ndarray) -> int:
    """Index, ab dem die Daten lückenlos sind (Wochenenden sind ~2 Tage)."""
    gaps = np.flatnonzero(np.diff(epoch) > MAX_GAP_DAYS * 86400)
    return int(gaps[-1]) + 1 if len(gaps) else 0


def iter_mt5_files(folder: Path, cfg: dict, symbols: list[str] | None, tf: str = "M1"):
    folder = Path(folder)
    meta = json.loads((folder / "meta.json").read_text())
    offset = meta["server_offset_seconds"] / 3600
    ny_close = abs(offset - ny_close_offset_now()) < 0.01
    commission_cfg = cfg["risk"]["commission_per_lot"]
    profile_file = folder / "spread_profile.json"
    profiles = json.loads(profile_file.read_text()) if profile_file.exists() else {}
    print(f"Export aus {meta.get('server')}, Serverzeit UTC{offset:+g}, NY-Close-Server: {ny_close}", flush=True)
    suffix = f"_{tf}.csv"
    for csv in sorted(folder.glob(f"*{suffix}*")):  # .csv oder gepackt .csv.gz
        name = csv.name[: csv.name.index(suffix)]
        if symbols and name not in symbols:
            continue
        spec_file = folder / f"{name}_spec.json"
        if not spec_file.exists() or csv.stat().st_size == 0:
            print(f"{name}: unvollständig", flush=True)
            continue
        info = json.loads(spec_file.read_text())
        df = pd.read_csv(csv)
        df = df.iloc[_last_block(df["time"].to_numpy()):].reset_index(drop=True)
        if len(df) < 5000:
            print(f"{name}: zu wenig {tf}-Daten ({len(df)})", flush=True)
            continue
        server_hour = (df["time"].to_numpy() // 3600) % 24
        df["time"] = server_to_utc(df["time"], offset, ny_close)
        keep = df["time"].notna().to_numpy()
        server_hour = server_hour[keep]
        df = df.dropna(subset=["time"]).reset_index(drop=True)

        asset = _asset_from_path(info.get("path", ""))
        base = BY_NAME.get(name)
        if base is not None and asset == "other":
            asset = base.asset
        raw = df["spread"].to_numpy(float) * info["point"]
        if name in profiles:
            hourly = np.array([np.nan if v is None else v for v in profiles[name]["hourly_points"]], float)
            hourly = np.where(np.isfinite(hourly), hourly, np.nanmedian(hourly)) * info["point"]
            floor = hourly[server_hour]
            label = "Ticks"
        else:
            floor = np.full(len(raw), base.fallback_spread * FLOOR_SHARE if base else 0.0)
            label = "Annahme"
        spread = np.maximum(raw, floor)
        src = f"{label} {(raw < floor).mean():.0%}"

        tick_value = info.get("trade_tick_value_loss") or info["trade_tick_value"]
        value_per_price_lot = tick_value / (info["trade_tick_size"] or info["point"])
        commission = commission_cfg if asset in ("fx", "metal") else 0.0
        sessions = base.sessions if base else ((NY_CASH,) if asset == "index" else (LDN, NY_FX))
        inst = Instrument(
            name=name, histdata="", dukascopy="", asset=asset,
            quote=info.get("currency_profit", "USD"), contract_size=info["trade_contract_size"],
            commission_usd=commission, sessions=sessions, fallback_spread=float(np.median(spread)),
            commission_price_override=commission / value_per_price_lot if value_per_price_lot else 0.0,
            minlot_value_override=info["volume_min"] * value_per_price_lot,
        )
        yield inst, df[["time", "open", "high", "low", "close"]], spread, src
