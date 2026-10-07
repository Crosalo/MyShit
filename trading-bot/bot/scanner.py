"""Marktauswahl: Der Bot entscheidet selbst, WO gehandelt wird.

Ein Symbol ist handelbar, wenn der Spread im Verhältnis zur normalen
Bewegung (ATR) billig ist. Unter den handelbaren wird nach Trendstärke (ADX)
sortiert; Signale auf besser bewerteten Märkten kommen zuerst dran.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class ScanResult:
    symbol: str
    tradable: bool
    score: float
    adx: float
    atr: float
    spread_atr_ratio: float
    reason: str


def scan(symbol: str, d: pd.DataFrame, i: int, spread_price: float, cfg: dict) -> ScanResult:
    row = d.iloc[i]
    atr_, adx_ = float(row["atr"]), float(row["adx"])
    if not np.isfinite(atr_) or atr_ <= 0 or not np.isfinite(adx_):
        return ScanResult(symbol, False, 0.0, 0.0, 0.0, 0.0, "zu wenig Daten")
    ratio = spread_price / atr_
    max_ratio = cfg["max_spread_atr_ratio"]
    if ratio > max_ratio:
        return ScanResult(symbol, False, 0.0, adx_, atr_, ratio,
                          f"Spread zu teuer ({ratio:.0%} der ATR)")
    score = adx_ * (1 - ratio / max_ratio)
    return ScanResult(symbol, True, score, adx_, atr_, ratio, "ok")


def rank(results: list[ScanResult]) -> list[ScanResult]:
    return sorted((r for r in results if r.tradable), key=lambda r: r.score, reverse=True)
