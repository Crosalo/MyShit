"""Kurshistorie + Symbol-Spezifikation aus MT5 exportieren (für den Backtest).

python -m bot.export_history --days 365 --config config.yaml
-> data/EURUSD_M15.csv, data/EURUSD_spec.json, ...

Zeiten werden nach UTC umgerechnet. Die meisten MT5-Broker nutzen
"New-York-Close"-Serverzeit (UTC+2 im Winter, UTC+3 im US-Sommer); das wird
angenommen, wenn es zum aktuell gemessenen Versatz passt.
"""
import argparse
import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from .broker import Broker, load_mt5_module
from .config import load_config


def ny_close_offset_now() -> float:
    ny = pd.Timestamp.now(tz="America/New_York")
    return ny.utcoffset().total_seconds() / 3600 + 7


def server_to_utc(epoch_seconds: pd.Series, offset_hours: float, ny_close: bool) -> pd.Series:
    naive = pd.to_datetime(epoch_seconds, unit="s")
    if ny_close:
        # Serverzeit = New-York-Ortszeit + 7h  (DST-korrekt über das ganze Jahr)
        return (naive - pd.Timedelta(hours=7)).dt.tz_localize(
            "America/New_York", ambiguous="NaT", nonexistent="shift_forward"
        ).dt.tz_convert("UTC")
    return naive.dt.tz_localize("UTC") - pd.Timedelta(hours=offset_hours)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--days", type=int, default=365)
    p.add_argument("--out", default="data")
    args = p.parse_args(argv)
    cfg = load_config(args.config)
    mt5 = load_mt5_module(cfg["mt5"])
    broker = Broker(mt5, {**cfg["mt5"], "allow_live": True})  # nur lesen
    broker.connect()

    offset = broker.server_offset_hours(cfg["symbols"])
    ny_close = abs(offset - ny_close_offset_now()) < 0.01
    print(f"Serverzeit UTC{offset:+g} -> {'New-York-Close (DST-korrekt)' if ny_close else 'fester Versatz'}")

    tf_name = cfg["strategy"]["timeframe"]
    tf = getattr(mt5, f"TIMEFRAME_{tf_name}")
    end = datetime.now(timezone.utc) + timedelta(days=1)
    start = end - timedelta(days=args.days + 1)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for sym in cfg["symbols"]:
        spec = broker.spec(sym)
        if spec is None:
            print(f"{sym}: nicht verfügbar")
            continue
        raw = mt5.copy_rates_range(sym, tf, start, end)
        if raw is None or len(raw) == 0:
            print(f"{sym}: keine Daten ({mt5.last_error()})")
            continue
        df = pd.DataFrame(raw)
        df["time"] = server_to_utc(df["time"], offset, ny_close)
        df = df.dropna(subset=["time"])[["time", "open", "high", "low", "close", "spread"]]
        df.to_csv(out / f"{sym}_{tf_name}.csv", index=False)
        (out / f"{sym}_spec.json").write_text(json.dumps(asdict(spec), indent=2), encoding="utf-8")
        print(f"{sym}: {len(df)} Kerzen {df['time'].iloc[0]:%Y-%m-%d} bis {df['time'].iloc[-1]:%Y-%m-%d}")
    broker.shutdown()


if __name__ == "__main__":
    main()
