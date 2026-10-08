"""5-Minuten-ORB auf "Stocks in Play" (Zarattini, Barbon, Aziz 2024) mit Fusion-Aktien-CFDs (M5, 2021-2026).

Regeln aus dem Paper, vor dem Test festgelegt:
- Filter: Eröffnungskurs > 5 $, ATR(14 Tage) > 0,50 $.
- Relatives Volumen (RV) = Volumen der ersten 5-Min-Kerze / Ø der ersten Kerze der letzten 14 Tage.
  Nur RV >= 1, davon die TOP_N mit dem höchsten RV (Paper: 20; Varianten 10 und 5).
- Richtung = Farbe der ersten Kerze (grün long, rot short, Doji kein Trade).
- Einstieg: Stop-Order am Hoch (long) bzw. Tief (short) der ersten Kerze, ab 9:35 New York.
- Stop: 10 % der ATR(14) vom Einstieg. Ausstieg: 16:00 New York, falls nicht ausgestoppt.
Volumen = Tick-Volumen des CFDs (Ersatz für Aktienvolumen). Kosten: Spread der Kerze, mindestens der
Ø-Spread des Symbols; Fusion verlangt auf Aktien-CFDs keine Kommission.

M5-Kerzen können nicht zeigen, ob nach dem Einstieg innerhalb derselben Kerze zuerst der Stop kam.
Deshalb zwei Grenzen: PESSIMISTISCH (Stop in der Einstiegskerze zählt, sobald berührt) und
OPTIMISTISCH (in der Einstiegskerze nur, wenn sie hinter dem Stop schließt).
Kontrolle: dieselben Trades mit zufälliger Richtung (Paper-Regel minus Zufall = echter Vorteil).

    python -m research.orb_stocks --data "<MQL5>/Files/stocks"
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .mt5_files import server_epoch_to_utc

SPLIT = pd.Timestamp("2025-01-01").date()


def load_days(csv: Path, spec: dict, offset_h: float) -> pd.DataFrame:
    d = pd.read_csv(csv)
    if len(d) < 5000 or "volume" not in d:
        return pd.DataFrame()
    t = server_epoch_to_utc(d["time"], offset_h).dt.tz_convert("America/New_York")
    d["day"], d["m"] = t.dt.date, (t.dt.hour * 60 + t.dt.minute)
    d = d.dropna(subset=["day"])
    pt = spec["point"]
    floor = d["spread"].mean() * pt
    d["sp"] = np.maximum(d["spread"] * pt, floor)
    d = d[(d.m >= 570) & (d.m < 960)]
    rows = []
    for day, g in d.groupby("day", sort=True):
        if g.m.iloc[0] != 570 or len(g) < 60:
            continue
        rows.append({"day": day, "bars": g[["m", "open", "high", "low", "close", "sp"]].to_numpy(),
                     "o": g.open.iloc[0], "or_h": g.high.iloc[0], "or_l": g.low.iloc[0], "or_c": g.close.iloc[0],
                     "or_v": g.volume.iloc[0], "hi": g.high.max(), "lo": g.low.min(), "cl": g.close.iloc[-1]})
    t = pd.DataFrame(rows)
    if t.empty:
        return t
    prev = t.cl.shift(1)
    tr = np.maximum(t.hi - t.lo, np.maximum((t.hi - prev).abs(), (t.lo - prev).abs()))
    t["atr"] = tr.rolling(14).mean().shift(1)  # nur Vortage
    t["rv"] = t.or_v / t.or_v.rolling(14).mean().shift(1)
    return t.dropna(subset=["atr", "rv"])


def simulate(row, d: int) -> tuple[float, float] | None:
    """(R pessimistisch, R optimistisch) für Richtung d, oder None ohne Einstieg."""
    bars, atr = row.bars, row.atr
    level = row.or_h if d == 1 else row.or_l
    risk = 0.1 * atr
    for i in range(1, len(bars)):
        m, o, h, l, c, sp = bars[i]
        triggered = (h + sp >= level) if d == 1 else (l <= level)
        if not triggered:
            continue
        entry = max(o + sp, level) if d == 1 else min(o, level)
        stop = entry - risk if d == 1 else entry + risk
        res = []
        for optimistic in (False, True):
            exit_px = None
            for j in range(i, len(bars)):
                _, oj, hj, lj, cj, spj = bars[j]
                if d == 1:
                    hit = (cj <= stop) if (optimistic and j == i) else (lj <= stop)
                    if hit:
                        exit_px = min(oj, stop) if j > i else stop
                        break
                else:
                    hit = (cj + spj >= stop) if (optimistic and j == i) else (hj + spj >= stop)
                    if hit:
                        exit_px = max(oj + spj, stop) if j > i else stop
                        break
            if exit_px is None:
                last = bars[-1]
                exit_px = last[4] if d == 1 else last[4] + last[5]
            res.append((exit_px - entry) * d / risk)
        return res[0], res[1]
    return None


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--out", default="research_out/orb_stocks")
    args = p.parse_args(argv)
    folder = Path(args.data)
    offset_h = json.loads((folder / "meta.json").read_text())["server_offset_seconds"] / 3600
    tables = []
    for csv in sorted(folder.glob("*_M5.csv*")):
        name = csv.name.split("_M5.csv")[0]
        spec_f = folder / f"{name}_spec.json"
        if csv.stat().st_size == 0 or not spec_f.exists():
            continue
        t = load_days(csv, json.loads(spec_f.read_text()), offset_h)
        if not t.empty:
            t["symbol"] = name
            tables.append(t)
    allt = pd.concat(tables, ignore_index=True)
    cand = allt[(allt.o > 5) & (allt.atr > 0.5) & (allt.rv >= 1) & (allt.or_c != allt.o)]
    print(f"{len(tables)} Aktien, {allt.day.nunique()} Handelstage ({allt.day.min()} bis {allt.day.max()}), "
          f"Kandidaten mit RV >= 1: {len(cand)}")
    rng = np.random.default_rng(7)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for top_n in (20, 10, 5):
        sel = cand.sort_values(["day", "rv"], ascending=[True, False]).groupby("day").head(top_n)
        trades = []
        for row in sel.itertuples():
            d = 1 if row.or_c > row.o else -1
            r = simulate(row, d)
            rnd = simulate(row, int(rng.choice([-1, 1])))
            if r is not None:
                trades.append({"day": row.day, "symbol": row.symbol, "dir": d, "rv": row.rv, "r_pess": r[0], "r_opt": r[1],
                               "rnd_pess": rnd[0] if rnd else np.nan, "rnd_opt": rnd[1] if rnd else np.nan})
        tr = pd.DataFrame(trades)
        tr.to_csv(out / f"trades_top{top_n}.csv", index=False)
        print(f"\n=== TOP {top_n} nach relativem Volumen: {len(tr)} Trades ===")
        for label, part in (("gesamt", tr), ("Lernzeitraum bis 2024", tr[tr.day < SPLIT]), ("Prüfzeitraum 2025-26", tr[tr.day >= SPLIT])):
            line = f"{label:22}"
            for col in ("r_pess", "r_opt"):
                x = part[col].to_numpy()
                t = x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else 0
                line += f" | {col[2:]:4}: Ø {x.mean():+.3f}R t={t:+.2f} Treffer {np.mean(x > 0):.0%}"
            rnd = part["rnd_pess"].dropna().to_numpy()
            line += f" | Zufall pess Ø {rnd.mean():+.3f}R" if len(rnd) else ""
            print(line)
        daily = tr.groupby("day")["r_pess"].sum() * 0.01  # 1 % Risiko je Trade
        dopt = tr.groupby("day")["r_opt"].sum() * 0.01
        for lab, s in (("pess", daily), ("opt", dopt)):
            sh = s.mean() / s.std(ddof=1) * np.sqrt(252) if s.std() > 0 else 0
            print(f"  Konto bei 1 % Risiko je Trade ({lab}): Ø {s.mean() * 252 * 100:+.1f} % p.a. (einfach), Sharpe {sh:+.2f}")


if __name__ == "__main__":
    main()
