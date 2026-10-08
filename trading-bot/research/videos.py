"""Neun YouTube-Strategien (Stand 07.10.2026), mechanisch nachgebaut und auf Fusion-Daten getestet.

Alle Regeln und Parameter sind VOR dem Test festgelegt und werden nicht nachjustiert.
Ermessensregeln aus den Videos ("starke Kerze", "sauberes Setup") sind so wörtlich wie möglich
in feste Regeln übersetzt. Kosten: gemessener Spread je Stunde plus Kommission (FX/Metalle).
Swaps bei Haltedauer über Nacht sind NICHT berücksichtigt.

Daten (aus ExportBars.mq5): M5 = 1 Jahr (daraus M15 und H1-Intraday), H1 = 2019-2026, D1 = ab 1997.

    python -m research.videos --data "<MQL5>/Files/m1export"
"""
import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from bot.config import load_config
from .mt5_files import iter_mt5_files, server_epoch_to_utc

US_INDICES = ("US100", "US500", "US30")
NY = "America/New_York"


# ------------------------------------------------------------------ Daten
class Bars:
    """OHLC + Spread eines Symbols auf einem Zeitrahmen, mit New-York-Ortszeit."""

    def __init__(self, df: pd.DataFrame, spread: np.ndarray, commission: float, name: str):
        self.name, self.commission = name, commission
        self.t = df["time"].reset_index(drop=True)
        self.o, self.h, self.l, self.c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
        self.spread = np.asarray(spread, float)
        ny = self.t.dt.tz_convert(NY)
        self.ny_day = (ny.dt.year * 10000 + ny.dt.month * 100 + ny.dt.day).to_numpy()
        self.ny_min = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
        self.weekday = self.t.dt.weekday.to_numpy()
        self.n = len(self.c)
        prev = np.r_[self.c[0], self.c[:-1]]
        tr = np.maximum(self.h - self.l, np.maximum(np.abs(self.h - prev), np.abs(self.l - prev)))
        self.atr = pd.Series(tr).rolling(14, min_periods=5).mean().to_numpy()

    def resample(self, minutes: int) -> "Bars":
        df = pd.DataFrame({"time": self.t, "open": self.o, "high": self.h, "low": self.l, "close": self.c,
                           "spread": self.spread}).set_index("time")
        r = df.resample(f"{minutes}min", label="left", closed="left").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "spread": "mean"}).dropna().reset_index()
        return Bars(r, r["spread"].to_numpy(), self.commission, self.name)

    def day_starts(self) -> list[tuple[int, int]]:
        s = np.flatnonzero(np.r_[True, self.ny_day[1:] != self.ny_day[:-1]])
        return list(zip(s, np.r_[s[1:], self.n]))


def d1_frame(path: Path, offset_h: float) -> pd.DataFrame:
    """D1 mit Zeitpunkt, ab dem die Kerze fertig ist (UTC), SMA50 und ATR14 des Tages."""
    d = pd.read_csv(path)
    prev = d["close"].shift(1)
    tr = np.maximum(d["high"] - d["low"], np.maximum((d["high"] - prev).abs(), (d["low"] - prev).abs()))
    d["sma50"] = d["close"].rolling(50).mean()
    d["atr14"] = tr.rolling(14).mean()
    d["ready"] = server_epoch_to_utc(d["time"] + 86400, offset_h).to_numpy()
    d = d.dropna(subset=["ready"])
    return d.set_index("ready").sort_index()


def d1_asof(d1: pd.DataFrame, times: pd.Series, col: str) -> np.ndarray:
    return d1[col].reindex(times, method="ffill").to_numpy()


# ------------------------------------------------------------------ Ausführung
def exit_trade(b: Bars, k0: int, d: int, entry: float, stop: float, target: float | None, last: int):
    """Stop vor Ziel; auf der Einstiegskerze zählt nur der Stop. Kerzen sind Bid, Short zahlt den Spread beim Ausstieg."""
    for k in range(k0, min(last, b.n - 1) + 1):
        ah, al, ao = b.h[k] + b.spread[k], b.l[k] + b.spread[k], b.o[k] + b.spread[k]
        if d == 1:
            if b.l[k] <= stop:
                return k, (min(b.o[k], stop) if k > k0 else stop), "SL"
            if k > k0 and target is not None and b.h[k] >= target:
                return k, target, "TP"
        else:
            if ah >= stop:
                return k, (max(ao, stop) if k > k0 else stop), "SL"
            if k > k0 and target is not None and al <= target:
                return k, target, "TP"
    k = min(last, b.n - 1)
    return k, (b.c[k] if d == 1 else b.c[k] + b.spread[k]), "ZEIT"


