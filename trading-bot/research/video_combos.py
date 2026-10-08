"""Kombinationen der Video-Strategien: jeder Einstieg x bis zu 3 Filter aus den anderen Videos.

Ablauf (vor dem Test festgelegt):
1. Alle Einstiegsmodelle laufen wie in research.videos / research.ict (eigene Ausstiege, alle Kosten).
2. Je Trade werden Filter-Merkmale zum Einstiegszeitpunkt bestimmt (nur Daten, die da schon bekannt waren).
3. Jede Kombination wird NUR im Lernzeitraum (erste 2/3) bewertet. Auswahl: >= 50 Trades, Ø R > 0, t >= 2,5.
4. Die Ausgewählten müssen im Prüfzeitraum (letztes 1/3) bestehen: >= 20 Trades, Ø R > 0, t >= 1,5.
Viele Kombinationen = viele Zufallstreffer im Lernzeitraum. Entscheidend ist der Prüfzeitraum.

Filter:
    D1TREND   Richtung = Vortagesschluss über/unter SMA50 (The Rumers "3R Rule")
    H1TREND   Richtung = letzter H1-Schluss über/unter EMA50 (TwinTraders, Trading.de)
    SEASON    aktives Saisonfenster in dieselbe Richtung (TwinTraders, aus research.seasonal)
    NYOPEN    Einstieg 9:30-11:30 New York (Scarface, TJR, Dennis Trades)
    ZONE      Long im unteren, Short im oberen Drittel der Vortagesspanne oder darüber hinaus (The Rumers)
    ATRROOM   Kurs heute noch keine halbe Tages-ATR vom Tagesopen entfernt (The Rumers "Range")
    CONFL     ein ANDERES Einstiegsmodell gab in den 4 h davor (H1: 24 h) dasselbe Signal

    python -m research.video_combos --data "<MQL5>/Files/m1export"
"""
import argparse
import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from bot.config import load_config
from . import ict, videos
from .mt5_files import iter_mt5_files, server_epoch_to_utc

FILTERS = ("D1TREND", "H1TREND", "SEASON", "NYOPEN", "ZONE", "ATRROOM", "CONFL")
US_INDICES = videos.US_INDICES
IS_MIN, IS_T = 50, 2.5
OOS_MIN, OOS_T = 20, 1.5


def collect(folder: Path, cfg: dict, symbols) -> tuple[pd.DataFrame, pd.DataFrame]:
    intraday, swing = [], []
    for inst, df, spread, src in iter_mt5_files(folder, cfg, symbols, "M5"):
        b5 = videos.Bars(df, spread, inst.commission_price, inst.name)
        b15, b60 = b5.resample(15), b5.resample(60)
        ema60 = pd.Series(b60.c).ewm(span=50, adjust=False).mean()
        slope = ema60.diff(5)
        bias = pd.Series(np.where((b60.c > ema60) & (slope > 0), 1, np.where((b60.c < ema60) & (slope < 0), -1, 0)),
                         index=b60.t + pd.Timedelta(hours=1)).reindex(b5.t, method="ffill").fillna(0).to_numpy()
        models = {
            "SNEAKY": videos.sneaky_pivot(b15, None),
            "BR_WIDE": videos.break_retest_wide(b5),
            "TREND15": videos.trendline_break(b15, 96),
            "PBD15": videos.pbd(b15, 32),
            "TLAB15": videos.tradinglab(b15, 96),
            "TJR": videos.tjr(b5),
            "RANGE": videos.range_fakeout(b5, None, True),
            "PB5R": videos.pullback_5r(b5, bias),
            "TWIN": videos.twin_scalp(b5, b60),
        }
        for name, tr in models.items():
            for t in tr:
                t["model"] = name
            intraday += tr
        print(f"{inst.name:7} M5-Modelle fertig", flush=True)
    for inst, df, spread, src in iter_mt5_files(folder, cfg, symbols, "H1"):
        per_month = df.groupby(df["time"].dt.strftime("%Y-%m"))["time"].transform("size").to_numpy()
        dense = np.flatnonzero(per_month >= 300)
        if not len(dense):
            continue
        df, spread = df.iloc[dense[0]:].reset_index(drop=True), spread[dense[0]:]
        b = videos.Bars(df, spread, inst.commission_price, inst.name)
        models = {"TREND_H1": videos.trendline_break(b, 120), "PBD_H1": videos.pbd(b, 120),
                  "TLAB_H1": videos.tradinglab(b, 120)}
        o, h, l, c = b.o, b.h, b.l, b.c
        setups = ict.find_setups(o, h, l, c, -1) + ict.find_setups(o, h, l, c, 1)
        it = ict.simulate(df, spread, inst.commission_price, setups)
        if len(it):
            it["symbol"] = inst.name
            models["ICT_H1"] = it.to_dict("records")
        for name, tr in models.items():
            for t in tr:
                t["model"] = name
            swing += tr
        print(f"{inst.name:7} H1-Modelle fertig", flush=True)
    return pd.DataFrame(intraday), pd.DataFrame(swing)


