"""Sechs eigenständige M1-Strategien aus verschiedenen Familien.

Alle Parameter sind VORHER festgelegt und werden nicht auf die Testdaten optimiert
(sonst findet man garantiert etwas, das nur in der Vergangenheit funktioniert).
Jede Funktion bekommt den Kontext eines Symbols und liefert Signals für die Engine.

| Kürzel   | Familie                 | Idee                                                        |
|----------|-------------------------|-------------------------------------------------------------|
| ORB      | Ausbruch                | Erste 15 Min. nach Markteröffnung, Ausbruch aus dieser Range |
| ASIA_MR  | Mean Reversion (ruhig)  | Überdehnungen in der ruhigen Asien-Session zurückhandeln    |
| SQUEEZE  | Volatilitäts-Ausbruch   | Nach extrem enger Bollinger-Phase in Ausbruchsrichtung      |
| TWAP_MR  | Mean Reversion (aktiv)  | Weit vom Session-Durchschnittspreis entfernt -> zurück      |
| MOMO     | Trendfolge              | Ausbruch auf 60-Min-Hoch im Trend, London/NY-Überlappung    |
| FIX_FADE | Ereignis                | Starke Bewegung in den London-Fix (16:00) wird gekontert    |
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from bot.indicators import atr, ema
from .engine import Signals
from .instruments import Instrument


@dataclass
class Context:
    df: pd.DataFrame
    inst: Instrument
    o: np.ndarray = field(init=False)
    h: np.ndarray = field(init=False)
    l: np.ndarray = field(init=False)
    c: np.ndarray = field(init=False)
    utc_min: np.ndarray = field(init=False)
    weekday: np.ndarray = field(init=False)
    atr14: np.ndarray = field(init=False)
    atr60: np.ndarray = field(init=False)
    tf_min: int = field(init=False)
    _local: dict = field(default_factory=dict, init=False)

    def __post_init__(self):
        d = self.df
        self.o, self.h, self.l, self.c = (d[k].to_numpy(float) for k in ("open", "high", "low", "close"))
        self.utc_min = (d["time"].dt.hour * 60 + d["time"].dt.minute).to_numpy()
        self.weekday = d["time"].dt.weekday.to_numpy()
        self.atr14 = atr(d, 14).to_numpy()
        self.atr60 = atr(d, 60).to_numpy()
        diffs = d["time"].diff().dt.total_seconds().dropna()
        self.tf_min = max(1, int(round(diffs.median() / 60))) if len(diffs) else 1

    def atr_n(self, period: int) -> np.ndarray:
        if period == 14:
            return self.atr14
        if period == 60:
            return self.atr60
        return atr(self.df, period).to_numpy()

    def local(self, tz: str) -> tuple[np.ndarray, np.ndarray]:
        """(Tages-Code, Minute des Tages) in lokaler Zeit inkl. Sommerzeit."""
        if tz not in self._local:
            t = self.df["time"].dt.tz_convert(tz)
            day = (t.dt.year * 10000 + t.dt.month * 100 + t.dt.day).to_numpy()
            minute = (t.dt.hour * 60 + t.dt.minute).to_numpy()
            self._local[tz] = (day, minute)
        return self._local[tz]

    def empty(self, max_hold: int) -> Signals:
        n = len(self.c)
        return Signals(np.zeros(n, bool), np.zeros(n, bool), np.full(n, np.nan), np.full(n, np.nan), max_hold)


def _hhmm(s: str) -> int:
    hh, mm = s.split(":")
    return int(hh) * 60 + int(mm)


def _rsi(close: np.ndarray, period: int) -> np.ndarray:
    delta = np.diff(close, prepend=close[0])
    up = pd.Series(np.clip(delta, 0, None)).ewm(alpha=1 / period, adjust=False).mean()
    down = pd.Series(np.clip(-delta, 0, None)).ewm(alpha=1 / period, adjust=False).mean()
    rs = up / down.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50).to_numpy()


# ---------------------------------------------------------------- ORB
def orb(ctx: Context, range_min=15, window_min=105, rr=1.5, max_hold=240) -> Signals:
    sig = ctx.empty(max_hold)
    for tz, hhmm in ctx.inst.sessions:
        day, mins = ctx.local(tz)
        m0 = _hhmm(hhmm)
        in_range = (mins >= m0) & (mins < m0 + range_min)
        in_win = (mins >= m0 + range_min) & (mins < m0 + range_min + window_min)
        frame = pd.DataFrame({"day": day,
                              "h": np.where(in_range, ctx.h, np.nan),
                              "l": np.where(in_range, ctx.l, np.nan)})
        g = frame.groupby("day")
        rh = g["h"].transform("max").to_numpy()
        rl = g["l"].transform("min").to_numpy()
        expected = max(1, round(range_min / ctx.tf_min * 0.8))
        complete = g["h"].transform("count").to_numpy() >= expected
        up = in_win & complete & (ctx.c > rh)
        dn = in_win & complete & (ctx.c < rl)
        brk = up | dn
        first = brk & (pd.Series(brk).groupby(day).cumsum().to_numpy() == 1)
        lg, sh = first & up, first & dn
        sig.long |= lg
        sig.short |= sh
        sig.sl_dist[lg] = (ctx.c - rl)[lg]
        sig.sl_dist[sh] = (rh - ctx.c)[sh]
    sig.tp_dist = sig.sl_dist * rr
    return sig


# ---------------------------------------------------------------- ASIA_MR
def asia_mr(ctx: Context, lookback=60, z_entry=2.2, max_hold=60, sl_atr=2.0, atr_period=14) -> Signals:
    sig = ctx.empty(max_hold)
    m = ctx.utc_min
    win = ((m >= 23 * 60 + 30) | (m < 5 * 60 + 30)) & (ctx.weekday != 5) & ~((ctx.weekday == 4) & (m >= 20 * 60))
    close = pd.Series(ctx.c)
    sma = close.rolling(lookback).mean().to_numpy()
    sd = close.rolling(lookback).std().to_numpy()
    z = (ctx.c - sma) / sd
    rsi = _rsi(ctx.c, 14)
    target = np.abs(sma - ctx.c)
    a = ctx.atr_n(atr_period)
    ok = win & (target >= a)
    sig.long = ok & (z < -z_entry) & (ctx.c > ctx.o) & (rsi < 30)
    sig.short = ok & (z > z_entry) & (ctx.c < ctx.o) & (rsi > 70)
    sig.sl_dist = sl_atr * a
    sig.tp_dist = target
    return sig


# ---------------------------------------------------------------- SQUEEZE
def squeeze(ctx: Context, period=20, squeeze_lookback=240, max_hold=90, window_min=360,
            sl_atr=1.5, tp_atr=3.0, atr_period=60) -> Signals:
    sig = ctx.empty(max_hold)
    close = pd.Series(ctx.c)
    sma = close.rolling(period).mean()
    sd = close.rolling(period).std()
    upper, lower = (sma + 2 * sd).to_numpy(), (sma - 2 * sd).to_numpy()
    bw = (4 * sd / sma)
    tight = (bw.shift(1) <= bw.rolling(squeeze_lookback).min().shift(1) * 1.05).to_numpy()
    win = np.zeros(len(ctx.c), bool)
    for tz, hhmm in ctx.inst.sessions:
        _, mins = ctx.local(tz)
        m0 = _hhmm(hhmm)
        win |= (mins >= m0) & (mins < m0 + window_min)
    sig.long = win & tight & (ctx.c > upper)
    sig.short = win & tight & (ctx.c < lower)
    a = ctx.atr_n(atr_period)
    sig.sl_dist = sl_atr * a
    sig.tp_dist = tp_atr * a
    return sig


# ---------------------------------------------------------------- TWAP_MR
def twap_mr(ctx: Context, dev_entry=4.0, session_min=480, max_hold=120, sl_atr=2.0, tp_frac=0.8,
            atr_period=60) -> Signals:
    sig = ctx.empty(max_hold)
    if ctx.inst.asset == "index":
        tz, hhmm = ctx.inst.sessions[0]
    else:
        tz, hhmm = "Europe/London", "08:00"
    day, mins = ctx.local(tz)
    m0 = _hhmm(hhmm)
    in_sess = (mins >= m0) & (mins < m0 + session_min)
    typical = (ctx.h + ctx.l + ctx.c) / 3
    grp = np.where(in_sess, day, -1)
    s = pd.Series(np.where(in_sess, typical, 0.0))
    twap = (s.groupby(grp).cumsum() / (s.groupby(grp).cumcount() + 1)).to_numpy()
    a = ctx.atr_n(atr_period)
    dev = (ctx.c - twap) / a
    win = in_sess & (mins >= m0 + 60)
    sig.long = win & (dev < -dev_entry) & (ctx.c > ctx.o)
    sig.short = win & (dev > dev_entry) & (ctx.c < ctx.o)
    sig.sl_dist = sl_atr * a
    sig.tp_dist = tp_frac * np.abs(twap - ctx.c)
    return sig


# ---------------------------------------------------------------- MOMO
def momo(ctx: Context, channel=60, max_hold=120, ema_fast=60, ema_slow=240, slope_bars=30,
         sl_atr=3.0, tp_atr=6.0, atr_period=60) -> Signals:
    sig = ctx.empty(max_hold)
    close = pd.Series(ctx.c)
    ef, es = ema(close, ema_fast).to_numpy(), ema(close, ema_slow).to_numpy()
    slope = es - np.roll(es, slope_bars)
    slope[:slope_bars] = 0
    up = (ef > es) & (ctx.c > es) & (slope > 0)
    dn = (ef < es) & (ctx.c < es) & (slope < 0)
    hi = pd.Series(ctx.h).rolling(channel).max().shift(1).to_numpy()
    lo = pd.Series(ctx.l).rolling(channel).min().shift(1).to_numpy()
    if ctx.inst.asset == "index":
        tz, hhmm = ctx.inst.sessions[0]
        _, mins = ctx.local(tz)
        m0 = _hhmm(hhmm)
        win = (mins >= m0 + 30) & (mins < m0 + 300)
    else:
        _, mins = ctx.local("America/New_York")
        win = (mins >= 8 * 60) & (mins < 12 * 60)
    sig.long = win & up & (ctx.c > hi)
    sig.short = win & dn & (ctx.c < lo)
    a = ctx.atr_n(atr_period)
    sig.sl_dist = sl_atr * a
    sig.tp_dist = tp_atr * a
    return sig


# ---------------------------------------------------------------- FIX_FADE
def fix_fade(ctx: Context, min_move_atr=12.0, max_hold=60, start="15:30", signal="16:02",
             atr_period=60) -> Signals:
    """M1: Kerze 16:02 schließt nach dem Fix-Fenster (15:57:30-16:02:30 London)."""
    sig = ctx.empty(max_hold)
    if ctx.inst.asset not in ("fx", "metal"):
        return sig
    day, mins = ctx.local("Europe/London")
    begin = pd.Series(np.where(mins == _hhmm(start), ctx.o, np.nan)).groupby(day).transform("max").to_numpy()
    at_fix = mins == _hhmm(signal)
    move = ctx.c - begin
    strong = at_fix & np.isfinite(move) & (np.abs(move) > min_move_atr * ctx.atr_n(atr_period))
    sig.short = strong & (move > 0)
    sig.long = strong & (move < 0)
    sig.sl_dist = 0.5 * np.abs(move)
    sig.tp_dist = 0.5 * np.abs(move)
    return sig


# Parameter je Zeitrahmen (Minuten). VOR dem Test festgelegt, nicht auf Ergebnisse optimiert.
# Haltedauern in Kerzen des jeweiligen Zeitrahmens; ATR-Schwellen auf das grobere Raster skaliert.
TF_PARAMS = {
    1: {},
    15: {
        "ORB": dict(range_min=30, window_min=180, rr=1.5, max_hold=24),
        "ASIA_MR": dict(lookback=40, z_entry=2.2, max_hold=16, sl_atr=2.0, atr_period=14),
        "SQUEEZE": dict(period=20, squeeze_lookback=120, max_hold=32, window_min=360,
                        sl_atr=1.5, tp_atr=3.0, atr_period=14),
        "TWAP_MR": dict(dev_entry=1.5, session_min=480, max_hold=16, sl_atr=1.0, tp_frac=0.8, atr_period=14),
        "MOMO": dict(channel=16, max_hold=32, ema_fast=32, ema_slow=96, slope_bars=8,
                     sl_atr=1.5, tp_atr=3.0, atr_period=14),
        "FIX_FADE": dict(min_move_atr=2.0, max_hold=8, start="15:30", signal="16:00", atr_period=14),
    },
    60: {
        "ORB": dict(range_min=60, window_min=240, rr=1.5, max_hold=8),
        "ASIA_MR": dict(lookback=24, z_entry=2.0, max_hold=5, sl_atr=2.0, atr_period=14),
        "SQUEEZE": dict(period=20, squeeze_lookback=120, max_hold=10, window_min=360,
                        sl_atr=1.5, tp_atr=3.0, atr_period=14),
        "TWAP_MR": dict(dev_entry=1.0, session_min=480, max_hold=6, sl_atr=1.0, tp_frac=0.8, atr_period=14),
        "MOMO": dict(channel=8, max_hold=10, ema_fast=24, ema_slow=72, slope_bars=6,
                     sl_atr=1.5, tp_atr=3.0, atr_period=14),
        "FIX_FADE": dict(min_move_atr=1.5, max_hold=3, start="14:00", signal="15:00", atr_period=14),
    },
}

STRATEGIES = {
    "ORB": orb,
    "ASIA_MR": asia_mr,
    "SQUEEZE": squeeze,
    "TWAP_MR": twap_mr,
    "MOMO": momo,
    "FIX_FADE": fix_fade,
}
