"""M1-Daten laden (HistData-Zips oder MT5-Export) und Spread je Kerze bestimmen."""
import io
import json
import math
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from .instruments import Instrument

ROLLOVER_MULT = 4.0  # Spreads um den Tageswechsel (20:55-22:10 UTC) sind ein Vielfaches


def load_histdata(inst: Instrument, folder: Path, cache: Path | None = None) -> pd.DataFrame | None:
    if cache and cache.exists():
        return pd.read_pickle(cache)
    frames = []
    for z in sorted(Path(folder).glob(f"{inst.histdata}_*.zip")):
        with zipfile.ZipFile(z) as zf:
            name = next(n for n in zf.namelist() if n.endswith(".csv"))
            raw = zf.read(name).decode()
        df = pd.read_csv(io.StringIO(raw), sep=";", header=None,
                         names=["t", "open", "high", "low", "close", "vol"])
        frames.append(df)
    if not frames:
        return None
    df = pd.concat(frames, ignore_index=True)
    # HistData: EST ohne Sommerzeit = UTC-5
    df["time"] = pd.to_datetime(df["t"], format="%Y%m%d %H%M%S").dt.tz_localize("UTC") + pd.Timedelta(hours=5)
    df = df.drop(columns=["t", "vol"]).drop_duplicates("time").sort_values("time").reset_index(drop=True)
    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        df.to_pickle(cache)
    return df


def _scale_to_price(raw_level: float, price_level: float) -> float:
    """Dukascopy liefert Integer-Preise; Zehnerpotenz finden, die zum echten Kurs passt."""
    return 10 ** round(math.log10(raw_level / price_level))


def spread_array(df: pd.DataFrame, inst: Instrument, spreads_file: Path | None) -> tuple[np.ndarray, str]:
    """Spread in Preis-Einheiten je Kerze, nach UTC-Stunde aus gemessenem Profil."""
    hours = df["time"].dt.hour.to_numpy()
    minutes = df["time"].dt.minute.to_numpy()
    source = "Annahme"
    profile = np.full(24, inst.fallback_spread)
    data = json.loads(Path(spreads_file).read_text()) if spreads_file and Path(spreads_file).exists() else {}
    if inst.name in data:
        entry = data[inst.name]
        scale = _scale_to_price(entry["raw_price_level"], float(df["close"].median()))
        measured = np.array(entry["raw_hourly"], dtype=float) / scale
        if np.isfinite(measured).sum() >= 12:
            fill = np.nanmedian(measured)
            profile = np.where(np.isfinite(measured), measured, fill)
            # Untergrenze: halber Fallback-Wert (gegen unrealistisch enge Messungen)
            profile = np.maximum(profile, inst.fallback_spread * 0.5)
            source = "gemessen"
    spread = profile[hours]
    if source == "Annahme":
        tod = hours * 60 + minutes
        rollover = (tod >= 20 * 60 + 55) | (tod < 22 * 60 + 10) & (tod >= 21 * 60)
        spread = np.where(rollover, spread * ROLLOVER_MULT, spread)
    return spread.astype(float), source


def load_mt5_csv(path: Path, point: float) -> tuple[pd.DataFrame, np.ndarray]:
    """CSV aus bot.export_history (Zeit UTC, Spread in Points je Kerze)."""
    df = pd.read_csv(path)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    spread = df["spread"].to_numpy(dtype=float) * point
    return df[["time", "open", "high", "low", "close"]], spread