def add_features(tr: pd.DataFrame, folder: Path, offset_h: float, confl_hours: int) -> pd.DataFrame:
    tr = tr.sort_values("time").reset_index(drop=True)
    tr["time"] = pd.to_datetime(tr["time"], utc=True)
    for f in FILTERS:
        tr[f] = False
    seasonal = Path("research_out/seasonal/trades.csv")
    sea = pd.read_csv(seasonal, parse_dates=["start"]) if seasonal.exists() else pd.DataFrame()
    parts = []
    for sym, g in tr.groupby("symbol"):
        g = g.copy()
        times, d = g["time"], g["dir"].to_numpy()
        d1p = folder / f"{sym}_D1.csv"
        if d1p.exists():
            d1 = pd.read_csv(d1p)
            start = server_epoch_to_utc(d1["time"], offset_h)
            ready = server_epoch_to_utc(d1["time"] + 86400, offset_h)
            ok =ready.notna().to_numpy() & start.notna().to_numpy()
            d1, start, ready = d1[ok].reset_index(drop=True), start[ok].reset_index(drop=True), ready[ok].reset_index(drop=True)
            prev = d1["close"].shift(1)
            tr_ = np.maximum(d1["high"] - d1["low"], np.maximum((d1["high"] - prev).abs(), (d1["low"] - prev).abs()))
            fin = pd.DataFrame({"sma50": d1["close"].rolling(50).mean().to_numpy(), "close": d1["close"].to_numpy(),
                                "high": d1["high"].to_numpy(), "low": d1["low"].to_numpy(),
                                "atr": tr_.rolling(14).mean().to_numpy()}, index=ready).sort_index()
            done = fin.reindex(times, method="ffill")  # letzter FERTIGER Tag
            today_open = pd.Series(d1["open"].to_numpy(), index=start).sort_index().reindex(times, method="ffill").to_numpy()
            g["D1TREND"] = np.sign(done["close"].to_numpy() - done["sma50"].to_numpy()) == d
            rng = done["high"].to_numpy() - done["low"].to_numpy()
            pos = (g["entry"].to_numpy() - done["low"].to_numpy()) / np.where(rng > 0, rng, np.nan)
            g["ZONE"] = np.where(d == 1, pos <= 1 / 3, pos >= 2 / 3)
            g["ATRROOM"] = np.abs(g["entry"].to_numpy() - today_open) < 0.5 * done["atr"].to_numpy()
        h1p = folder / f"{sym}_H1.csv"
        if h1p.exists():
            h1 = pd.read_csv(h1p)
            ema = h1["close"].ewm(span=50, adjust=False).mean()
            t_ready = server_epoch_to_utc(h1["time"] + 3600, offset_h)
            side = pd.Series(np.sign(h1["close"] - ema).to_numpy(), index=t_ready)
            side = side[side.index.notna()].sort_index()
            side = side[~side.index.duplicated(keep="last")]
            g["H1TREND"] = side.reindex(times, method="ffill").fillna(0).to_numpy() == d
        if not sea.empty:
            s = np.zeros(len(g))
            tt = times.dt.tz_localize(None)
            for _, row in sea[sea.symbol == sym].iterrows():
                end = row["start"] + pd.Timedelta(days=int(row["length"]))
                s[((tt >= row["start"]) & (tt < end)).to_numpy()] = row["dir"]
            g["SEASON"] = s == d
        ny = times.dt.tz_convert("America/New_York")
        m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
        g["NYOPEN"] = (m >= 570) & (m < 690)
        # Bestätigung durch ein anderes Modell, gleiche Richtung, in den confl_hours davor
        conf = np.zeros(len(g), bool)
        tv, mv = times.to_numpy(), g["model"].to_numpy()
        win = np.timedelta64(confl_hours, "h")
        for i in range(len(g)):
            lo = np.searchsorted(tv, tv[i] - win)
            for j in range(lo, i):
                if d[j] == d[i] and mv[j] != mv[i]:
                    conf[i] = True
                    break
        g["CONFL"] = conf
        parts.append(g)
    return pd.concat(parts, ignore_index=True)


