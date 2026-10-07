import numpy as np
import pandas as pd


def make_ohlc(n=600, start=1.1000, drift=0.0, noise=0.0004, seed=1, freq="15min",
              t0="2026-01-05 00:00", spread_points=None):
    """Synthetische M15-Kerzen (UTC). drift/noise pro Kerze in Preis-Einheiten."""
    rng = np.random.default_rng(seed)
    closes = start + np.cumsum(drift + rng.normal(0, noise, n))
    opens = np.concatenate([[start], closes[:-1]])
    wick = np.abs(rng.normal(0, noise / 2, n))
    df = pd.DataFrame({
        "time": pd.date_range(t0, periods=n, freq=freq, tz="UTC"),
        "open": opens,
        "high": np.maximum(opens, closes) + wick,
        "low": np.minimum(opens, closes) - wick,
        "close": closes,
    })
    if spread_points is not None:
        df["spread"] = spread_points
    return df


def uptrend_with_pullback(t0="2026-01-03 05:45"):
    """Aufwärtstrend, dann Rücksetzer unter die EMA20 und bullische Kerze zurück darüber.

    Die Signalkerze ist die letzte (Index 401). Mit dem Standard-t0 liegt die
    Einstiegskerze danach auf Mittwoch 2026-01-07 10:15 UTC (im Handelsfenster).
    """
    from bot.indicators import ema

    df = make_ohlc(n=400, drift=0.0002, noise=0.00005, seed=3, t0=t0)
    last = df["close"].iloc[-1]
    ema20 = ema(df["close"], 20).iloc[-1]
    pull = pd.DataFrame({
        "time": pd.date_range(df["time"].iloc[-1] + pd.Timedelta("15min"), periods=2, freq="15min"),
        "open": [last, ema20 - 0.0002],
        "high": [last, ema20 + 0.0006],
        "low": [ema20 - 0.0003, ema20 - 0.0003],
        "close": [ema20 - 0.0002, ema20 + 0.0005],
    })
    return pd.concat([df, pull], ignore_index=True)


def append_bars(df, bars):
    """bars: Liste von (open, high, low, close) im 15-Minuten-Takt anhängen."""
    times = pd.date_range(df["time"].iloc[-1] + pd.Timedelta("15min"), periods=len(bars), freq="15min")
    extra = pd.DataFrame(bars, columns=["open", "high", "low", "close"])
    extra.insert(0, "time", times)
    return pd.concat([df, extra], ignore_index=True)