def trade(b: Bars, k0: int, d: int, entry: float, stop: float, target: float | None, last: int, tag: str) -> dict | None:
    risk = abs(entry - stop)
    if risk <= 0 or (target is not None and (target - entry) * d <= 0):
        return None
    if risk < 3 * (b.spread[k0] + b.commission):  # Stop enger als 3x Kosten: nicht handelbar
        return None
    k, px, reason = exit_trade(b, k0, d, entry, stop, target, last)
    r = ((px - entry) * d - b.commission) / risk
    return {"symbol": b.name, "time": b.t.iloc[k0], "dir": d, "r": r, "reason": reason, "tag": tag, "entry": entry}


def market_next_open(b: Bars, k: int, d: int, stop: float, target: float | None, last: int, tag: str):
    """Signal auf Schlusskurs von k, Einstieg zur Eröffnung von k+1 (Long zum Ask)."""
    if k + 1 >= b.n:
        return None
    e = b.o[k + 1] + (b.spread[k + 1] if d == 1 else 0.0)
    if (e - stop) * d <= 0:
        return None
    return trade(b, k + 1, d, e, stop, target, last, tag)


def session_last(b: Bars, k: int, end_min: int = 16 * 60) -> int:
    """Letzte Kerze desselben NY-Tages vor end_min."""
    j = k
    while j + 1 < b.n and b.ny_day[j + 1] == b.ny_day[k] and b.ny_min[j + 1] < end_min:
        j += 1
    return j


def weekend_last(b: Bars, k: int, max_hold: int) -> int:
    """Spätestens nach max_hold Kerzen oder vor Freitag 20:00 UTC."""
    last = min(b.n - 1, k + max_hold)
    fri = np.flatnonzero((b.weekday[k:last + 1] == 4) & (b.t.iloc[k:last + 1].dt.hour >= 20).to_numpy())
    return k + int(fri[0]) if len(fri) else last


def pivots(h, l, k=3):
    n = len(h)
    ph, pl = np.zeros(n, bool), np.zeros(n, bool)
    for i in range(k, n - k):
        wh, wl = h[i - k:i + k + 1], l[i - k:i + k + 1]
        ph[i] = h[i] == wh.max() and (wh == h[i]).sum() == 1
        pl[i] = l[i] == wl.min() and (wl == l[i]).sum() == 1
    return ph, pl


# ------------------------------------------------------------------ V1 Sneaky Pivot (+ V2-Filter)
def sneaky_pivot(b15: Bars, d1: pd.DataFrame | None, filt: str = "") -> list[dict]:
    """M15. Zone: erste 15-Min-Kerze ab 9:30 NY erreicht das Vortagestief (+10 % der Vortagesspanne)
    -> Long-Setup (Hoch spiegelbildlich). 'Sneaky' = erste grüne Kerze unter den Kerzen 2-4.
    Einstieg: Buy-Stop über deren Hoch bis 11:00 NY. Stop: Tagestief seit 9:30. Ziel: Vortageshoch.
    filt='trend': nur in Richtung D1-Schluss vs. SMA50 (Video 2). 'trend+atr': zusätzlich Ziel <= 1 D1-ATR."""
    out = []
    days = b15.day_starts()
    day_hl = {}
    for a, e in days:
        day_hl[b15.ny_day[a]] = (b15.h[a:e].max(), b15.l[a:e].min())
    keys = list(day_hl)
    for i, (a, e) in enumerate(days):
        if i == 0:
            continue
        pdh, pdl = day_hl[keys[i - 1]]
        rng = pdh - pdl
        idx = [k for k in range(a, e) if 570 <= b15.ny_min[k] < 660]  # 9:30-11:00
        if len(idx) < 4 or b15.ny_min[idx[0]] != 570:
            continue
        k1 = idx[0]
        near_low = b15.l[k1] <= pdl + 0.1 * rng
        near_high = b15.h[k1] >= pdh - 0.1 * rng
        if near_low == near_high:
            continue
        d = 1 if near_low else -1
        if filt and d1 is not None:
            t = b15.t.iloc[k1:k1 + 1]
            sma, cl, atr = (d1_asof(d1, t, col)[0] for col in ("sma50", "close", "atr14"))
            if not np.isfinite(sma) or np.sign(cl - sma) != d:
                continue
        sneaky = next((k for k in idx[1:4] if (b15.c[k] > b15.o[k]) == (d == 1) and b15.c[k] != b15.o[k]), None)
        if sneaky is None:
            continue
        level = b15.h[sneaky] if d == 1 else b15.l[sneaky]
        target = pdh if d == 1 else pdl
        for k in [x for x in idx if x > sneaky]:
            ah, al = b15.h[k] + b15.spread[k], b15.l[k] + b15.spread[k]
            if (d == 1 and ah >= level) or (d == -1 and b15.l[k] <= level):
                entry = max(b15.o[k] + b15.spread[k], level) if d == 1 else min(b15.o[k], level)
                stop = b15.l[k1:k + 1].min() if d == 1 else b15.h[k1:k + 1].max() + 0.0
                if filt == "trend+atr":
                    atr = d1_asof(d1, b15.t.iloc[k:k + 1], "atr14")[0]
                    if not np.isfinite(atr) or abs(target - entry) > atr:
                        break
                t = trade(b15, k, d, entry, stop, target, session_last(b15, k), "SNEAKY")
                if t:
                    out.append(t)
                break
    return out


