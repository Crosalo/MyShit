"""5-Minuten-Opening-Range "Break & Retest" aus dem Video "Die einfachste Daytrading Strategie
für Anfänger" (Dennis Trades), mechanisch nachgebaut. Regeln vor dem Test festgelegt:

1. Range = Hoch/Tief der ersten 5 Minuten nach US-Kassaeröffnung (9:30-9:35 New York = 15:30 MEZ/MESZ).
2. Ausbruch = erste Kerze, die über dem Hoch (Long) oder unter dem Tief (Short) schließt.
   Kein Einstieg beim Ausbruch.
3. Retest = eine spätere Kerze berührt das Level wieder (Tief <= Range-Hoch bei Long).
   Schließt vorher eine Kerze zurück in der Range, ist das Setup ungültig; ein neuer Ausbruch
   (in beide Richtungen) darf es neu starten.
4. Einstieg mit Kerzenschluss, sobald nach der Berührung eine Kerze in Ausbruchsrichtung
   schließt (grün und über dem Level bei Long). Stop: tiefster Kurs seit dem Retest. Ziel 2R.
   Kein Break-Even ("kill or fill").
5. Setups nur 9:35-11:30 New York (Video: "nur 2 Stunden Trading"), ein Trade pro Tag,
   Ausstieg spätestens nach 4 Stunden.

    python -m research.break_retest --data "<MQL5>/Files/m1export" --tf M1
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from bot.config import load_config
from .engine import Signals, force_exit_mask, simulate
from .mt5_files import iter_mt5_files
from .strategies import Context

OPEN_MIN = 9 * 60 + 30
RANGE_MIN = 5
SETUP_END = 11 * 60 + 30
RR = 2.0
MAX_HOLD_MIN = 240
US_INDICES = ("US100", "US500", "US30")


def break_retest(ctx: Context) -> Signals:
    bm = ctx.tf_min
    sig = ctx.empty(max(1, MAX_HOLD_MIN // bm))
    day, mins = ctx.local("America/New_York")
    o, h, l, c = ctx.o, ctx.h, ctx.l, ctx.c
    in_range = (mins >= OPEN_MIN) & (mins < OPEN_MIN + RANGE_MIN)
    in_setup = (mins >= OPEN_MIN + RANGE_MIN) & (mins < SETUP_END)
    starts = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
    ends = np.r_[starts[1:], len(day)]
    need = max(1, int(RANGE_MIN / bm * 0.8))
    for a, b in zip(starts, ends):
        r = np.flatnonzero(in_range[a:b]) + a
        if len(r) < need:
            continue
        rh, rl = h[r].max(), l[r].min()
        direction, touched, extreme = 0, False, np.nan
        for k in np.flatnonzero(in_setup[a:b]) + a:
            if direction == 0:
                if c[k] > rh:
                    direction, touched = 1, False
                elif c[k] < rl:
                    direction, touched = -1, False
                continue
            if direction == 1:
                if c[k] < rh:  # zurück in der Range -> ungültig
                    direction = 0
                    continue
                if l[k] <= rh and not touched:
                    touched, extreme = True, l[k]
                elif touched:
                    extreme = min(extreme, l[k])
                if touched and c[k] > o[k]:
                    sig.long[k] = True
                    sig.sl_dist[k] = c[k] - extreme
                    break
            else:
                if c[k] > rl:
                    direction = 0
                    continue
                if h[k] >= rl and not touched:
                    touched, extreme = True, h[k]
                elif touched:
                    extreme = max(extreme, h[k])
                if touched and c[k] < o[k]:
                    sig.short[k] = True
                    sig.sl_dist[k] = extreme - c[k]
                    break
    sig.tp_dist = sig.sl_dist * RR
    return sig


def run_trades(inst, df: pd.DataFrame, spread: np.ndarray) -> pd.DataFrame:
    """Break & Retest auf df simulieren (research.engine), Spalten wie research.run: time, dir, r, ..."""
    ctx = Context(df, inst)
    trades, _ = simulate(ctx.o, ctx.h, ctx.l, ctx.c, spread, force_exit_mask(df["time"]), break_retest(ctx),
                         inst.commission_price)
    if len(trades):
        trades["time"] = df["time"].iloc[trades["entry_bar"]].to_numpy()
        trades["symbol"], trades["strategy"] = inst.name, "Break&Retest"
    return trades


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--tf", default="M1")
    p.add_argument("--symbols", nargs="*")
    p.add_argument("--out", default="research_out/break_retest")
    args = p.parse_args(argv)
    trades, split = [], None
    for inst, df, spread, src in iter_mt5_files(Path(args.data), load_config(args.config), args.symbols, args.tf):
        if split is None:
            t0, t1 = df["time"].iloc[0], df["time"].iloc[-1]
            split = (t0 + (t1 - t0) * 2 / 3).normalize()
        t = run_trades(inst, df, spread)
        if len(t):
            trades.append(t)
    out = Path(args.out) / args.tf
    out.mkdir(parents=True, exist_ok=True)
    tr = pd.concat(trades, ignore_index=True) if trades else pd.DataFrame(columns=["symbol", "r", "time", "dir"])
    tr.to_csv(out / "trades.csv", index=False)

    def line(label, part):
        r = part["r"].to_numpy()
        if len(r) < 2:
            return f"{label:22} {len(r):4} Trades"
        t = r.mean() / (r.std(ddof=1) / np.sqrt(len(r)))
        return (f"{label:22} {len(r):4} Trades  Treffer {np.mean(r > 0):5.1%}  Ø {r.mean():+.3f}R  "
                f"t={t:+.2f}  Summe {r.sum():+.1f}R")

    print(f"Break & Retest {args.tf}, Lernzeitraum bis {split.date() if split is not None else '-'}")
    us = tr[tr.symbol.isin(US_INDICES)]
    for label, part in (("US-Indizes gesamt", us), ("  Lernzeitraum", us[us.time < split]),
                        ("  Prüfzeitraum", us[us.time >= split]), ("  Long", us[us.dir == 1]),
                        ("  Short", us[us.dir == -1]), ("Alle 31 Märkte", tr)):
        print(line(label, part))
    for sym in US_INDICES:
        print(line(f"  {sym}", tr[tr.symbol == sym]))
    print("\nBeste übrige Märkte (nur zur Einordnung, viele Versuche):")
    rest = tr[~tr.symbol.isin(US_INDICES)].groupby("symbol")["r"].agg(["size", "mean", "sum"])
    print(rest[rest["size"] >= 20].sort_values("mean", ascending=False).head(5).round(3).to_string())


if __name__ == "__main__":
    main()
