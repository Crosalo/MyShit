"""ICT/SMC-Einstiegsmodell aus dem Video "Die langweiligste Trading-Strategie", mechanisch auf H1.

Ablauf (Short; Long spiegelbildlich), alle Regeln vor dem Test festgelegt:
1. Swing-Punkte: Hoch/Tief mit je 3 niedrigeren/höheren Kerzen links und rechts (bestätigt 3 Kerzen später).
2. Liquidity Sweep: Kerze sticht über das letzte bestätigte Swing-Hoch und schließt wieder darunter.
3. Break of Structure: innerhalb von 24 Kerzen schließt eine Kerze unter dem letzten Swing-Tief vor dem Sweep.
   Schließt vorher eine Kerze über dem Swing-Hoch, ist das Setup ungültig.
4. Fair Value Gap: letzte bärische Lücke (Tief[m-2] > Hoch[m]) zwischen Sweep und BOS.
   Einstieg: Sell-Limit an der Unterkante der Lücke, 24 Kerzen gültig.
5. Stop: Hoch des Sweeps. Ziel: nächstes bestätigtes Swing-Tief unter dem gebrochenen Tief
   (Liquidität), sonst 2R. Ziel unter 1R -> kein Trade.
6. Ausstieg spätestens nach 72 Kerzen oder Freitag 20:00 UTC. Treffen Stop und Ziel dieselbe Kerze: Stop.

Filter (Video: Richtung aus höherem Zeitrahmen, dazu Saisonalität):
    HTF    = Long nur über, Short nur unter der EMA50 auf D1 (Vortag)
    SAISON = nur in Richtung eines aktiven Saisonfensters aus research.seasonal (Walk-Forward)

    python -m research.ict --data "<MQL5>/Files/m1export"
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from bot.config import load_config
from .engine import stats
from .mt5_files import iter_mt5_files, server_epoch_to_utc

PIVOT = 3
SETUP_BARS = 24
ORDER_BARS = 24
MAX_HOLD = 72
TARGET_LOOKBACK = 300
MIN_RR = 1.0
FALLBACK_RR = 2.0


def pivots(h: np.ndarray, l: np.ndarray, k: int = PIVOT) -> tuple[np.ndarray, np.ndarray]:
    n = len(h)
    ph, pl = np.zeros(n, bool), np.zeros(n, bool)
    for i in range(k, n - k):
        win_h, win_l = h[i - k:i + k + 1], l[i - k:i + k + 1]
        ph[i] = h[i] == win_h.max() and (win_h == h[i]).sum() == 1
        pl[i] = l[i] == win_l.min() and (win_l == l[i]).sum() == 1
    return ph, pl


def find_setups(o, h, l, c, direction: int) -> list[dict]:
    """Setups einer Richtung. Für Long werden die Kurse gespiegelt, damit nur eine Logik nötig ist."""
    if direction == 1:  # Long = Short-Logik auf gespiegelten Kursen
        o, h, l, c = -o, -l, -h, -c
    n = len(c)
    ph, pl = pivots(h, l)
    setups = []
    last_sh = last_sl = -1  # Index des letzten BESTÄTIGTEN Swing-Hochs/-Tiefs
    swept_sh = -1
    sl_hist: list[int] = []
    i = PIVOT
    while i < n:
        j = i - PIVOT  # Pivot bei j ist ab Kerze i bestätigt
        if j >= 0 and ph[j]:
            last_sh = j
        if j >= 0 and pl[j]:
            last_sl = j
            sl_hist.append(j)
        if last_sh >= 0 and last_sl >= 0 and last_sh != swept_sh and h[i] > h[last_sh] and c[i] < h[last_sh]:
            swept_sh = last_sh
            sh_price, ref_low = h[last_sh], l[last_sl]
            sweep_high, bos = h[i], -1
            for k in range(i + 1, min(i + 1 + SETUP_BARS, n)):
                if c[k] > sh_price:
                    break
                sweep_high = max(sweep_high, h[k])
                if c[k] < ref_low:
                    bos = k
                    break
            if bos > 0:
                fvg = [m for m in range(i + 2, bos + 1) if l[m - 2] > h[m]]
                if fvg:
                    m = fvg[-1]
                    entry, stop = h[m], sweep_high
                    risk = stop - entry
                    lows = [l[s] for s in sl_hist if s >= bos - TARGET_LOOKBACK and s + PIVOT <= bos and l[s] < ref_low]
                    target = max(lows) if lows else entry - FALLBACK_RR * risk
                    if risk > 0 and (entry - target) >= MIN_RR * risk:
                        setups.append({"bar": bos, "entry": entry, "stop": stop, "target": target})
        i += 1
    if direction == 1:
        for s in setups:
            s["entry"], s["stop"], s["target"] = -s["entry"], -s["stop"], -s["target"]
    for s in setups:
        s["dir"] = direction
    return setups


def simulate(df: pd.DataFrame, spread: np.ndarray, commission: float, setups: list[dict]) -> pd.DataFrame:
    """Limit-Einstieg, Stop/Ziel auf Bid-Kerzen; Short zahlt den Spread beim Rückkauf (Ask)."""
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    t = df["time"]
    friday_late = ((t.dt.weekday == 4) & (t.dt.hour >= 20)).to_numpy() | (t.dt.weekday >= 5).to_numpy()
    n = len(c)
    trades, busy_until = [], {1: -1, -1: -1}
    for s in sorted(setups, key=lambda x: x["bar"]):
        d, b = s["dir"], s["bar"]
        if b <= busy_until[d]:
            continue
        entry, stop, target = s["entry"], s["stop"], s["target"]
        risk = abs(entry - stop)
        fill = -1
        for k in range(b + 1, min(b + 1 + ORDER_BARS, n)):
            ask_h, ask_l = h[k] + spread[k], l[k] + spread[k]
            if d == -1:
                if l[k] <= target:  # Ziel ohne uns erreicht -> Order streichen
                    break
                if h[k] >= entry:
                    fill = k
                    break
            else:
                if h[k] >= target:
                    break
                if ask_l <= entry:
                    fill = k
                    break
        if fill < 0:
            continue
        exit_px, reason, k = None, "", fill
        while k < n:
            ask_h, ask_l = h[k] + spread[k], l[k] + spread[k]
            if d == -1:
                if ask_h >= stop:
                    exit_px, reason = stop, "SL"
                elif k > fill and ask_l <= target:
                    exit_px, reason = target, "TP"
            else:
                if l[k] <= stop:
                    exit_px, reason = stop, "SL"
                elif k > fill and h[k] >= target:
                    exit_px, reason = target, "TP"
            if exit_px is None and (k - fill >= MAX_HOLD or friday_late[k]):
                exit_px, reason = (c[k] + spread[k]) if d == -1 else c[k], "TIME"
            if exit_px is not None:
                break
            k += 1
        if exit_px is None:
            break
        pnl = (exit_px - entry) * d - commission
        trades.append({"time": t.iloc[fill], "dir": d, "entry": entry, "exit": exit_px, "reason": reason,
                       "r": pnl / risk, "bars": k - fill})
        busy_until[d] = k
    return pd.DataFrame(trades)


def htf_bias(d1_path: Path, times: pd.Series, offset_h: float) -> np.ndarray:
    """+1/-1 je H1-Kerze: Schlusskurs des letzten fertigen D1-Tages über/unter EMA50."""
    d1 = pd.read_csv(d1_path)
    close = d1["close"].astype(float)
    ema50 = close.ewm(span=50, adjust=False).mean()
    # D1-Kerze (Serverdatum) ist am Folgetag 00:00 Serverzeit fertig
    ready = server_epoch_to_utc(d1["time"] + 86400, offset_h)
    s = pd.Series(np.sign(close - ema50).to_numpy(), index=ready)
    s = s[s.index.notna()].sort_index()
    return s.reindex(times, method="ffill").fillna(0).to_numpy()


def seasonal_bias(seasonal_csv: Path, symbol: str, times: pd.Series) -> np.ndarray:
    out = np.zeros(len(times))
    if not seasonal_csv.exists():
        return out
    w = pd.read_csv(seasonal_csv, parse_dates=["start"])
    w = w[w.symbol == symbol]
    tt = times.dt.tz_localize(None)
    for _, row in w.iterrows():
        end = row["start"] + pd.Timedelta(days=int(row["length"]))
        out[((tt >= row["start"]) & (tt < end)).to_numpy()] = row["dir"]
    return out


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--symbols", nargs="*")
    p.add_argument("--seasonal", default="research_out/seasonal/trades.csv")
    p.add_argument("--out", default="research_out/ict")
    args = p.parse_args(argv)
    folder = Path(args.data)
    offset_h = json.loads((folder / "meta.json").read_text())["server_offset_seconds"] / 3600
    variants = {"ICT": [], "ICT+HTF": [], "ICT+HTF+SAISON": []}
    for inst, df, spread, src in iter_mt5_files(folder, load_config(args.config), args.symbols, "H1"):
        # Ältere Broker-Historie hat oft nur eine Kerze pro Tag: erst ab dem ersten vollen H1-Monat
        per_month = df.groupby(df["time"].dt.strftime("%Y-%m"))["time"].transform("size").to_numpy()
        dense = np.flatnonzero(per_month >= 300)
        if not len(dense):
            continue
        df, spread = df.iloc[dense[0]:].reset_index(drop=True), spread[dense[0]:]
        o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
        setups = find_setups(o, h, l, c, -1) + find_setups(o, h, l, c, 1)
        htf = htf_bias(folder / f"{inst.name}_D1.csv", df["time"], offset_h) \
            if (folder / f"{inst.name}_D1.csv").exists() else np.zeros(len(df))
        sea = seasonal_bias(Path(args.seasonal), inst.name, df["time"])
        filt = {
            "ICT": setups,
            "ICT+HTF": [s for s in setups if htf[s["bar"]] == s["dir"]],
            "ICT+HTF+SAISON": [s for s in setups if htf[s["bar"]] == s["dir"] and sea[s["bar"]] == s["dir"]],
        }
        line = [f"{inst.name:7} {len(df):>6} H1"]
        for name, ss in filt.items():
            tr = simulate(df, spread, inst.commission_price, ss)
            if len(tr):
                tr["symbol"] = inst.name
                variants[name].append(tr)
            line.append(f"{name} {len(tr)} Ø{tr['r'].mean() if len(tr) else 0:+.2f}R")
        print(" | ".join(line), flush=True)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print()
    for name, parts in variants.items():
        if not parts:
            continue
        tr = pd.concat(parts, ignore_index=True).sort_values("time")
        tr.to_csv(out / f"trades_{name}.csv", index=False)
        t0, t1 = tr["time"].min(), tr["time"].max()
        split = t0 + (t1 - t0) * 2 / 3
        months = lambda a, b: (b - a).days / 30.44
        is_s = stats(tr.loc[tr.time < split, "r"].to_numpy(), months(t0, split))
        oos_s = stats(tr.loc[tr.time >= split, "r"].to_numpy(), months(split, t1))
        print(f"{name:15} IS bis {split.date()}: {is_s}")
        print(f"{'':15} OOS:            {oos_s}")
        long_r, short_r = tr.loc[tr.dir == 1, "r"], tr.loc[tr.dir == -1, "r"]
        print(f"{'':15} Long {len(long_r)} Ø{long_r.mean():+.3f}R | Short {len(short_r)} Ø{short_r.mean():+.3f}R")
        yr = tr.groupby(tr.time.dt.year)["r"].agg(["size", "mean"]).round(3)
        print(f"{'':15} je Jahr Ø R: " + ", ".join(f"{y}:{m:+.2f}({n})" for y, (n, m) in yr.iterrows()))


if __name__ == "__main__":
    main()
