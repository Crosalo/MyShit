"""Alle Strategien x alle Märkte testen: Lernzeitraum (IS), Prüfzeitraum (OOS), optional Validierung (VAL).

Auf dem PC mit MT5 (echte Fusion-Daten, alle handelbaren Symbole):
    python -m research.run --source mt5 --days 365 --tf 15
Offline mit freien Daten (HistData + gemessene Dukascopy-Spreads), inkl. älterer Jahre als VAL:
    python -m research.run --source histdata --tf 15 --val-folder data/histdata_old

--tf 1 / 15 / 60: Signale auf M1, M15 oder H1. Ausstiege werden immer auf M1 simuliert.
Ergebnis in research_out/tf<N>/: report.md, summary.csv, trades.csv.gz

Bewertung: zählt nur, wenn IS klar positiv (t >= 2, >= 30 Trades) UND OOS positiv
UND (falls vorhanden) VAL positiv. Bei vielen Kombinationen sind Zufallstreffer im IS normal.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from bot.config import load_config
from .data import load_histdata, spread_array
from .engine import force_exit_mask, simulate, stats
from .instruments import UNIVERSE
from .strategies import STRATEGIES, TF_PARAMS, Context
from .timeframes import resample, to_m1

MIN_IS_TRADES, MIN_OOS_TRADES, MIN_IS_T = 30, 15, 2.0


def iter_histdata(folder: Path, spreads: Path, cache: Path, symbols, val_folder: Path | None):
    for inst in UNIVERSE:
        if symbols and inst.name not in symbols:
            continue
        df = load_histdata(inst, folder, cache / f"{inst.name}.pkl")
        if df is None or len(df) < 5000:
            print(f"{inst.name}: keine Daten", flush=True)
            continue
        spread, src = spread_array(df, inst, spreads)
        val = None
        if val_folder:
            old = load_histdata(inst, val_folder, cache / f"{inst.name}_val.pkl")
            if old is not None and len(old) > 5000:
                val = (old, spread_array(old, inst, spreads)[0])
        yield inst, df, spread, src, val


def run_strategies(inst, m1: pd.DataFrame, spread: np.ndarray, tf: int) -> dict:
    """{Strategie: (Trades, abgelehnt wegen Kosten)} auf einem Datensatz."""
    bars = resample(m1, tf)
    ctx = Context(bars, inst)
    o, h, l, c = (m1[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    fx = force_exit_mask(m1["time"])
    out = {}
    for name, fn in STRATEGIES.items():
        sig = to_m1(fn(ctx, **TF_PARAMS[tf].get(name, {})), bars["time"], m1["time"], tf)
        trades, skipped = simulate(o, h, l, c, spread, fx, sig, inst.commission_price)
        if len(trades):
            trades["time"] = m1["time"].iloc[trades["entry_bar"]].to_numpy()
        out[name] = (trades, skipped)
    return out


def _months(times: pd.Series) -> float:
    return (times.iloc[-1] - times.iloc[0]).days / 30.44 if len(times) > 1 else 0.0


def evaluate(inst, df, spread, src, split, equity, tf=1, val=None):
    rows, trades_all = [], []
    main = run_strategies(inst, df, spread, tf)
    val_res = run_strategies(inst, val[0], val[1], tf) if val else None
    times = df["time"]
    for name, (trades, skipped) in main.items():
        row = {"symbol": inst.name, "strategy": name, "tf": tf, "spread_source": src, "skipped_cost": skipped}
        if len(trades):
            trades = trades.assign(symbol=inst.name, strategy=name, part=np.where(trades["time"] < split, "is", "oos"))
            trades_all.append(trades)
        for part, seg in (("is", times[times < split]), ("oos", times[times >= split])):
            r = trades.loc[trades["part"] == part, "r"].to_numpy() if len(trades) else np.array([])
            for k, v in stats(r, _months(seg)).items():
                row[f"{part}_{k}"] = v
        if val_res is not None:
            vt, _ = val_res[name]
            r = vt["r"].to_numpy() if len(vt) else np.array([])
            for k, v in stats(r, _months(val[0]["time"])).items():
                row[f"val_{k}"] = v
            if len(vt):
                trades_all.append(vt.assign(symbol=inst.name, strategy=name, part="val"))
        value = inst.minlot_value()
        if len(trades) and value:
            risk = float(np.median(trades["sl_dist"])) * value
            row["minlot_risk"] = round(risk, 2)
            row["minlot_risk_pct"] = round(risk / equity * 100, 1)
        rows.append(row)
    return rows, trades_all


def survivors(summary: pd.DataFrame) -> pd.DataFrame:
    s = summary
    ok = ((s.is_trades >= MIN_IS_TRADES) & (s.is_t >= MIN_IS_T) & (s.is_avg_r > 0)
          & (s.oos_trades >= MIN_OOS_TRADES) & (s.oos_avg_r > 0))
    if "val_trades" in s:
        ok &= (s.val_trades >= MIN_OOS_TRADES) & (s.val_avg_r > 0)
    return s[ok].sort_values("oos_t", ascending=False)


def strategy_table(trades: pd.DataFrame) -> pd.DataFrame:
    out = []
    for name, g in trades.groupby("strategy"):
        row = {"strategy": name}
        for part in ("is", "oos", "val"):
            r = g.loc[g["part"] == part, "r"].to_numpy()
            if part == "val" and not len(r) and "val" not in set(trades["part"]):
                continue
            st = stats(r, 1)
            row.update({f"{part}_trades": st["trades"], f"{part}_avg_r": st["avg_r"], f"{part}_t": st["t"]})
        out.append(row)
    return pd.DataFrame(out).sort_values("oos_avg_r", ascending=False)


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def write_report(summary, trades, split, out: Path, source: str, equity: float, tf: int):
    n_tests = int((summary.is_trades >= MIN_IS_TRADES).sum())
    is_hits = summary[(summary.is_trades >= MIN_IS_TRADES) & (summary.is_t >= MIN_IS_T) & (summary.is_avg_r > 0)]
    surv = survivors(summary)
    has_val = "val_trades" in summary
    label = {1: "M1", 15: "M15", 60: "H1"}.get(tf, f"{tf} Min.")
    lines = [
        f"# Strategie-Test {label} ({source})",
        "",
        f"- Märkte: {summary.symbol.nunique()}, Strategien: {summary.strategy.nunique()}, "
        f"Kombinationen mit genug Trades: {n_tests}",
        f"- Lernzeitraum (IS) bis {split:%Y-%m-%d}, Prüfzeitraum (OOS) danach"
        + (", Validierung (VAL) = ältere, vorher unberührte Daten" if has_val else ""),
        "- Ergebnis in R: +1 R = Gewinn in Höhe des Risikos; Spread und Kommission abgezogen;"
        " Ausstiege auf M1-Basis simuliert",
        "",
        "## Je Strategie über alle Märkte",
        "",
        md_table(strategy_table(trades)) if len(trades) else "_keine Trades_",
        "",
        f"## Treffer im Lernzeitraum (t >= {MIN_IS_T}): {len(is_hits)} von {n_tests}",
        f"Bei reinem Zufall wären etwa {n_tests * 0.023:.0f} zu erwarten.",
        "",
        "## Bestehen alle Prüfungen" + (" (IS + OOS + VAL)" if has_val else " (IS + OOS)"),
        "",
    ]
    cols = ["symbol", "strategy", "is_trades", "is_avg_r", "is_t", "oos_trades", "oos_avg_r", "oos_t",
            "val_trades", "val_avg_r", "val_t", "oos_max_dd_r", "minlot_risk", "minlot_risk_pct"]
    if len(surv):
        lines.append(md_table(surv[[c for c in cols if c in surv.columns]]))
        lines += ["", f"minlot_risk = typischer Verlust eines Trades mit Mindestlot; _pct bezogen auf {equity:g}."]
    else:
        lines.append("**Keine Kombination besteht alle Prüfungen.**")
    lines += ["", "## Beste 15 im Lernzeitraum (zur Einordnung)", "",
              md_table(summary[summary.is_trades >= MIN_IS_TRADES].sort_values("is_t", ascending=False)
                       .head(15)[[c for c in cols if c in summary.columns]])]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--source", choices=["histdata", "mt5"], required=True)
    p.add_argument("--tf", type=int, choices=sorted(TF_PARAMS), default=1)
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--days", type=int, default=365, help="nur mt5: Historie in Tagen")
    p.add_argument("--symbols", nargs="*")
    p.add_argument("--split", help="Beginn Prüfzeitraum (YYYY-MM-DD), Standard: letztes Drittel")
    p.add_argument("--val-folder", help="nur histdata: ältere Daten als zusätzliche Validierung")
    p.add_argument("--equity", type=float, default=19.0)
    p.add_argument("--data", default="data")
    p.add_argument("--out", default=None)
    args = p.parse_args(argv)

    data = Path(args.data)
    if args.source == "histdata":
        source = iter_histdata(data / "histdata", data / "spreads.json", data / "m1", args.symbols,
                               Path(args.val_folder) if args.val_folder else None)
    else:
        from .mt5_source import iter_mt5
        source = ((i, d, s, src, None) for i, d, s, src in iter_mt5(load_config(args.config), args.days, args.symbols))

    rows, trades = [], []
    split = pd.Timestamp(args.split, tz="UTC") if args.split else None
    for inst, df, spread, src, val in source:
        if split is None:
            t0, t1 = df["time"].iloc[0], df["time"].iloc[-1]
            split = (t0 + (t1 - t0) * 2 / 3).normalize()
        r, t = evaluate(inst, df, spread, src, split, args.equity, args.tf, val)
        rows += r
        trades += t
        best = max(r, key=lambda x: x.get("is_t", 0))
        print(f"{inst.name:8} {len(df):>7} M1-Kerzen, Spread {src:9} | bestes IS: {best['strategy']} "
              f"t={best['is_t']} OOS avgR={best['oos_avg_r']}", flush=True)

    out = Path(args.out or f"research_out/tf{args.tf}")
    out.mkdir(parents=True, exist_ok=True)
    summary = pd.DataFrame(rows)
    all_trades = pd.concat(trades, ignore_index=True) if trades else pd.DataFrame()
    summary.to_csv(out / "summary.csv", index=False)
    if len(all_trades):
        all_trades.to_csv(out / "trades.csv.gz", index=False)
    write_report(summary, all_trades, split, out, args.source, args.equity, args.tf)
    print(f"\nBericht: {out / 'report.md'}")


if __name__ == "__main__":
    main()