# ------------------------------------------------------------------ V2 Behauptung "Kauf zur Eröffnung"
def buy_the_open(b5: Bars) -> dict[str, list[float]]:
    """Kaufen 9:30 NY, verkaufen nach 60/120 Min. und 16:00 NY. Ergebnis in Prozent je Tag (ohne Kosten)."""
    res = {"1h": [], "2h": [], "16:00": []}
    for a, e in b5.day_starts():
        m = b5.ny_min[a:e]
        try:
            i0 = a + int(np.flatnonzero(m == 570)[0])
        except IndexError:
            continue
        p0 = b5.o[i0]
        for label, mins in (("1h", 630), ("2h", 690), ("16:00", 960)):
            j = np.flatnonzero(m == mins)
            if len(j):
                res[label].append(b5.o[a + int(j[0])] / p0 - 1)
    return res


# ------------------------------------------------------------------ V3 Scarface: Break & Retest mit Stop am Gegenrand
def break_retest_wide(b5: Bars) -> list[dict]:
    """Wie research.break_retest (M5), aber Stop am gegenüberliegenden Rand der 5-Min-Range, Ziel 2R."""
    out = []
    for a, e in b5.day_starts():
        rng_idx = [k for k in range(a, e) if b5.ny_min[k] == 570]
        if not rng_idx:
            continue
        r0 = rng_idx[0]
        rh, rl = b5.h[r0], b5.l[r0]
        direction, touched = 0, False
        for k in range(r0 + 1, e):
            if b5.ny_min[k] >= 690:
                break
            if direction == 0:
                if b5.c[k] > rh:
                    direction, touched = 1, False
                elif b5.c[k] < rl:
                    direction, touched = -1, False
                continue
            lvl = rh if direction == 1 else rl
            if (b5.c[k] - lvl) * direction < 0:
                direction = 0
                continue
            if (direction == 1 and b5.l[k] <= rh) or (direction == -1 and b5.h[k] >= rl):
                touched = True
            if touched and (b5.c[k] - b5.o[k]) * direction > 0:
                stop = rl if direction == 1 else rh
                e0 = b5.o[k + 1] + (b5.spread[k + 1] if direction == 1 else 0) if k + 1 < b5.n else None
                if e0 is not None:
                    t = trade(b5, k + 1, direction, e0, stop, e0 + 2 * abs(e0 - stop) * direction,
                              session_last(b5, k + 1), "BR_WIDE")
                    if t:
                        out.append(t)
                break
    return out


