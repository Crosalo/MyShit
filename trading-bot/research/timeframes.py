"""Höhere Zeitrahmen: Signale auf M15/H1-Kerzen, Ausführung und Ausstieg auf M1.

So entscheidet die echte Minuten-Kursfolge, ob zuerst Stop oder Ziel getroffen wird,
statt der pessimistischen "SL zuerst"-Annahme innerhalb einer großen Kerze.
"""
import numpy as np
import pandas as pd

from .engine import Signals


def resample(m1: pd.DataFrame, minutes: int) -> pd.DataFrame:
    if minutes == 1:
        return m1
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    out = (m1.set_index("time").resample(f"{minutes}min", label="left", closed="left")
           .agg(agg).dropna().reset_index())
    return out


def to_m1(sig: Signals, tf_times: pd.Series, m1_times: pd.Series, minutes: int) -> Signals:
    """Signal auf TF-Kerze j -> letzte M1-Kerze vor Ende von j; Einstieg dann zur nächsten M1-Kerze."""
    if minutes == 1:
        return sig
    n1 = len(m1_times)
    out = Signals(np.zeros(n1, bool), np.zeros(n1, bool), np.full(n1, np.nan), np.full(n1, np.nan),
                  sig.max_hold * minutes)
    idx = np.flatnonzero(sig.long | sig.short)
    if len(idx) == 0:
        return out
    bar_end = (tf_times.iloc[idx] + pd.Timedelta(minutes=minutes)).to_numpy()
    pos = np.searchsorted(m1_times.to_numpy(), bar_end, side="left") - 1
    valid = pos >= 0
    idx, pos = idx[valid], pos[valid]
    out.long[pos] = sig.long[idx]
    out.short[pos] = sig.short[idx]
    out.sl_dist[pos] = sig.sl_dist[idx]
    out.tp_dist[pos] = sig.tp_dist[idx]
    return out
