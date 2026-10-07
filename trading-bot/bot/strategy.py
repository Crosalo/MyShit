"""Basis-Strategie: Trend-Pullback.

Das ist ein TESTOBJEKT, keine bewiesene Gewinnstrategie. Regeln:
- Trend: EMA20 > EMA50 > EMA200 und Kurs über EMA200 (Long), gespiegelt für Short.
- Trendstärke: ADX >= adx_min.
- Einstieg: Kurs läuft in den letzten 2 Kerzen an die EMA20 zurück und die
  Signalkerze schließt wieder in Trendrichtung jenseits der EMA20.
- Stop: sl_atr * ATR, Ziel: rr * Stop-Abstand.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .indicators import adx, atr, ema


@dataclass
class Signal:
    side: str  # "buy" oder "sell"
    entry: float  # Schlusskurs der Signalkerze (Referenz)
    sl_distance: float
    tp_distance: float
    atr: float
    adx: float
    reason: str


class TrendPullback:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.min_bars = int(cfg["ema_trend"]) + 50

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        c = self.cfg
        d = df.copy()
        d["ema_f"] = ema(d["close"], c["ema_fast"])
        d["ema_s"] = ema(d["close"], c["ema_slow"])
        d["ema_t"] = ema(d["close"], c["ema_trend"])
        d["atr"] = atr(d, c["atr_period"])
        d["adx"] = adx(d, c["adx_period"])

        touched_low = np.minimum(d["low"], d["low"].shift(1)) <= d["ema_f"]
        touched_high = np.maximum(d["high"], d["high"].shift(1)) >= d["ema_f"]
        strong = d["adx"] >= c["adx_min"]
        up = (d["ema_f"] > d["ema_s"]) & (d["ema_s"] > d["ema_t"]) & (d["close"] > d["ema_t"])
        down = (d["ema_f"] < d["ema_s"]) & (d["ema_s"] < d["ema_t"]) & (d["close"] < d["ema_t"])

        d["long_sig"] = up & strong & touched_low & (d["close"] > d["ema_f"]) & (d["close"] > d["open"])
        d["short_sig"] = down & strong & touched_high & (d["close"] < d["ema_f"]) & (d["close"] < d["open"])
        d.loc[d.index[: self.min_bars], ["long_sig", "short_sig"]] = False
        return d

    def signal_at(self, d: pd.DataFrame, i: int) -> Signal | None:
        """Signal auf der GESCHLOSSENEN Kerze i (Live: i = len(d) - 2)."""
        if i < self.min_bars or i >= len(d):
            return None
        row = d.iloc[i]
        if not (row["long_sig"] or row["short_sig"]) or not np.isfinite(row["atr"]) or row["atr"] <= 0:
            return None
        sl_distance = self.cfg["sl_atr"] * row["atr"]
        side = "buy" if row["long_sig"] else "sell"
        return Signal(
            side=side,
            entry=float(row["close"]),
            sl_distance=float(sl_distance),
            tp_distance=float(sl_distance * self.cfg["rr"]),
            atr=float(row["atr"]),
            adx=float(row["adx"]),
            reason=f"Trend-Pullback {side} (ADX {row['adx']:.1f})",
        )