# ------------------------------------------------------------------ V4 Trendlinienbruch
def trendline_break(b: Bars, max_hold: int) -> list[dict]:
    """Aufwärtslinie durch die zwei letzten bestätigten steigenden Pivot-Tiefs. Bruch = rote Kerze mit
    Körper >= 0,5 ATR schließt unter der Linie -> Short zum nächsten Open. Stop: letztes Pivot-Hoch.
    Kein Ziel; Ausstieg, wenn eine Kerze über der Abwärtslinie durch die zwei letzten fallenden
    Pivot-Hochs schließt (oder max_hold / Wochenende). Long spiegelbildlich."""
    ph, pl = pivots(b.h, b.l)
    out, k = [], 10
    lows, highs = [], []
    busy = -1
    while k < b.n - 1:
        j = k - 3
        if ph[j]:
            highs.append(j)
        if pl[j]:
            lows.append(j)
        if k > busy:
            for d, pts, opp in ((-1, lows, highs), (1, highs, lows)):
                if len(pts) < 2 or not opp:
                    continue
                p1, p2 = pts[-2], pts[-1]
                y1, y2 = (b.l[p1], b.l[p2]) if d == -1 else (b.h[p1], b.h[p2])
                rising = y2 > y1 if d == -1 else y2 < y1  # Aufwärtslinie für Short, Abwärtslinie für Long
                if not rising:
                    continue
                line = y1 + (y2 - y1) * (k - p1) / (p2 - p1)
                body = (b.c[k] - b.o[k]) * d
                if (b.c[k] - line) * d > 0 and body >= 0.5 * b.atr[k] and (b.c[k - 1] - (y1 + (y2 - y1) * (k - 1 - p1) / (p2 - p1))) * d <= 0:
                    stop = b.h[opp[-1]] if d == -1 else b.l[opp[-1]]
                    if k + 1 >= b.n:
                        break
                    e0 = b.o[k + 1] + (b.spread[k + 1] if d == 1 else 0)
                    if (e0 - stop) * d <= 0 or abs(e0 - stop) < 3 * (b.spread[k + 1] + b.commission):
                        continue
                    last = weekend_last(b, k + 1, max_hold)
                    # Ausstieg über Gegenlinie: Pivots NACH dem Einstieg
                    ex_k, ex_px, reason = None, None, ""
                    piv_after = []
                    for m in range(k + 1, last + 1):
                        if (d == 1 and b.l[m] <= stop) or (d == -1 and b.h[m] + b.spread[m] >= stop):
                            ex_k, ex_px, reason = m, (stop if m == k + 1 else (min(b.o[m], stop) if d == 1 else max(b.o[m] + b.spread[m], stop))), "SL"
                            break
                        q = m - 3
                        if q > k and ((d == -1 and ph[q]) or (d == 1 and pl[q])):
                            piv_after.append(q)
                        if len(piv_after) >= 2:
                            q1, q2 = piv_after[-2], piv_after[-1]
                            z1, z2 = (b.h[q1], b.h[q2]) if d == -1 else (b.l[q1], b.l[q2])
                            if (z2 < z1) if d == -1 else (z2 > z1):
                                ln = z1 + (z2 - z1) * (m - q1) / (q2 - q1)
                                if (b.c[m] - ln) * d < 0:
                                    ex_k, ex_px, reason = m, (b.c[m] if d == 1 else b.c[m] + b.spread[m]), "LINIE"
                                    break
                    if ex_k is None:
                        ex_k, ex_px, reason = last, (b.c[last] if d == 1 else b.c[last] + b.spread[last]), "ZEIT"
                    r = ((ex_px - e0) * d - b.commission) / abs(e0 - stop)
                    out.append({"symbol": b.name, "time": b.t.iloc[k + 1], "dir": d, "r": r, "reason": reason, "tag": "TREND",
                                "entry": e0})
                    busy = ex_k
                    break
        k += 1
    return out


# ------------------------------------------------------------------ V5 PBD (Impuls -> Seitwärts -> Fortsetzung)
def pbd(b: Bars, max_hold: int) -> list[dict]:
    """Impuls: 6 Kerzen, Schluss-zu-Schluss >= 3 ATR, mind. 5 Schlüsse in Richtung.
    Seitwärts: die folgenden 6-24 Kerzen, Körper-Spanne <= 1,5 ATR, kein Schluss unter der Impuls-Mitte.
    Einstieg: erster Schluss über dem höchsten Körper der Seitwärtsphase (nächstes Open).
    Stop: tiefster Körper der Seitwärtsphase. Ziel 2R. Short ("b") spiegelbildlich."""
    out, k, busy = [], 30, -1
    c, o = b.c, b.o
    while k < b.n - 30:
        if k <= busy:
            k += 1
            continue
        a = b.atr[k]
        mv = c[k] - c[k - 6]
        if not np.isfinite(a) or abs(mv) < 3 * a:
            k += 1
            continue
        d = 1 if mv > 0 else -1
        if ((np.diff(c[k - 6:k + 1]) * d) > 0).sum() < 5:
            k += 1
            continue
        mid = (c[k] + c[k - 6]) / 2
        hi_body = lo_body = c[k]
        done = False
        for m in range(k + 1, min(k + 25, b.n - 1)):
            bt, bb = max(o[m], c[m]), min(o[m], c[m])
            if (c[m] - mid) * d < 0:
                break
            span = m - k
            if span >= 6 and (c[m] - (hi_body if d == 1 else lo_body)) * d > 0:
                stop = lo_body if d == 1 else hi_body
                last = weekend_last(b, m + 1, max_hold)
                e0 = o[m + 1] + (b.spread[m + 1] if d == 1 else 0)
                if (e0 - stop) * d > 0:
                    t = trade(b, m + 1, d, e0, stop, e0 + 2 * abs(e0 - stop) * d, last, "PBD")
                    if t:
                        out.append(t)
                        busy = m + 1
                done = True
                break
            hi_body, lo_body = max(hi_body, bt), min(lo_body, bb)
            if hi_body - lo_body > 1.5 * a:
                break
        k = max(k + 1, busy + 1) if done else k + 1
    return out


