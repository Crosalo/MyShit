"""Zeitrahmen-Sweep: alle Strategien auf allen kurzen Zeitrahmen: M1, M2, M3 (aus M1-Daten, 3 Monate) und
M5, M10, M15, M30 (aus M5-Daten, 1 Jahr). 31 Märkte, alle Kosten.

Haltedauer und Fenster der Video-Modelle sind in ZEIT festgelegt (8 h halten, 4 h Range), damit die
Zeitrahmen vergleichbar sind. Die 6 Cloud-Strategien und Break & Retest laufen über research.run.evaluate.
Bewertung wie in research.combos: Auswahl im Lernzeitraum (>= 50 Trades, Ø R > 0, t >= 2,5),
Bestätigung im Prüfzeitraum (>= 20 Trades, Ø R > 0, t >= 1,5).

    python -m research.tf_sweep --data "<MQL5>/Files/m1export"
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from bot.config import load_config
from . import ict, videos
from .break_retest import run_trades as break_retest_trades
from .mt5_files import iter_mt5_files
from .run import evaluate

PLAN = {"M1": ("M1", [1, 2, 3]), "M5": ("M5", [5, 10, 15, 30])}
US_INDICES = videos.US_INDICES
IS_MIN, IS_T, OOS_MIN, OOS_T = 50, 2.5, 20, 1.5


def to_df(b: videos.Bars) -> pd.DataFrame:
    return pd.DataFrame({"time": b.t, "open": b.o, "high": b.h, "low": b.l, "close": b.c})


def run_tf(inst, b: videos.Bars, b60: videos.Bars, tf: int, split) -> list[dict]:
    hold = max(2, 480 // tf)  # 8 Stunden
    win = max(6, 240 // tf)  # 4 Stunden Range
    ema = pd.Series(b60.c).ewm(span=50, adjust=False).mean()
    slope = ema.diff(5)
    bias = pd.Series(np.where((b60.c > ema) & (slope > 0), 1, np.where((b60.c < ema) & (slope < 0), -1, 0)),
                     index=b60.t + pd.Timedelta(hours=1)).reindex(b.t, method="ffill").fillna(0).to_numpy()
    models = {
        "Sneaky Pivot": videos.sneaky_pivot(b, None),
        "BR Stop Gegenrand": videos.break_retest_wide(b),
        "Trendlinie": videos.trendline_break(b, hold),
        "PBD": videos.pbd(b, hold),
        "TradingLab": videos.tradinglab(b, hold),
        "TJR Sweep": videos.tjr(b),
        "Range-Fakeout": videos.range_fakeout(b, None, True, win, hold),
        "Pullback 5R": videos.pullback_5r(b, bias, hold),
        "TwinTraders": videos.twin_scalp(b, b60),
    }
    df = to_df(b)
    setups = ict.find_setups(b.o, b.h, b.l, b.c, -1) + ict.find_setups(b.o, b.h, b.l, b.c, 1)
    it = ict.simulate(df, b.spread, inst.commission_price, setups)
    models["ICT"] = it.to_dict("records") if len(it) else []
    out = []
    for name, tr in models.items():
        for t in tr:
            out.append({"strategy": name, "symbol": inst.name, "time": t["time"], "dir": t["dir"], "r": t["r"]})
    _, trades = evaluate(inst, df, b.spread, "", split, 19.0)  # tf=1: Signale und Ausstiege auf df selbst
    br = break_retest_trades(inst, df, b.spread)
    if len(br):
        trades.append(br)
    for t in trades:
        for row in t[["strategy", "time", "dir", "r"]].itertuples(index=False):
            out.append({"strategy": row.strategy, "symbol": inst.name, "time": row.time, "dir": row.dir, "r": row.r})
    for o in out:
        o["tf"] = f"M{tf}"
    return out


def tstat(r):
    return float(r.mean() / (r.std(ddof=1) / np.sqrt(len(r)))) if len(r) > 2 and r.std() > 0 else 0.0


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--symbols", nargs="*")
    p.add_argument("--out", default="research_out/timeframes")
    args = p.parse_args(argv)
    folder, cfg = Path(args.data), load_config(args.config)
    rows, splits = [], {}
    for base, (src_tf, tfs) in PLAN.items():
        split = None
        for inst, df, spread, src in iter_mt5_files(folder, cfg, args.symbols, src_tf):
            b0 = videos.Bars(df, spread, inst.commission_price, inst.name)
            if split is None:
                split = b0.t.iloc[0] + (b0.t.iloc[-1] - b0.t.iloc[0]) * 2 / 3
                for tf in tfs:
                    splits[f"M{tf}"] = split
            b60 = b0.resample(60)
            for tf in tfs:
                b = b0 if tf == int(src_tf[1:]) else b0.resample(tf)
                rows += run_tf(inst, b, b60, tf, split)
            print(f"{inst.name:7} {base}-Basis fertig", flush=True)
    tr = pd.DataFrame(rows)
    tr["time"] = pd.to_datetime(tr["time"], utc=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tr.to_csv(out / "trades.csv.gz", index=False)

    res = []
    for group, g0 in (("alle", tr), ("US-Idx", tr[tr.symbol.isin(US_INDICES)])):
        for (strat, tf), g in g0.groupby(["strategy", "tf"]):
            sp = splits[tf]
            is_r, oos_r = g.loc[g.time < sp, "r"].to_numpy(), g.loc[g.time >= sp, "r"].to_numpy()
            res.append({"group": group, "strategy": strat, "tf": tf, "n": len(g), "avg": g.r.mean(), "t": tstat(g.r.to_numpy()),
                        "is_n": len(is_r), "is_avg": is_r.mean() if len(is_r) else np.nan, "is_t": tstat(is_r),
                        "oos_n": len(oos_r), "oos_avg": oos_r.mean() if len(oos_r) else np.nan, "oos_t": tstat(oos_r)})
    res = pd.DataFrame(res)
    res.to_csv(out / "summary.csv", index=False)
    order = ["M1", "M2", "M3", "M5", "M10", "M15", "M30"]
    for group in ("alle", "US-Idx"):
        piv = res[res.group == group].pivot(index="strategy", columns="tf", values="avg").reindex(columns=order)
        print(f"\n=== Ø R je Trade nach Kosten, {group} (M1-M3: 3 Monate, M5-M30: 1 Jahr) ===")
        print(piv.round(3).to_string())
    tested = res[res.is_n >= IS_MIN]
    sel = tested[(tested.is_avg > 0) & (tested.is_t >= IS_T)]
    ok = sel[(sel.oos_n >= OOS_MIN) & (sel.oos_avg > 0) & (sel.oos_t >= OOS_T)]
    print(f"\nZellen mit >= {IS_MIN} Trades im Lernzeitraum: {len(tested)}")
    print(f"im Lernzeitraum ausgewählt (t >= {IS_T}): {len(sel)}   (reiner Zufall: ca. {0.006 * len(tested):.0f})")
    print(f"davon im Prüfzeitraum bestanden: {len(ok)}")
    cols = ["group", "strategy", "tf", "is_n", "is_avg", "is_t", "oos_n", "oos_avg", "oos_t"]
    print("\nBeste 12 im Lernzeitraum:")
    print(tested.sort_values("is_t", ascending=False).head(12)[cols].round(3).to_string(index=False))
    if len(ok):
        print("\nBestanden:")
        print(ok[cols].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
