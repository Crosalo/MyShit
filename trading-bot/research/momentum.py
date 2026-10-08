"""Zwei Intraday-Momentum-Strategien aus der Forschung, auf Fusion-Index-CFDs (M5, alle Kosten).

1. Market Intraday Momentum (Gao, Han, Li, Zhou, JFE 2018; Baltussen, Da, Lammers, Martens, JFE 2021):
   Rendite vom Vortagesschluss bis 30 Minuten vor Börsenschluss -> in diese Richtung die letzte halbe
   Stunde halten. Variante "GAO": Signal ist die Rendite vom Vortagesschluss bis 30 Minuten nach Eröffnung.
   Variante "STARK": nur Tage, an denen |Signal| über dem 67. Perzentil der letzten 60 Tage liegt.
2. Noise-Boundary-Momentum (Zarattini, Aziz, Barbon 2024, nur US-Indizes):
   sigma(t) = Ø |Kurs(t)/Open - 1| der letzten 14 Tage je Uhrzeit. Obere Grenze = max(Open, Vortagesschluss)
   x (1 + sigma), untere = min(...) x (1 - sigma). Prüfung nur zur vollen und halben Stunde ab 10:00:
   über der Grenze long, unter der Grenze short. Ausstieg, wenn der Kurs zurück hinter Grenze bzw. Ø-Preis
   des Tages fällt (TWAP statt VWAP, weil die Exportdaten kein Volumen haben), spätestens 16:00.

Ergebnis je Trade bzw. Tag in Prozent des Kurses, nach Spread. Indizes zahlen bei Fusion keine Kommission.

    python -m research.momentum --data "<MQL5>/Files/m1export"
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from bot.config import load_config
from .mt5_files import iter_mt5_files

# Name: (Zeitzone, Eröffnung, Schluss) der Kassabörse
SESSIONS = {
    "US500": ("America/New_York", "09:30", "16:00"),
    "US100": ("America/New_York", "09:30", "16:00"),
    "US30": ("America/New_York", "09:30", "16:00"),
    "GER40": ("Europe/Berlin", "09:00", "17:30"),
    "UK100": ("Europe/London", "08:00", "16:30"),
    "JPN225": ("Asia/Tokyo", "09:00", "15:30"),
}


def _m(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def day_table(df: pd.DataFrame, spread: np.ndarray, tz: str, open_s: str, close_s: str) -> pd.DataFrame:
    """Je Handelstag: Kurse zu festen Uhrzeiten (Schluss der M5-Kerze VOR der Uhrzeit) und Spread."""
    t = df["time"].dt.tz_convert(tz)
    d = pd.DataFrame({"day": t.dt.date, "m": t.dt.hour * 60 + t.dt.minute, "o": df["open"].to_numpy(),
                      "c": df["close"].to_numpy(), "s": spread})
    o, c = _m(open_s), _m(close_s)
    rows = []
    for day, g in d.groupby("day"):
        at = dict(zip(g["m"], zip(g["o"], g["c"], g["s"])))
        need = (o, o + 25, c - 35, c - 30, c - 5)
        if not all(k in at for k in need):
            continue
        rows.append({"day": day, "open": at[o][0], "p_o30": at[o + 25][1], "p_c30": at[c - 35][1],
                     "entry_open": at[c - 30][0], "s_entry": at[c - 30][2], "close": at[c - 5][1], "s_exit": at[c - 5][2]})
    return pd.DataFrame(rows)


def intraday_momentum(tab: pd.DataFrame) -> pd.DataFrame:
    tab = tab.copy()
    tab["prev_close"] = tab["close"].shift(1)
    tab = tab.dropna(subset=["prev_close"]).reset_index(drop=True)
    sig_rest = tab["p_c30"] / tab["prev_close"] - 1
    sig_gao = tab["p_o30"] / tab["prev_close"] - 1
    out = []
    for name, sig in (("REST", sig_rest), ("GAO", sig_gao)):
        thr = sig.abs().rolling(60, min_periods=30).quantile(0.67).shift(1)
        for variant, mask in ((name, np.ones(len(tab), bool)), (name + "_STARK", (sig.abs() > thr).to_numpy())):
            d = np.sign(sig.to_numpy())
            e = tab["entry_open"].to_numpy() + np.where(d > 0, tab["s_entry"], 0)  # Long kauft zum Ask
            x = tab["close"].to_numpy() + np.where(d < 0, tab["s_exit"], 0)  # Short kauft zum Ask zurück
            gross = d * (tab["close"] - tab["entry_open"]).to_numpy() / tab["entry_open"].to_numpy()
            net = d * (x - e) / tab["entry_open"].to_numpy()
            ok = mask & (d != 0)
            out.append(pd.DataFrame({"day": tab["day"][ok], "variant": variant, "dir": d[ok],
                                     "gross": gross[ok], "net": net[ok]}))
    return pd.concat(out, ignore_index=True)


def noise_boundary(df: pd.DataFrame, spread: np.ndarray, tz: str) -> pd.DataFrame:
    t = df["time"].dt.tz_convert(tz)
    d = pd.DataFrame({"day": t.dt.date, "m": (t.dt.hour * 60 + t.dt.minute).to_numpy(),
                      "o": df["open"].to_numpy(), "h": df["high"].to_numpy(), "l": df["low"].to_numpy(),
                      "c": df["close"].to_numpy(), "s": spread})
    d = d[(d.m >= 570) & (d.m < 960)]
    days = []
    for day, g in d.groupby("day"):
        if len(g) < 70 or g.m.iloc[0] != 570:
            continue
        days.append((day, g.reset_index(drop=True)))
    moves = {}  # Minute -> Liste |c/open-1| der letzten Tage
    rows, prev_close = [], None
    for day, g in days:
        op = g.o.iloc[0]
        rel = dict(zip(g.m + 5, np.abs(g.c / op - 1)))  # Bewegung bis Ende der Kerze
        if prev_close is not None and all(len(moves.get(k, [])) >= 14 for k in (600, 630)):
            up_base, dn_base = max(op, prev_close), min(op, prev_close)
            typical = (g.h + g.l + g.c) / 3
            twap = typical.expanding().mean().to_numpy()
            pos, entry, pnl = 0, 0.0, 0.0
            for i in range(len(g)):
                m_end = g.m.iloc[i] + 5
                px, s = g.c.iloc[i], g.s.iloc[i]
                if m_end >= 960:
                    break
                if m_end < 600 or m_end % 30 != 0 or len(moves.get(m_end, [])) < 14:
                    continue
                sig = np.mean(moves[m_end][-14:])
                ub, lb = up_base * (1 + sig), dn_base * (1 - sig)
                want = pos
                if pos == 0:
                    want = 1 if px > ub else (-1 if px < lb else 0)
                elif pos == 1 and px < max(ub, twap[i]):
                    want = 0 if px >= lb else -1
                elif pos == -1 and px > min(lb, twap[i]):
                    want = 0 if px <= ub else 1
                if want != pos:
                    if pos != 0:
                        pnl += pos * (px - entry) - s
                    if want != 0:
                        entry = px
                    pos = want
            if pos != 0:
                last = g[g.m + 5 <= 960].iloc[-1]
                pnl += pos * (last.c - entry) - last.s
            rows.append({"day": day, "ret": pnl / op})
        for k, v in rel.items():
            moves.setdefault(k, []).append(v)
        prev_close = g.c.iloc[-1]
    return pd.DataFrame(rows)


def stats(x: np.ndarray) -> str:
    if len(x) < 3:
        return f"{len(x)} Werte"
    t = x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))
    return f"{len(x):4}  Treffer {np.mean(x > 0):5.1%}  Ø {x.mean() * 1e4:+6.2f} bp  t={t:+5.2f}"


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--out", default="research_out/momentum")
    args = p.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    allm, alln = [], []
    for inst, df, spread, src in iter_mt5_files(Path(args.data), load_config(args.config), list(SESSIONS), "M5"):
        tz, o, c = SESSIONS[inst.name]
        im = intraday_momentum(day_table(df, spread, tz, o, c))
        im["symbol"] = inst.name
        allm.append(im)
        if tz == "America/New_York":
            nb = noise_boundary(df, spread, tz)
            nb["symbol"] = inst.name
            alln.append(nb)
    im = pd.concat(allm, ignore_index=True)
    im.to_csv(out / "intraday_momentum.csv", index=False)
    split = im["day"].min() + (im["day"].max() - im["day"].min()) * 2 / 3
    print(f"=== 1. Market Intraday Momentum (letzte 30 Min.), Lernzeitraum bis {split} ===")
    print("    Variante / Markt         Tage  Treffer   Ø je Tag     t      (bp = 0,01 %)")
    for v, g in im.groupby("variant"):
        print(f"{v:12} alle 6     netto  {stats(g.net.to_numpy())}   | brutto Ø {g.gross.mean() * 1e4:+.2f} bp")
        print(f"{'':12}            IS     {stats(g[g.day < split].net.to_numpy())}")
        print(f"{'':12}            OOS    {stats(g[g.day >= split].net.to_numpy())}")
        for s, gg in g.groupby("symbol"):
            print(f"{'':12} {s:7}   netto  {stats(gg.net.to_numpy())}")
    if alln:
        nb = pd.concat(alln, ignore_index=True)
        nb.to_csv(out / "noise_boundary.csv", index=False)
        print("\n=== 2. Noise-Boundary-Momentum (Zarattini et al.), Tagesrendite bei 1x Hebel, netto ===")
        for s, g in nb.groupby("symbol"):
            r = g.ret.to_numpy()
            traded = r[r != 0]
            sharpe = r.mean() / r.std(ddof=1) * np.sqrt(252) if r.std() > 0 else 0
            print(f"{s:6} Tage {len(r)}, mit Trade {len(traded)}  Summe {r.sum() * 100:+.2f} %  Sharpe {sharpe:+.2f}  "
                  f"| Trade-Tage {stats(traded)}")
        r = nb.groupby("day").ret.mean().to_numpy()
        sh = r.mean() / r.std(ddof=1) * np.sqrt(252) if r.std() > 0 else 0
        print(f"Korb (Ø der 3) Summe {r.sum() * 100:+.2f} %  Sharpe {sh:+.2f}")
    last_hour_h1(Path(args.data), load_config(args.config))


def last_hour_h1(folder: Path, cfg: dict) -> None:
    """Variante mit H1-Daten (2019-2026): Signal Vortagesschluss -> 15:00 NY, Handel 15:00 -> 16:00 NY.
    H1-Kerzen beginnen beim NY-Close-Server zur vollen New-Yorker Stunde."""
    print("\n=== 1b. Intraday-Momentum letzte Stunde, H1 2019-2026, US-Indizes, netto ===")
    rows = []
    for inst, df, spread, src in iter_mt5_files(folder, cfg, ["US500", "US100", "US30"], "H1"):
        t = df["time"].dt.tz_convert("America/New_York")
        d = pd.DataFrame({"day": t.dt.date, "h": t.dt.hour, "o": df["open"].to_numpy(), "c": df["close"].to_numpy(), "s": spread})
        per_day = d.groupby("day")
        prev_close = None
        for day, g in per_day:
            at = {int(r.h): r for r in g.itertuples()}
            if 14 in at and 15 in at and prev_close is not None:
                sig = at[14].c / prev_close - 1
                dd = np.sign(sig)
                e = at[15].o + (at[15].s if dd > 0 else 0)
                x = at[15].c + (at[15].s if dd < 0 else 0)
                rows.append({"symbol": inst.name, "day": day, "net": dd * (x - e) / at[15].o,
                             "gross": dd * (at[15].c - at[15].o) / at[15].o})
            if 15 in at:
                prev_close = at[15].c
    r = pd.DataFrame(rows)
    r = r[r.day >= pd.Timestamp("2019-10-01").date()]
    years = pd.to_datetime(r.day).dt.year
    print(f"alle 3   netto  {stats(r.net.to_numpy())}   | brutto Ø {r.gross.mean() * 1e4:+.2f} bp")
    for s, g in r.groupby("symbol"):
        print(f"{s:7} netto  {stats(g.net.to_numpy())}")
    print("je Jahr (netto Ø bp, alle 3): " + ", ".join(f"{y}: {g.net.mean() * 1e4:+.1f}" for y, g in r.groupby(years)))


if __name__ == "__main__":
    main()