# ------------------------------------------------------------------ V6 TradingLab (Struktur + Demand/Supply + CRV 2,5)
def tradinglab(b: Bars, max_hold: int) -> list[dict]:
    """Trend: Schluss über dem letzten bestätigten Swing-Hoch -> Aufwärtstrend; gültiges Tief = tiefster
    Kurs zwischen diesem Swing-Hoch und dem Bruch. Nur ein Schluss unter dem gültigen Tief beendet den
    Trend (kleinere Tiefs zählen nicht). Abwärtstrend spiegelbildlich.
    Impuls = Kerze mit Spanne >= 2 ATR in Trendrichtung; Zone = Kerze davor. Limit am Zonenrand,
    100 Kerzen gültig, nur erste Berührung; Stop hinter der Zone; Ziel = Extrem seit dem Impuls; nur CRV >= 2,5."""
    ph, pl = pivots(b.h, b.l)
    out, zones = [], []
    trend, prot = 0, np.nan
    last_ph = last_pl = -1
    busy = -1
    for k in range(10, b.n - 1):
        j = k - 3
        if ph[j]:
            last_ph = j
        if pl[j]:
            last_pl = j
        if trend == 1 and b.c[k] < prot or trend == -1 and b.c[k] > prot:
            trend, zones = 0, []
        if trend != -1 and last_ph >= 0 and b.c[k] > b.h[last_ph]:
            if trend != 1:
                zones = []
            trend, prot, last_ph = 1, b.l[last_ph:k + 1].min(), -1
        elif trend != 1 and last_pl >= 0 and b.c[k] < b.l[last_pl]:
            if trend != -1:
                zones = []
            trend, prot, last_pl = -1, b.h[last_pl:k + 1].max(), -1
        a = b.atr[k]
        if trend != 0 and np.isfinite(a) and (b.h[k] - b.l[k]) >= 2 * a and (b.c[k] - b.o[k]) * trend > 0:
            zones.append((k, trend, b.h[k - 1], b.l[k - 1]))
        if k <= busy:
            continue
        keep = []
        for zi, d, top, bot in zones:
            if zi >= k:
                keep.append((zi, d, top, bot))
                continue
            if k - zi > 100 or d != trend:
                continue
            entry, stop = (top, bot) if d == 1 else (bot, top)
            touched = (b.l[k] + b.spread[k] <= entry) if d == 1 else (b.h[k] >= entry)
            if not touched:
                keep.append((zi, d, top, bot))
                continue
            target = b.h[zi:k].max() if d == 1 else b.l[zi:k].min()
            if abs(target - entry) >= 2.5 * abs(entry - stop):
                fill = min(b.o[k] + b.spread[k], entry) if d == 1 else max(b.o[k], entry)
                t = trade(b, k, d, fill, stop, target, weekend_last(b, k, max_hold), "TLAB")
                if t:
                    out.append(t)
                    busy = k
        zones = keep
    return out


# ------------------------------------------------------------------ V7 TJR (Overnight-Sweep zur NY-Eröffnung)
def tjr(b5: Bars) -> list[dict]:
    """Overnight-Range = 18:00 Vortag bis 9:30 NY. Zwischen 9:30 und 11:00 sticht der Kurs über das
    Overnight-Hoch und schließt wieder darunter (Sweep) -> Short-Bias (Tief spiegelbildlich).
    BOS: Schluss unter dem tiefsten Tief der 6 Kerzen vor dem Sweep, innerhalb von 12 Kerzen.
    Einstieg: Sell-Limit an der Unterkante des letzten bärischen FVG zwischen Sweep und BOS (12 Kerzen gültig).
    Stop: Sweep-Hoch. Ziel: Overnight-Tief (Liquidität), mind. 1R, sonst kein Trade. Ausstieg 16:00 NY."""
    out = []
    t_ny = b5.t.dt.tz_convert(NY)
    sess = (t_ny - pd.Timedelta(hours=18)).dt.date.to_numpy()  # Overnight + Folgetag = eine "Sitzung"
    starts = np.flatnonzero(np.r_[True, sess[1:] != sess[:-1]])
    for a, e in zip(starts, np.r_[starts[1:], b5.n]):
        m = b5.ny_min[a:e]
        on = np.flatnonzero((m >= 18 * 60) | (m < 570)) + a
        op = [k for k in range(a, e) if 570 <= b5.ny_min[k] < 660]
        if len(on) < 50 or not op:
            continue
        on_hi, on_lo = b5.h[on].max(), b5.l[on].min()
        for k in op:
            for d, lvl in ((-1, on_hi), (1, on_lo)):
                swept = (b5.h[k] > lvl and b5.c[k] < lvl) if d == -1 else (b5.l[k] < lvl and b5.c[k] > lvl)
                if not swept:
                    continue
                ref = b5.l[max(a, k - 6):k].min() if d == -1 else b5.h[max(a, k - 6):k].max()
                ext = b5.h[k] if d == -1 else b5.l[k]
                bos = None
                for j in range(k + 1, min(k + 13, e)):
                    ext = max(ext, b5.h[j]) if d == -1 else min(ext, b5.l[j])
                    if (b5.c[j] - ref) * d > 0:
                        bos = j
                        break
                if bos is None:
                    continue
                fvg = [x for x in range(k + 2, bos + 1) if (b5.l[x - 2] > b5.h[x] if d == -1 else b5.h[x - 2] < b5.l[x])]
                if not fvg:
                    continue
                x = fvg[-1]
                entry = b5.h[x] if d == -1 else b5.l[x]
                stop, target = ext, (on_lo if d == -1 else on_hi)
                if abs(target - entry) < abs(entry - stop):
                    continue
                for q in range(bos + 1, min(bos + 13, e)):
                    if (d == -1 and b5.l[q] <= target) or (d == 1 and b5.h[q] >= target):
                        break
                    filled = (b5.h[q] >= entry) if d == -1 else (b5.l[q] + b5.spread[q] <= entry)
                    if filled:
                        t = trade(b5, q, d, entry, stop, target, session_last(b5, q), "TJR")
                        if t:
                            out.append(t)
                        break
                break
            else:
                continue
            break
    return out


