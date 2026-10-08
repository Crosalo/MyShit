"""Saisonalität ehrlich prüfen (Walk-Forward), wie im Video "Die langweiligste Trading-Strategie".

Behauptung: Es gibt Kalenderfenster, in denen ein Markt in 90-100 % der letzten 10 Jahre in
dieselbe Richtung lief (z. B. GBPUSD fällt 17.09.-08.10.). Wer das handelt, hat einen Vorteil.

Problem: Wer 365 Starttage x mehrere Fensterlängen x 30 Märkte durchsucht, findet solche
"100 %-Fenster" auch in reinem Zufall. Deshalb Walk-Forward:
    Für jedes Testjahr Y nur die N Jahre DAVOR auswerten, Fenster mit Trefferquote >= MIN_HIT
    auswählen und dann im Jahr Y handeln. Gezählt wird nur Jahr Y.
Ein echter Vorteil zeigt sich als Trefferquote deutlich über 50 % im Testjahr.

    python -m research.seasonal --data "<MQL5>/Files/m1export"

Alle Parameter sind vorher festgelegt (Video: "letzte 10 Jahre", "90-100 %", Fenster 3-4 Wochen).
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

LOOKBACK_YEARS = 10
MIN_HIT = 0.9  # mind. 9 von 10 Jahren gleiche Richtung
WINDOW_DAYS = (14, 21, 30)
ROUND_TRIP_COST_ATR = 0.05  # Spread + Kommission als Anteil der Tages-ATR (D1-Fenster, grob, konservativ)


def load_d1(path: Path) -> pd.Series:
    df = pd.read_csv(path)
    # D1-Kerzen sind auf Serverzeit 00:00 gestempelt; das Datum reicht
    idx = pd.to_datetime(df["time"], unit="s").dt.normalize()
    close = pd.Series(df["close"].to_numpy(float), index=idx)
    return close[~close.index.duplicated()]


def daily_atr(path: Path) -> pd.Series:
    df = pd.read_csv(path)
    idx = pd.to_datetime(df["time"], unit="s").dt.normalize()
    prev = df["close"].shift(1)
    tr = np.maximum(df["high"] - df["low"], np.maximum((df["high"] - prev).abs(), (df["low"] - prev).abs()))
    s = pd.Series(tr.rolling(20).mean().to_numpy(), index=idx)
    return s[~s.index.duplicated()]


def window_returns(close: pd.Series, year: int, start_doy: int, length: int) -> tuple[float, float, float] | None:
    """(Rendite, Einstiegskurs, Ausstiegskurs) für Fenster ab Kalendertag start_doy (Schaltjahr-neutral)."""
    start = pd.Timestamp(year, 1, 1) + pd.Timedelta(days=start_doy)
    end = start + pd.Timedelta(days=length)
    i0 = close.index.searchsorted(start)
    i1 = close.index.searchsorted(end)
    if i0 >= len(close) or i1 >= len(close) or i1 <= i0:
        return None
    # Kurs darf nicht mehr als 5 Tage neben dem Wunschdatum liegen (fehlende Historie)
    if (close.index[i0] - start).days > 5 or (close.index[i1] - end).days > 5:
        return None
    a, b = close.iloc[i0], close.iloc[i1]
    return b / a - 1, a, b


def select_windows(close: pd.Series, year: int) -> list[dict]:
    """Fenster, die in den LOOKBACK_YEARS Jahren vor `year` zu >= MIN_HIT in eine Richtung liefen."""
    years = range(year - LOOKBACK_YEARS, year)
    found = []
    for length in WINDOW_DAYS:
        for doy in range(0, 365 - length):
            rets = [window_returns(close, y, doy, length) for y in years]
            if any(r is None for r in rets):
                continue
            r = np.array([x[0] for x in rets])
            up = (r > 0).mean()
            hit, direction = (up, 1) if up >= 0.5 else (1 - up, -1)
            if hit >= MIN_HIT:
                found.append({"doy": doy, "length": length, "dir": direction, "hit": hit,
                              "avg": float(np.mean(r) * direction)})
    # Überlappende Fenster zusammenfassen: beste zuerst, dann nur noch überschneidungsfreie
    found.sort(key=lambda w: (-w["hit"], -w["avg"]))
    chosen = []
    for w in found:
        a0, a1 = w["doy"], w["doy"] + w["length"]
        if all(a1 <= c["doy"] or a0 >= c["doy"] + c["length"] for c in chosen):
            chosen.append(w)
    return chosen


def walk_forward(name: str, close: pd.Series, atr: pd.Series) -> list[dict]:
    first_year = close.index[0].year + 1  # erstes volles Jahr
    last_year = close.index[-1].year
    trades = []
    for year in range(first_year + LOOKBACK_YEARS, last_year + 1):
        for w in select_windows(close, year):
            res = window_returns(close, year, w["doy"], w["length"])
            if res is None:
                continue
            ret, entry, _ = res
            start = pd.Timestamp(year, 1, 1) + pd.Timedelta(days=w["doy"])
            a = atr.asof(start)
            if not np.isfinite(a) or a <= 0:
                continue
            move_atr = ret * entry / a * w["dir"]  # Bewegung in Tages-ATR, in Signalrichtung
            trades.append({"symbol": name, "year": year, "start": start.date(), "length": w["length"],
                           "dir": w["dir"], "hist_hit": w["hit"], "win": ret * w["dir"] > 0,
                           "move_atr": move_atr - ROUND_TRIP_COST_ATR})
    return trades


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--out", default="research_out/seasonal")
    args = p.parse_args(argv)
    folder = Path(args.data)
    all_trades, coverage = [], []
    for f in sorted(folder.glob("*_D1.csv")):
        name = f.name[: -len("_D1.csv")]
        if f.stat().st_size == 0:
            continue
        close = load_d1(f)
        years = close.index[-1].year - close.index[0].year
        coverage.append((name, close.index[0].date(), years))
        if years < LOOKBACK_YEARS + 2:
            print(f"{name}: nur {years} Jahre D1 - zu kurz", flush=True)
            continue
        t = walk_forward(name, close, daily_atr(f))
        all_trades += t
        if t:
            w = np.mean([x["win"] for x in t])
            print(f"{name:7} ab {close.index[0].date()}  {len(t):3} Fenster  Treffer {w:.0%}", flush=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(all_trades)
    df.to_csv(out / "trades.csv", index=False)
    if df.empty:
        print("Keine Daten mit genug Jahren.")
        return
    n, wins = len(df), int(df["win"].sum())
    m = df["move_atr"]
    t_stat = m.mean() / (m.std(ddof=1) / np.sqrt(n)) if n > 1 else 0
    # Binomialtest gegen 50 %: z-Wert
    z = (wins - n / 2) / np.sqrt(n / 4)
    print(f"\nWalk-Forward, {df.symbol.nunique()} Märkte, Testjahre {df.year.min()}-{df.year.max()}")
    print(f"Fenster gehandelt: {n}   Treffer: {wins} = {wins / n:.1%}   (Historie versprach Ø {df.hist_hit.mean():.0%})")
    print(f"z gegen 50 %: {z:.2f}   Ø Bewegung {m.mean():+.3f} Tages-ATR nach Kosten, t = {t_stat:.2f}")
    print("\nJe Testjahr:")
    print(df.groupby("year").agg(fenster=("win", "size"), treffer=("win", "mean"), move_atr=("move_atr", "mean"))
          .round(3).to_string())


if __name__ == "__main__":
    main()
