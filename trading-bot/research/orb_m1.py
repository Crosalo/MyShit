"""ORB "Stocks in Play": dieselben Trades wie in research.orb_stocks (Auswahl aus M5, 70 Aktien),
aber Einstieg, Stop und Ausstieg auf M1 nachgerechnet. Mit M1 wird die Unschärfe in der
Einstiegskerze (pessimistisch vs. optimistisch) viel kleiner; die Wahrheit liegt dazwischen.

    python -m research.orb_m1 --m5 "<MQL5>/Files/stocks" --m1 "<MQL5>/Files/orbm1"
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .mt5_files import server_epoch_to_utc
from .orb_stocks import SPLIT, load_days, simulate


def load_m1_days(csv: Path, spec: dict, offset_h: float) -> dict:
    d = pd.read_csv(csv)
    t = server_epoch_to_utc(d["time"], offset_h).dt.tz_convert("America/New_York")
    d["day"], d["m"] = t.dt.date, t.dt.hour * 60 + t.dt.minute
    d = d.dropna(subset=["day"])
    pt = spec["point"]
    d["sp"] = np.maximum(d["spread"] * pt, d["spread"].mean() * pt)
    d = d[(d.m >= 574) & (d.m < 960)]  # ab 9:34: Index 0 wird in simulate() übersprungen, Einstieg ab 9:35
    return {day: g[["m", "open", "high", "low", "close", "sp"]].to_numpy() for day, g in d.groupby("day")}


def tstat(x):
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else 0.0


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--m5", required=True)
    p.add_argument("--m1", required=True)
    p.add_argument("--trades", default="research_out/orb_stocks")
    args = p.parse_args(argv)
    m5, m1 = Path(args.m5), Path(args.m1)
    off5 = json.loads((m5 / "meta.json").read_text())["server_offset_seconds"] / 3600
    off1 = json.loads((m1 / "meta.json").read_text())["server_offset_seconds"] / 3600
    rng = np.random.default_rng(11)
    for top_n in (5, 10, 20):
        tr = pd.read_csv(Path(args.trades) / f"trades_top{top_n}.csv", parse_dates=["day"])
        tr["day"] = tr["day"].dt.date
        rows = []
        for sym, g in tr.groupby("symbol"):
            f1 = next(iter(m1.glob(f"{sym}_M1.csv*")), None)
            f5 = next(iter(m5.glob(f"{sym}_M5.csv*")), None)
            if f1 is None or f5 is None or f1.stat().st_size == 0:
                continue
            spec = json.loads((m1 / f"{sym}_spec.json").read_text())
            days5 = load_days(f5, spec, off5).set_index("day")
            days1 = load_m1_days(f1, spec, off1)
            for t in g.itertuples():
                if t.day not in days1 or t.day not in days5.index:
                    continue
                row5 = days5.loc[t.day]
                row = pd.Series({"bars": days1[t.day], "or_h": row5.or_h, "or_l": row5.or_l, "atr": row5.atr})
                res = simulate(row, t.dir)
                rnd = simulate(row, int(rng.choice([-1, 1])))
                if res is None:
                    continue
                rows.append({"day": t.day, "symbol": sym, "m5_pess": t.r_pess, "m5_opt": t.r_opt,
                             "m1_pess": res[0], "m1_opt": res[1], "rnd_mid": np.mean(rnd) if rnd else np.nan})
        r = pd.DataFrame(rows)
        if r.empty:
            continue
        r["m1_mid"] = (r.m1_pess + r.m1_opt) / 2
        print(f"\n=== TOP {top_n}: {len(r)} Trades in {r.symbol.nunique()} Aktien mit M1-Daten ===")
        for label, part in (("gesamt", r), ("bis 2024", r[r.day < SPLIT]), ("2025-26", r[r.day >= SPLIT])):
            line = f"{label:9}"
            for col in ("m5_pess", "m5_opt", "m1_pess", "m1_opt", "m1_mid"):
                x = part[col].to_numpy()
                line += f" | {col} {x.mean():+.3f}" + (f" (t={tstat(x):+.2f})" if col == "m1_mid" else "")
            line += f" | Zufall M1 {part.rnd_mid.mean():+.3f}"
            print(line)


if __name__ == "__main__":
    main()