# ------------------------------------------------------------------ V8a Range-Fehlausbruch
def range_fakeout(b5: Bars, h1_bias: np.ndarray | None, to_mid: bool, window: int = 48, hold: int = 96) -> list[dict]:
    """Range = Hoch/Tief der letzten 48 M5-Kerzen (4 h), Breite <= 6 ATR. Fehlausbruch Long: Tief unter
    dem Range-Tief, Schluss wieder darüber -> Long zum nächsten Open. Stop: Tief der Kerze.
    Ziel: Range-Mitte (Video) bzw. Range-Hoch. Optional nur mit H1-Trend (Schluss über EMA50)."""
    out, busy = [], -1
    hh = pd.Series(b5.h).rolling(window).max().shift(1).to_numpy()
    ll = pd.Series(b5.l).rolling(window).min().shift(1).to_numpy()
    for k in range(window + 12, b5.n - 1):
        if k <= busy or not np.isfinite(hh[k]) or (hh[k] - ll[k]) > 6 * b5.atr[k]:
            continue
        for d in (1, -1):
            edge = ll[k] if d == 1 else hh[k]
            if not ((b5.l[k] < edge < b5.c[k]) if d == 1 else (b5.h[k] > edge > b5.c[k])):
                continue
            if h1_bias is not None and h1_bias[k] != d:
                continue
            stop = b5.l[k] if d == 1 else b5.h[k]
            target = (hh[k] + ll[k]) / 2 if to_mid else (hh[k] if d == 1 else ll[k])
            t = market_next_open(b5, k, d, stop, target, weekend_last(b5, k + 1, hold), "RANGE")
            if t:
                out.append(t)
                busy = k + 1
            break
    return out


# ------------------------------------------------------------------ V8b Trend-Pullback 5R
def pullback_5r(b5: Bars, h1_bias: np.ndarray, hold: int = 96) -> list[dict]:
    """H1-Trend (Schluss über EMA50 und EMA50 steigend). M5: nach Swing-Tief L und Swing-Hoch H
    läuft der Kurs auf <= 50 % zurück, bleibt über L und bildet ein höheres Pivot-Tief P.
    Einstieg: erster Schluss über dem Hoch der Bestätigungskerze von P (24 Kerzen gültig), nächstes Open.
    Stop: P. Ziel 5R. Short spiegelbildlich."""
    ph, pl = pivots(b5.h, b5.l)
    out, busy, armed = [], -1, None
    last_l = last_h = -1
    for k in range(10, b5.n - 1):
        j = k - 3
        if pl[j]:
            if 0 <= last_l < last_h < j and h1_bias[k] == 1:
                L, H, P = b5.l[last_l], b5.h[last_h], b5.l[j]
                if L < P <= L + 0.5 * (H - L):
                    armed = (1, P, b5.h[k], k)
            last_l = j
        if ph[j]:
            if 0 <= last_h < last_l < j and h1_bias[k] == -1:
                H, L, P = b5.h[last_h], b5.l[last_l], b5.h[j]
                if H > P >= H - 0.5 * (H - L):
                    armed = (-1, P, b5.l[k], k)
            last_h = j
        if armed and k > armed[3] and k > busy:
            d, P, trig, k_arm = armed
            if k - k_arm > 24:
                armed = None
            elif (b5.c[k] - trig) * d > 0:
                e0 = b5.o[k + 1] + (b5.spread[k + 1] if d == 1 else 0)
                t = trade(b5, k + 1, d, e0, P, e0 + 5 * abs(e0 - P) * d, weekend_last(b5, k + 1, hold), "PB5R")
                if t:
                    out.append(t)
                    busy = k + 1
                armed = None
    return out


