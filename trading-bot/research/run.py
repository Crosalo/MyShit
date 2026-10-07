"""Alle Strategien x alle Märkte auf M1 testen, getrennt nach Lern- und Prüfzeitraum.

Auf dem PC mit MT5 (echte Fusion-Daten, alle handelbaren Symbole):
    python -m research.run --source mt5 --days 365
Offline mit freien Daten (HistData + gemessene Dukascopy-Spreads):
    python -m research.run --source histdata

Ergebnis in research_out/: report.md, summary.csv, trades.csv.gz

Bewertung: Ein Ergebnis zählt nur, wenn es im Lernzeitraum (IS) klar positiv ist
(t >= 2, >= 30 Trades) UND im unberührten Prüfzeitraum (OOS) positiv bleibt.
Bei ~180 Kombinationen sind ein paar Zufallstreffer im IS normal - deshalb der OOS-Test.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from bot.config import load_config
from .data import load_histdata, spread_array
from .engine import force_exit_mask, simulate, stats
from .instruments import UNIVERSE
from .strategies import STRATEGIES, Context

MIN_IS_TRADES, MIN_OOS_TRADES, MIN_IS_T = 30, 15, 2.0


def iter_histdata(folder: Path, spreads: Path, cache: Path, symbols):
    for inst in UNIVERSE:
        if symbols and inst.name not in symbols:
            continue
        df = load_histdata(inst, folder, cache / f"{inst.name}.pkl")
        if df is None or len(df) < 5000:
            print(f"{inst.name}: keine Daten", flush=True)
            continue
        spread, src = spread_array(df, inst, spreads)
        yield inst, df, spread, src


def evaluate(inst, df, spread, src, split, equity) -> tuple[list[dict], list[pd.DataFrame]]:
    ctx = Context(df, inst)
    fx = force_exit_mask(df["time"])
    times = df["time"]
    rows, trades_all = [], []
    for name, fn in STRATEGIES.items():
        sig = fn(ctx)
        trades, skipped = simulate(ctx.o, ctx.h, ctx.l, ctx.c, spread, fx, sig, inst.commission_price)
        row = {"symbol": inst.name, "strategy": name, "spread_source": src, "skipped_cost": skipped}
        if len(trades):
            trades["time"] = times.iloc[trades["entry_bar"]].to_numpy()
            trades["symbol"], trades["strategy"] = inst.name, name
            trades_all.append(trades)
        for part, mask_fn in (("is", lambda t: t < split), ("oos", lambda t: t >= split)):
            seg_times = times[mask_fn(times)]
            months = (seg_times.iloc[-1] - seg_times.iloc[0]).days / 30.44 if len(seg_times) > 1 else 0
            r = trades.loc[mask_fn(trades["time"]), "r"].to_numpy() if len(trades) else np.array([])
            for k, v in stats(r, months).items():
                row[f"{part}_{k}"] = v
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
    return s[ok].sort_values("oos_t", ascending=False)


def strategy_table(trades: pd.DataFrame, split) -> pd.DataFrame:
    out = []
    for name, g in trades.groupby("strategy"):
        row = {"strategy": name}
        for part, m in (("is", g["time"] < split), ("oos", g["time"] >= split)):
            st = stats(g.loc[m, "r"].to_numpy(), 1)
            row.update({f"{part}_trades": st["trades"], f"{part}_avg_r": st["avg_r"],
                        f"{part}_t": st["t"], f"{part}_win_pct": st["win_pct"]})
        out.append(row)
    return pd.DataFrame(out).sort_values("oos_avg_r", ascending=False)


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def write_report(summary, trades, split, out: Path, source: str, equity: float):
    n_tests = int((summary.is_trades >= MIN_IS_TRADES).sum())
    is_hits = summary[(summary.is_trades >= MIN_IS_TRADES) & (summary.is_t >= MIN_IS_T) & (summary.is_avg_r > 0)]
    surv = survivors(summary)
    lines = [
        f"# Strategie-Test M1 ({source})",
        "",
        f"- Märkte: {summary.symbol.nunique()}, Strategien: {summary.strategy.nunique()}, "
        f"Kombinationen mit genug Trades: {n_tests}",
        f"- Lernzeitraum (IS) bis {split:%Y-%m-%d}, Prüfzeitraum (OOS) danach",
        "- Ergebnis in R: +1 R = Gewinn in Höhe des Risikos; alle Kosten (Spread, Kommission) abgezogen",
        "",
        "## Je Strategie über alle Märkte",
        "",
        md_table(strategy_table(trades, split)) if len(trades) else "_keine Trades_",
        "",
        f"## Treffer im Lernzeitraum (t >= {MIN_IS_T}): {len(is_hits)} von {n_tests}",
        f"Bei reinem Zufall wären etwa {n_tests * 0.023:.0f} zu erwarten.",
        "",
        "## Bestehen auch den Prüfzeitraum",
        "",
    ]
    cols = ["symbol", "strategy", "is_trades", "is_avg_r", "is_t", "oos_trades", "oos_avg_r", "oos_t",
            "oos_pf", "oos_max_dd_r", "minlot_risk", "minlot_risk_pct"]
    if len(surv):
        lines.append(md_table(surv[[c for c in cols if c in surv.columns]]))
        lines.append("")
        lines.append(f"minlot_risk = typischer Verlust eines Trades mit Mindestlot; _pct bezogen auf {equity:g}.")
    else:
        lines.append("**Keine Kombination besteht beide Zeiträume.**")
    lines += ["", "## Beste 15 im Lernzeitraum (zur Einordnung)", "",
              md_table(summary[summary.is_trades >= MIN_IS_TRADES].sort_values("is_t", ascending=False)
                       .head(15)[[c for c in cols if c in summary.columns]])]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--source", choices=["histdata", "mt5"], required=True)
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--days", type=int, default=365, help="nur mt5: Historie in Tagen")
    p.add_argument("--symbols", nargs="*")
    p.add_argument("--split", help="Beginn Prüfzeitraum (YYYY-MM-DD), Standard: letztes Drittel")
    p.add_argument("--equity", type=float, default=19.0)
    p.add_argument("--data", default="data")
    p.add_argument("--out", default="research_out")
    args = p.parse_args(argv)

    data = Path(args.data)
    if args.source == "histdata":
        source = iter_histdata(data / "histdata", data / "spreads.json", data / "m1", args.symbols)
    else:
        from .mt5_source import iter_mt5
        source = iter_mt5(load_config(args.config), args.days, args.symbols)

    rows, trades = [], []
    split = pd.Timestamp(args.split, tz="UTC") if args.split else None
    for inst, df, spread, src in source:
        if split is None:
            t0, t1 = df["time"].iloc[0], df["time"].iloc[-1]
            split = (t0 + (t1 - t0) * 2 / 3).normalize()
        r, t = evaluate(inst, df, spread, src, split, args.equity)
        rows += r
        trades += t
        best = max(r, key=lambda x: x.get("is_t", 0))
        print(f"{inst.name:8} {len(df):>7} Kerzen, Spread {src:9} | bestes IS: {best['strategy']} "
              f"t={best['is_t']} OOS avgR={best['oos_avg_r']}", flush=True)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    summary = pd.DataFrame(rows)
    all_trades = pd.concat(trades, ignore_index=True) if trades else pd.DataFrame()
    summary.to_csv(out / "summary.csv", index=False)
    if len(all_trades):
        all_trades.to_csv(out / "trades.csv.gz", index=False)
    write_report(summary, all_trades, split, out, args.source, args.equity)
    print(f"\nBericht: {out / 'report.md'}")


if __name__ == "__main__":
    main()
