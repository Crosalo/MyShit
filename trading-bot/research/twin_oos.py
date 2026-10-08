"""Out-of-Sample-Prüfung der einzigen offenen Spur: TwinTraders-Scalp (research.videos.twin_scalp) auf M1.

Bisher angeschaut: nur Juli-Oktober 2026 (dort +0,45R auf US-Indizes, 77 Trades). Hier zählen
ausschließlich Daten VOR dem 29.06.2026, die vorher niemand gesehen hat. Regel unverändert.
Vorab festgelegt: bestanden, wenn gesamt Ø R > 0 mit t >= 2 UND mindestens 2 von 3 Indizes positiv.

    python -m research.twin_oos --data "<MQL5>/Files/m1long"
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from bot.config import load_config
from . import videos
from .mt5_files import iter_mt5_files

CUTOFF = pd.Timestamp("2026-06-29", tz="UTC")
MIN_BARS_PER_MONTH = 15000  # ältere Broker-Historie ist teils lückenhaft


def tstat(r):
    return r.mean() / (r.std(ddof=1) / np.sqrt(len(r))) if len(r) > 2 and r.std() > 0 else 0.0


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--config", default="config.yaml")
    args = p.parse_args(argv)
    rows = []
    for inst, df, spread, src in iter_mt5_files(Path(args.data), load_config(args.config), None, "M1"):
        keep = (df["time"] < CUTOFF).to_numpy()
        df, spread = df[keep].reset_index(drop=True), spread[keep]
        per_month = df.groupby(df["time"].dt.strftime("%Y-%m"))["time"].transform("size").to_numpy()
        dense = np.flatnonzero(per_month >= MIN_BARS_PER_MONTH)
        if not len(dense):
            print(f"{inst.name}: keine dichten M1-Daten")
            continue
        df, spread = df.iloc[dense[0]:].reset_index(drop=True), spread[dense[0]:]
        b = videos.Bars(df, spread, inst.commission_price, inst.name)
        tr = videos.twin_scalp(b, b.resample(60))
        print(f"{inst.name:6} M1 {b.t.iloc[0].date()} bis {b.t.iloc[-1].date()}: {len(tr)} Trades", flush=True)
        rows += tr
    t = pd.DataFrame(rows)
    if t.empty:
        print("Keine Trades.")
        return
    r = t["r"].to_numpy()
    print(f"\nGESAMT  {len(r)} Trades  Treffer {np.mean(r > 0):.1%}  Ø {r.mean():+.3f}R  t={tstat(r):+.2f}")
    pos = 0
    for s, g in t.groupby("symbol"):
        x = g["r"].to_numpy()
        pos += x.mean() > 0
        print(f"  {s:6} {len(x):5} Trades  Ø {x.mean():+.3f}R  t={tstat(x):+.2f}")
    years = pd.to_datetime(t["time"]).dt.year
    print("  je Jahr: " + ", ".join(f"{y}: {g.r.mean():+.2f} ({len(g)})" for y, g in t.groupby(years)))
    ok = r.mean() > 0 and tstat(r) >= 2 and pos >= 2
    print(f"\nURTEIL (vorab festgelegt): {'BESTANDEN' if ok else 'NICHT BESTANDEN'}")


if __name__ == "__main__":
    main()