# ------------------------------------------------------------------ V9 TwinTraders Scalping (H1-FVG + M5-Sweep/BOS)
def twin_scalp(b5: Bars, b60: Bars) -> list[dict]:
    """H1-Trend = Schluss über EMA50 (H1). Bullische H1-FVG: Hoch[i-2] < Tief[i]. Betritt der Kurs die
    jüngste unberührte FVG in Trendrichtung (ab 9:00 MEZ = 3:00 NY), sucht M5 einen Sweep (Tief unter dem
    tiefsten Tief der 6 Kerzen davor) und danach einen BOS (Schluss über dem höchsten Hoch seit dem Sweep-
    Beginn, binnen 12 Kerzen) -> Long zum nächsten Open. Stop: Sweep-Tief. Ziel: höchstes Hoch der
    H1-Bewegung seit der FVG ("Range High"), mind. 1R. Short spiegelbildlich. Die M1-Ebene entfällt."""
    ema = pd.Series(b60.c).ewm(span=50, adjust=False).mean().to_numpy()
    h1_t = b60.t
    fvgs = []  # (fertig_ab_zeit, dir, top, bottom, h1_index)
    for i in range(2, b60.n):
        if b60.h[i - 2] < b60.l[i]:
            fvgs.append((h1_t.iloc[i] + pd.Timedelta(hours=1), 1, b60.l[i], b60.h[i - 2], i))
        elif b60.l[i - 2] > b60.h[i]:
            fvgs.append((h1_t.iloc[i] + pd.Timedelta(hours=1), -1, b60.l[i - 2], b60.h[i], i))
    trend = pd.Series(np.sign(b60.c - ema), index=h1_t + pd.Timedelta(hours=1)).reindex(b5.t, method="ffill").fillna(0).to_numpy()
    out, busy, fi = [], -1, 0
    active = []
    used = set()
    for k in range(10, b5.n - 1):
        while fi < len(fvgs) and fvgs[fi][0] <= b5.t.iloc[k]:
            active.append(fvgs[fi])
            fi += 1
        active = active[-10:]
        if k <= busy or b5.ny_min[k] < 180 or b5.ny_min[k] >= 16 * 60:
            continue
        d = int(trend[k])
        if d == 0:
            continue
        zone = next((z for z in reversed(active) if z[1] == d and z[4] not in used), None)
        if zone is None:
            continue
        _, _, top, bot, zi = zone
        inside = (b5.l[k] <= top and b5.h[k] >= bot)
        if not inside:
            continue
        ref = b5.l[k - 6:k].min() if d == 1 else b5.h[k - 6:k].max()
        if not ((b5.l[k] < ref) if d == 1 else (b5.h[k] > ref)):
            continue
        used.add(zi)
        ext, start = (b5.l[k], b5.h[k - 6:k + 1].max()) if d == 1 else (b5.h[k], b5.l[k - 6:k + 1].min())
        for j in range(k + 1, min(k + 13, b5.n - 1)):
            ext = min(ext, b5.l[j]) if d == 1 else max(ext, b5.h[j])
            if (b5.c[j] - start) * d > 0:
                # nur FERTIGE H1-Kerzen (Ende <= Zeitpunkt der Sweep-Kerze), sonst Zukunftswissen im Ziel
                h1_since = (b60.t >= b60.t.iloc[zi]) & (b60.t + pd.Timedelta(hours=1) <= b5.t.iloc[k])
                target = b60.h[h1_since.to_numpy()].max() if d == 1 else b60.l[h1_since.to_numpy()].min()
                e0 = b5.o[j + 1] + (b5.spread[j + 1] if d == 1 else 0)
                if abs(target - e0) >= abs(e0 - ext):
                    t = trade(b5, j + 1, d, e0, ext, target, session_last(b5, j + 1, 17 * 60), "TWIN")
                    if t:
                        out.append(t)
                        busy = j + 1
                break
    return out


