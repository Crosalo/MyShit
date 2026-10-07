"""Ereignisgesteuerter M1-Backtest, Ergebnis in R (Vielfache des Risikos pro Trade).

Bewusst pessimistische Annahmen:
- Kerzen sind Bid-Kurse. Long: Einstieg zum Ask (Bid + Spread), Ausstieg zum Bid.
  Short: Einstieg zum Bid, Ausstieg zum Ask.
- Signal auf dem Schlusskurs von Kerze s, Einstieg zum Eröffnungskurs von Kerze s+1.
- Berühren SL und TP dieselbe Kerze, zählt der SL. Kurslücken über den SL: Füllung zum
  schlechteren Eröffnungskurs.
- Kein Trade, wenn Spread + Kommission mehr als 1/min_cost_ratio des Risikos ausmachen.
- Zwangsausstieg vor dem Tageswechsel (20:55 UTC) und vor dem Wochenende.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class Signals:
    long: np.ndarray  # bool
    short: np.ndarray  # bool
    sl_dist: np.ndarray  # Preis-Einheiten
    tp_dist: np.ndarray  # Preis-Einheiten (nan = kein TP)
    max_hold: int  # Kerzen


def force_exit_mask(times: pd.Series) -> np.ndarray:
    tod = (times.dt.hour * 60 + times.dt.minute).to_numpy()
    wd = times.dt.weekday.to_numpy()
    rollover = (tod >= 20 * 60 + 55) & (tod < 22 * 60 + 10)
    weekend = ((wd == 4) & (tod >= 20 * 60 + 30)) | (wd == 5) | ((wd == 6) & (tod < 22 * 60 + 10))
    return rollover | weekend


def simulate(o, h, l, c, spread, force_exit, sig: Signals, commission_price: float,
             min_cost_ratio: float = 5.0) -> tuple[pd.DataFrame, int]:
    n = len(o)
    idx = np.flatnonzero(sig.long | sig.short)
    rows = []
    skipped_cost = 0
    busy_until = -1
    for s in idx:
        if s <= busy_until:
            continue
        e = s + 1
        if e >= n or force_exit[e]:
            continue
        sd, td = sig.sl_dist[s], sig.tp_dist[s]
        if not np.isfinite(sd) or sd <= 0:
            continue
        if sd < min_cost_ratio * (spread[e] + commission_price):
            skipped_cost += 1
            continue
        is_long = bool(sig.long[s])
        if is_long:
            entry = o[e] + spread[e]
            sl, tp = entry - sd, entry + td
        else:
            entry = o[e]
            sl, tp = entry + sd, entry - td

        last = min(n - 1, e + sig.max_hold - 1)
        forced_at = -1
        fe = np.flatnonzero(force_exit[e + 1:last + 1])
        if len(fe):
            forced_at = e + 1 + fe[0]
            last = forced_at - 1
        w = slice(e, last + 1)
        if is_long:
            hit_sl = l[w] <= sl
            hit_tp = h[w] >= tp if np.isfinite(td) else np.zeros(last - e + 1, bool)
        else:
            hit_sl = h[w] + spread[w] >= sl
            hit_tp = l[w] + spread[w] <= tp if np.isfinite(td) else np.zeros(last - e + 1, bool)
        k_sl = e + int(np.argmax(hit_sl)) if hit_sl.any() else n
        k_tp = e + int(np.argmax(hit_tp)) if hit_tp.any() else n

        if k_sl <= k_tp and k_sl < n:
            k, reason = k_sl, "SL"
            if is_long:
                exit_ = min(o[k], sl) if k > e else sl
            else:
                exit_ = max(o[k] + spread[k], sl) if k > e else sl
        elif k_tp < n:
            k, reason, exit_ = k_tp, "TP", tp
        elif forced_at >= 0:
            k, reason = forced_at, "Zwang"
            exit_ = o[k] if is_long else o[k] + spread[k]
        else:
            k, reason = last, "Zeit"
            exit_ = c[k] if is_long else c[k] + spread[k]

        direction = 1.0 if is_long else -1.0
        pnl = (exit_ - entry) * direction - commission_price
        rows.append((s, e, k, int(direction), entry, exit_, sd, pnl / sd, reason))
        busy_until = k
    trades = pd.DataFrame(rows, columns=["signal", "entry_bar", "exit_bar", "dir", "entry",
                                         "exit", "sl_dist", "r", "reason"])
    return trades, skipped_cost


def stats(r: np.ndarray, months: float) -> dict:
    n = len(r)
    if n == 0:
        return {"trades": 0, "trades_pm": 0.0, "win_pct": 0.0, "avg_r": 0.0, "t": 0.0,
                "pf": 0.0, "total_r": 0.0, "max_dd_r": 0.0}
    eq = np.cumsum(r)
    dd = float(np.max(np.maximum.accumulate(np.concatenate([[0.0], eq])) - np.concatenate([[0.0], eq])))
    std = r.std(ddof=1) if n > 1 else 0.0
    pos, neg = r[r > 0].sum(), -r[r < 0].sum()
    return {
        "trades": n,
        "trades_pm": round(n / months, 1) if months else 0.0,
        "win_pct": round(float((r > 0).mean() * 100), 1),
        "avg_r": round(float(r.mean()), 3),
        "t": round(float(r.mean() / (std / np.sqrt(n))), 2) if std > 0 else 0.0,
        "pf": round(float(pos / neg), 2) if neg > 0 else float("inf"),
        "total_r": round(float(eq[-1]), 1),
        "max_dd_r": round(dd, 1),
    }