def tstat(r: np.ndarray) -> float:
    return float(r.mean() / (r.std(ddof=1) / np.sqrt(len(r)))) if len(r) > 2 and r.std() > 0 else 0.0


def evaluate(tr: pd.DataFrame, group: str) -> pd.DataFrame:
    t0, t1 = tr["time"].min(), tr["time"].max()
    split = t0 + (t1 - t0) * 2 / 3
    rows = []
    for model, g in tr.groupby("model"):
        for k in range(0, 4):
            for combo in combinations(FILTERS, k):
                m = np.ones(len(g), bool)
                for f in combo:
                    m &= g[f].to_numpy()
                sub = g[m]
                is_r = sub.loc[sub.time < split, "r"].to_numpy()
                oos_r = sub.loc[sub.time >= split, "r"].to_numpy()
                rows.append({"group": group, "model": model, "filters": "+".join(combo) or "-",
                             "is_n": len(is_r), "is_avg": is_r.mean() if len(is_r) else np.nan, "is_t": tstat(is_r),
                             "oos_n": len(oos_r), "oos_avg": oos_r.mean() if len(oos_r) else np.nan,
                             "oos_t": tstat(oos_r), "split": split.date()})
    return pd.DataFrame(rows)


def report(res: pd.DataFrame, label: str):
    sel = res[(res.is_n >= IS_MIN) & (res.is_avg > 0) & (res.is_t >= IS_T)]
    ok = sel[(sel.oos_n >= OOS_MIN) & (sel.oos_avg > 0) & (sel.oos_t >= OOS_T)]
    tested = res[res.is_n >= IS_MIN]
    print(f"\n=== {label} (Lernzeitraum bis {res.split.iloc[0]}) ===")
    print(f"Kombinationen mit >= {IS_MIN} Trades im Lernzeitraum: {len(tested)}")
    print(f"im Lernzeitraum ausgewählt (t >= {IS_T}): {len(sel)}   (reiner Zufall: ca. {0.006 * len(tested):.0f})")
    print(f"davon im Prüfzeitraum bestanden: {len(ok)}   (bei Zufall: ca. {0.07 * len(sel):.1f})")
    if len(sel):
        print(f"Ø R der Ausgewählten: Lernzeitraum {sel.is_avg.mean():+.3f}  ->  Prüfzeitraum {sel.oos_avg.mean():+.3f}")
    top = tested.sort_values("is_t", ascending=False).head(12)
    cols = ["group", "model", "filters", "is_n", "is_avg", "is_t", "oos_n", "oos_avg", "oos_t"]
    print("\nBeste 12 im Lernzeitraum und was danach passierte:")
    print(top[cols].round(3).to_string(index=False))
    if len(ok):
        print("\nBestanden:")
        print(ok[cols].round(3).to_string(index=False))


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--symbols", nargs="*")
    p.add_argument("--out", default="research_out/combos")
    args = p.parse_args(argv)
    folder = Path(args.data)
    offset_h = json.loads((folder / "meta.json").read_text())["server_offset_seconds"] / 3600
    intraday, swing = collect(folder, load_config(args.config), args.symbols)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for label, tr, hours in (("M5/M15, 1 Jahr", intraday, 4), ("H1, 2019-2026", swing, 24)):
        if tr.empty:
            continue
        tr = add_features(tr, folder, offset_h, hours)
        tr.to_csv(out / f"trades_{label.split(',')[0].replace('/', '_')}.csv", index=False)
        res = pd.concat([evaluate(tr, "alle"), evaluate(tr[tr.symbol.isin(US_INDICES)], "US-Idx")])
        res.to_csv(out / f"combos_{label.split(',')[0].replace('/', '_')}.csv", index=False)
        report(res, label)


if __name__ == "__main__":
    main()