# ------------------------------------------------------------------ Auswertung
def summarize(label: str, tr: pd.DataFrame, split) -> str:
    if tr.empty:
        return f"{label:34} 0 Trades"
    r = tr["r"].to_numpy()
    t = r.mean() / (r.std(ddof=1) / np.sqrt(len(r))) if len(r) > 1 and r.std() > 0 else 0.0
    is_r = tr.loc[tr.time < split, "r"]
    oos_r = tr.loc[tr.time >= split, "r"]
    return (f"{label:34} {len(r):5} Tr  Treffer {np.mean(r > 0):5.1%}  Ø {r.mean():+.3f}R  t={t:+5.2f}  "
            f"| IS Ø {is_r.mean() if len(is_r) else 0:+.3f} ({len(is_r)})  OOS Ø {oos_r.mean() if len(oos_r) else 0:+.3f} ({len(oos_r)})")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--symbols", nargs="*")
    p.add_argument("--out", default="research_out/videos")
    args = p.parse_args(argv)
    folder = Path(args.data)
    cfg = load_config(args.config)
    offset_h = json.loads((folder / "meta.json").read_text())["server_offset_seconds"] / 3600
    results: dict[str, list[dict]] = {}
    open_stats = {"1h": [], "2h": [], "16:00": []}

    def add(key, trades):
        results.setdefault(key, []).extend(trades)

    m5_range = None
    for inst, df, spread, src in iter_mt5_files(folder, cfg, args.symbols, "M5"):
        b5 = Bars(df, spread, inst.commission_price, inst.name)
        m5_range = m5_range or (b5.t.iloc[0], b5.t.iloc[-1])
        b15, b60 = b5.resample(15), b5.resample(60)
        d1p = folder / f"{inst.name}_D1.csv"
        d1 = d1_frame(d1p, offset_h) if d1p.exists() else None
        ema60 = pd.Series(b60.c).ewm(span=50, adjust=False).mean()
        slope = ema60.diff(5)
        bias60 = pd.Series(np.where((b60.c > ema60) & (slope > 0), 1, np.where((b60.c < ema60) & (slope < 0), -1, 0)),
                           index=b60.t + pd.Timedelta(hours=1))
        h1_bias = bias60.reindex(b5.t, method="ffill").fillna(0).to_numpy()
        h1_side = pd.Series(np.sign(b60.c - ema60.to_numpy()), index=b60.t + pd.Timedelta(hours=1)) \
            .reindex(b5.t, method="ffill").fillna(0).to_numpy()

        add("V1 Sneaky Pivot (M15)", sneaky_pivot(b15, d1))
        if d1 is not None:
            add("V1+V2 Sneaky + D1-Trend", sneaky_pivot(b15, d1, "trend"))
            add("V1+V2 Sneaky + Trend + ATR", sneaky_pivot(b15, d1, "trend+atr"))
        if inst.name in US_INDICES:
            for kx, v in buy_the_open(b5).items():
                open_stats[kx] += [(inst.name, x) for x in v]
        add("V3 Break&Retest Stop Gegenrand (M5)", break_retest_wide(b5))
        add("V4 Trendlinienbruch (M15)", trendline_break(b15, 96))
        add("V5 PBD (M15)", pbd(b15, 32))
        add("V6 TradingLab (M15)", tradinglab(b15, 96))
        add("V7 TJR Overnight-Sweep (M5)", tjr(b5))
        add("V8a Range-Fakeout Ziel Mitte (M5)", range_fakeout(b5, None, True))
        add("V8a Range-Fakeout + H1-Trend (M5)", range_fakeout(b5, h1_side, True))
        add("V8a Range-Fakeout Ziel Rand (M5)", range_fakeout(b5, None, False))
        add("V8b Trend-Pullback 5R (M5)", pullback_5r(b5, h1_bias))
        add("V9 TwinTraders H1-FVG+M5 (M5)", twin_scalp(b5, b60))
        print(f"{inst.name:7} M5 fertig", flush=True)

    h1_range = None
    for inst, df, spread, src in iter_mt5_files(folder, cfg, args.symbols, "H1"):
        per_month = df.groupby(df["time"].dt.strftime("%Y-%m"))["time"].transform("size").to_numpy()
        dense = np.flatnonzero(per_month >= 300)
        if not len(dense):
            continue
        df, spread = df.iloc[dense[0]:].reset_index(drop=True), spread[dense[0]:]
        b = Bars(df, spread, inst.commission_price, inst.name)
        h1_range = h1_range or (b.t.iloc[0], b.t.iloc[-1])
        add("H1 V4 Trendlinienbruch", trendline_break(b, 120))
        add("H1 V5 PBD", pbd(b, 120))
        add("H1 V6 TradingLab", tradinglab(b, 120))
        print(f"{inst.name:7} H1 fertig", flush=True)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print("\n=== Behauptung Video 2: US-Index zur Eröffnung (9:30 NY) kaufen, ohne Kosten ===")
    for kx, v in open_stats.items():
        x = np.array([y for _, y in v])
        if len(x):
            print(f"  verkaufen {kx:6}: {len(x)} Tage, Gewinntage {np.mean(x > 0):.1%}, Ø {x.mean() * 100:+.3f} %")
    print("\n=== Strategien (alle Kosten, R je Trade) ===")
    for key, trades in results.items():
        tr = pd.DataFrame(trades)
        if tr.empty:
            print(f"{key:34} 0 Trades")
            continue
        tr.to_csv(out / (re.sub(r"[^A-Za-z0-9]+", "_", key).strip("_") + ".csv"), index=False)
        rng = h1_range if key.startswith("H1") else m5_range
        split = rng[0] + (rng[1] - rng[0]) * 2 / 3
        print(summarize(key, tr, split))
        us = tr[tr.symbol.isin(US_INDICES)]
        if len(us) and len(us) != len(tr):
            print(summarize("   nur US-Indizes", us, split))


if __name__ == "__main__":
    main()
