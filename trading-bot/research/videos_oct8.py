"""Sechs YouTube-Videos vom 08.10.2026. Drei davon haben mechanisch prüfbare Regeln:

A  Tradermacher "30 Minuten täglich traden" (g2tZQSTqYEQ): EMA20-Pullback im Stundenchart, nur long.
   Aktienliste aus dem Video, soweit bei Fusion vorhanden. Marktfilter: NAS100 EMA10 > EMA20 (D1).
   Setup am Vorabend: Stunden-EMA10 vor kurzem über EMA20 gekreuzt, erster oder zweiter Rücklauf zur
   EMA20, enge Konsolidierung (kleine Stundenkerzen) an der EMA20. Einstieg 9:30-10:00 New York per
   Stop-Buy über dem Konsolidierungshoch. Stop unter dem Tagestief (Variante: Vortagestief), max. 3 %.
   Hälfte bei 2R, danach Stop auf Einstand; Rest raus, wenn eine Stundenkerze unter der EMA20 schließt.
B  TradingFreaks "Swing Trading lernen" (RJk6W_kwjCQ): Zonen aus dem TradingView-Indikator
   "Support Resistance Channels" (LonesomeTheBlue, Standardwerte), Limit-Order am Zonenrand,
   Stop jenseits der Zone, Chance-Risiko 1:1. Behauptung im Video: Trefferquote 60-65 %.
C  Craig Percoco "Price Action" (jVs9BMIWyn4): M15-Trend aus Marktstruktur (BOS), auf M1 zur
   New-York-Eröffnung Change of Character in Trendrichtung, Limit in der Mitte der Fair Value Gap,
   Stop hinter der FVG-Kerze, Ziel 3R (Variante 4R).

Nicht prüfbar: TradeX-TV-Livestream (Ermessen, eigene Indikatoren), Robbins-Cup-Orderflow (braucht
Bid/Ask-Delta und Options-Gamma, CFDs liefern nur Tick-Volumen), Urban Forex (keine Untertitel).

Alle Regeln sind vor dem ersten Lauf festgelegt. Bestanden, wenn Ø R > 0 mit t >= 2 UND beide
Zeithälften (Lern-/Prüfzeitraum) positiv.

    python -m research.videos_oct8 A --data "<MQL5>/Files/stocks" --d1 "<MQL5>/Files/m1export"
    python -m research.videos_oct8 B --data "<MQL5>/Files/m1export"
    python -m research.videos_oct8 C --data "<MQL5>/Files/m1long"
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from bot.config import load_config
from .mt5_files import iter_mt5_files, server_epoch_to_utc
from .videos import Bars, exit_trade, pivots, session_last, trade

NY = "America/New_York"
TM_LIST = ("AMD", "Amazon", "Broadcom", "Intel", "Microsoft", "Netflix", "ServiceNow", "Tesla")
SWAP_PA = 0.07  # Finanzierung Aktien-/Index-CFDs über Nacht, Annahme 7 % p. a. auf den Nominalwert


def tstat(x):
    x = np.asarray(x, float)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else 0.0


def report(label: str, t: pd.DataFrame, split, col="r"):
    if t.empty:
        print(f"{label:38} 0 Trades")
        return
    r = t[col].to_numpy()
    a, b = t[t.time < split][col], t[t.time >= split][col]
    print(f"{label:38} {len(r):5} Tr  Treffer {np.mean(r > 0):5.1%}  Ø {r.mean():+.3f}R  t={tstat(r):+5.2f}"
          f"  | vor {split.date()} {a.mean():+.3f} ({len(a)})  ab {b.mean():+.3f} ({len(b)})")
    ok = r.mean() > 0 and tstat(r) >= 2 and len(a) and len(b) and a.mean() > 0 and b.mean() > 0
    return ok


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


# ================================================================== A  Tradermacher
def stock_session(csv: Path, spec: dict, offset_h: float) -> pd.DataFrame:
    d = pd.read_csv(csv)
    t = server_epoch_to_utc(d["time"], offset_h).dt.tz_convert(NY)
    d["day"], d["m"] = t.dt.date, t.dt.hour * 60 + t.dt.minute
    d = d.dropna(subset=["day"])
    d = d[(d.m >= 570) & (d.m < 960)].copy()
    pt = spec["point"]
    d["sp"] = np.maximum(d["spread"] * pt, d["spread"].mean() * pt)
    d["hb"] = (d.m - 570) // 60  # Stundenkerzen ab 9:30 (letzte 15:30-16:00)
    return d.reset_index(drop=True)


def tradermacher(d: pd.DataFrame, filt_ok: dict, name: str, stop_mode: str, setup: bool = True,
                 tp_r: float = 2.0) -> list[dict]:
    g = d.groupby(["day", "hb"], sort=True)
    h1 = g.agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"),
               last_idx=("m", "size")).reset_index()
    h1["end"] = g.apply(lambda x: x.index[-1]).to_numpy()  # Index der letzten M5-Kerze der Stunde
    c, hi, lo = h1.close.to_numpy(), h1.high.to_numpy(), h1.low.to_numpy()
    e10, e20 = ema(c, 10), ema(c, 20)
    prev = np.r_[c[0], c[:-1]]
    atr = pd.Series(np.maximum(hi - lo, np.maximum(abs(hi - prev), abs(lo - prev)))).rolling(14).mean().to_numpy()
    h1_end = h1.end.to_numpy()
    below20 = np.zeros(len(d), bool)  # Stundenschluss unter EMA20, wirksam ab der letzten M5-Kerze der Stunde
    below20[h1_end[c < e20]] = True

    days = h1.day.unique()
    day_last_h1 = h1.groupby("day").apply(lambda x: x.index[-1]).to_dict()
    day_m5 = {k: (v.index[0], v.index[-1]) for k, v in d.groupby("day")}
    o5, h5, l5, c5, sp5 = (d[k].to_numpy() for k in ("open", "high", "low", "close", "sp"))
    day5 = d.day.to_numpy()

    # Rückläufe zur EMA20 seit dem letzten Kreuzen nach oben zählen
    touch_no = np.zeros(len(h1), int)
    cross, n_touch, away, in_touch = -1, 0, False, False
    for i in range(1, len(h1)):
        if e10[i] > e20[i] and e10[i - 1] <= e20[i - 1]:
            cross, n_touch, away, in_touch = i, 0, False, False
        if cross < 0 or e10[i] <= e20[i] or not np.isfinite(atr[i]):
            cross = -1 if e10[i] <= e20[i] else cross
            continue
        if lo[i] - e20[i] >= atr[i]:
            away, in_touch = True, False
        if away and lo[i] <= e20[i] + 0.25 * atr[i] and not in_touch:
            n_touch, in_touch = n_touch + 1, True
        touch_no[i] = n_touch if in_touch else 0

    out, busy_until = [], -1
    for di in range(20, len(days) - 1):
        day, nxt = days[di], days[di + 1]
        i = day_last_h1[day]
        if i < 3 or not filt_ok.get(day, False) or not np.isfinite(atr[i]) or e10[i] <= e20[i]:
            continue
        if setup:
            last3 = slice(i - 2, i + 1)
            if not (1 <= touch_no[i - 2:i + 1].max() <= 2):
                continue
            if (hi[last3] - lo[last3]).max() > atr[i] or hi[last3].max() - lo[last3].min() > 1.5 * atr[i]:
                continue
            if c[last3].min() < e20[i] - 0.25 * atr[i] or lo[last3].min() > e20[i] + 0.25 * atr[i]:
                continue
            level = hi[last3].max() + 0.01
        else:  # Basis ohne Setup: dieselbe Ausführung an jedem Tag mit Marktfilter und Stunden-Aufwärtstrend
            level = hi[i - 2:i + 1].max() + 0.01
        a, z = day_m5[nxt]
        if a <= busy_until:
            continue
        k0 = None
        for k in range(a, min(a + 6, z + 1)):  # 9:30-10:00
            if h5[k] >= level:
                k0 = k
                break
        if k0 is None:
            continue
        entry = (max(o5[k0], level) if k0 == a else level) + sp5[k0]
        # Tagestief bis VOR der Einstiegskerze (das Tief der Einstiegskerze kann nach dem Einstieg liegen)
        day_low = l5[a:k0].min() if k0 > a else o5[a]
        stop = (day_low if stop_mode == "tag" else lo[day_last_h1[day] - 6:day_last_h1[day] + 1].min()) - 0.01
        risk = entry - stop
        if risk <= 3 * sp5[k0] or risk > 0.03 * entry:
            continue
        tgt = entry + tp_r * risk
        res, part, st = [None, None], False, stop
        if l5[k0] <= stop:  # Einstiegskerze erreicht den Stop: pessimistisch ausgestoppt
            res = [(stop, k0), (stop, k0)]
        k = k0 + 1
        last = min(len(d) - 1, k0 + 20 * 78)
        while k <= last and (res[0] is None or res[1] is None):
            gap_px = o5[k] if day5[k] != day5[k - 1] else None
            for j in (0, 1):
                if res[j] is None and l5[k] <= st:
                    res[j] = (min(gap_px, st) if gap_px is not None else st, k)
            if res[0] is None and h5[k] >= tgt:
                res[0] = (max(gap_px, tgt) if gap_px is not None else tgt, k)
                st = max(st, entry)
            if res[1] is None and below20[k]:
                res[1] = (c5[k], k)
            k += 1
        for j in (0, 1):
            if res[j] is None:
                res[j] = (c5[last], last)
        rr = []
        for px, kx in res:
            nights = (pd.Timestamp(day5[kx]) - pd.Timestamp(day5[k0])).days
            rr.append((px - entry - SWAP_PA / 365 * nights * entry) / risk)
        busy_until = max(res[0][1], res[1][1])
        out.append({"symbol": name, "time": pd.Timestamp(nxt), "r": float(np.mean(rr)),
                    "hold_days": (pd.Timestamp(day5[busy_until]) - pd.Timestamp(day5[k0])).days})
    return out


def nas_filter(d1_csv: Path, offset_h: float) -> dict:
    d = pd.read_csv(d1_csv)
    t = server_epoch_to_utc(d["time"], offset_h)
    d["day"] = t.dt.tz_convert(NY).dt.date
    d = d.dropna(subset=["day"])
    ok = ema(d.close.to_numpy(), 10) > ema(d.close.to_numpy(), 20)
    # D1-Kerze des Vortags (Serverdatum) ist am Abend des NY-Tags fertig -> Setup-Abend nutzt sie
    return dict(zip(pd.to_datetime(d["time"], unit="s").dt.date, ok))


def run_a(args):
    folder = Path(args.data)
    off = json.loads((folder / "meta.json").read_text())["server_offset_seconds"] / 3600
    off1 = json.loads((Path(args.d1) / "meta.json").read_text())["server_offset_seconds"] / 3600
    filt = nas_filter(next(Path(args.d1).glob("US100_D1.csv*")), off1)
    split = pd.Timestamp("2024-07-01")
    res = {}
    for csv in sorted(folder.glob("*_M5.csv*")):
        name = csv.name.split("_M5.csv")[0]
        spec_f = folder / f"{name}_spec.json"
        if not spec_f.exists() or csv.stat().st_size < 1000:
            continue
        d = stock_session(csv, json.loads(spec_f.read_text()), off)
        if len(d) < 20000:
            continue
        for key, kw in (("tag", dict(stop_mode="tag")), ("vortag", dict(stop_mode="vortag")),
                        ("tag_3R", dict(stop_mode="tag", tp_r=3.0)), ("basis", dict(stop_mode="tag", setup=False))):
            res.setdefault(key, []).extend(dict(t, liste=name in TM_LIST) for t in tradermacher(d, filt, name, **kw))
        print(f"{name:22} {d.day.iloc[0]} bis {d.day.iloc[-1]}  Setups (Tagestief-Stop): "
              f"{sum(1 for t in res['tag'] if t['symbol'] == name)}", flush=True)
    print("\nA  Tradermacher EMA20-Pullback H1 (long, Kosten: Spread + 7 % p.a. Finanzierung)")
    verdict = None
    for key, label in (("tag", "Stop Tagestief, 2R/EMA20 (Hauptregel)"), ("vortag", "Stop Vortagestief"),
                       ("tag_3R", "Stop Tagestief, Hälfte bei 3R"), ("basis", "Basis ohne Setup (Kontrolle)")):
        t = pd.DataFrame(res.get(key, []))
        if t.empty:
            continue
        ok = report(f"{label} - Videoliste", t[t.liste], split)
        report(f"{label} - alle Aktien", t, split)
        if key == "tag":
            verdict = ok
            print(f"   Haltedauer Median {t.hold_days.median():.0f} Tage")
    print(f"\nURTEIL A (Hauptregel, Videoliste): {'BESTANDEN' if verdict else 'NICHT BESTANDEN'}")


# ================================================================== B  SR-Channel
def sr_channels(h, l, i, prd=10, width_pct=5.0, loopback=290, max_sr=6):
    """Kanäle aus LonesomeTheBlues 'Support Resistance Channels' mit Daten bis einschließlich i.
    Pivots sind erst prd Kerzen später bestätigt. Rückgabe [(hi, lo, Anzahl Pivots)]."""
    a = max(0, i - 299)
    cwidth = (h[a:i + 1].max() - l[a:i + 1].min()) * width_pct / 100
    lo_lim = max(prd, i - loopback)
    vals = []
    for p in range(i - prd, lo_lim - 1, -1):
        wh, wl = h[p - prd:p + prd + 1], l[p - prd:p + prd + 1]
        if h[p] == wh.max():
            vals.append(h[p])
        if l[p] == wl.min():
            vals.append(l[p])
    if not vals:
        return []
    vals = np.array(vals)
    hb, lb = h[lo_lim:i + 1], l[lo_lim:i + 1]
    ch = []
    for v in vals:
        lo = hi = v
        n = 0
        for y in vals:
            w = hi - y if y <= hi else y - lo
            if w <= cwidth:
                lo, hi = (min(lo, y), hi) if y <= hi else (lo, max(hi, y))
                n += 1
        touches = (((hb <= hi) & (hb >= lo)) | ((lb <= hi) & (lb >= lo))).sum()
        ch.append([n * 20 + touches, hi, lo, n])
    ch.sort(key=lambda x: -x[0])
    out = []
    for s, hi, lo, n in ch:
        if len(out) >= max_sr:
            break
        if any(not (hi < o[1] or lo > o[0]) for o in out):
            continue
        out.append((hi, lo, n))
    return out


def sr_trades(b: Bars, swap_pa: float, min_piv: int, tp_mode: str, max_hold: int = 60) -> list[dict]:
    """Tagesschluss i: Limit für Kerze i+1 am Rand der nächsten Zone mit >= min_piv Pivots, wenn der Kurs
    mindestens 0,5 ATR davor steht. Ein Trade je Markt gleichzeitig. Finanzierung je Nacht auf den Nominalwert."""
    out, busy = [], -1
    for i in range(320, b.n - 1):
        if i <= busy or not np.isfinite(b.atr[i]):
            continue
        chans = sr_channels(b.h, b.l, i)
        cl, atr = b.c[i], b.atr[i]
        cands = []
        sup = [x for x in chans if x[0] < cl and x[2] >= min_piv]
        res = [x for x in chans if x[1] > cl and x[2] >= min_piv]
        if sup:
            hi, lo, _ = max(sup, key=lambda x: x[0])
            if cl - hi >= 0.5 * atr:
                tpz = min((x[1] for x in chans if x[1] > cl), default=None)
                cands.append((1, hi, lo - 0.5 * atr, tpz))
        if res:
            hi, lo, _ = min(res, key=lambda x: x[1])
            if lo - cl >= 0.5 * atr:
                tpz = max((x[0] for x in chans if x[0] < cl), default=None)
                cands.append((-1, lo, hi + 0.5 * atr, tpz))
        k = i + 1
        for d, lvl, stop, tpz in cands:
            sp = b.spread[k]
            if d == 1 and b.l[k] + sp <= lvl:
                entry = min(b.o[k] + sp, lvl)
            elif d == -1 and b.h[k] >= lvl:
                entry = max(b.o[k], lvl)
            else:
                continue
            risk = abs(entry - stop)
            target = entry + d * risk if tp_mode == "1:1" else tpz
            if target is None or (target - entry) * d < risk or risk < 3 * (sp + b.commission):
                continue
            kx, px, why = exit_trade(b, k, d, entry, stop, target, min(b.n - 1, k + max_hold))
            nights = max(0, (b.t.iloc[kx] - b.t.iloc[k]).days)
            r = ((px - entry) * d - b.commission - swap_pa / 365 * nights * entry) / risk
            out.append({"symbol": b.name, "time": b.t.iloc[k].tz_convert(None), "dir": d, "r": r, "reason": why,
                        "nights": nights})
            busy = kx
            break
    return out


def run_b(args):
    folder = Path(args.data)
    cfg = load_config(args.config)
    prof = json.loads((folder / "spread_profile.json").read_text()) if (folder / "spread_profile.json").exists() else {}
    res = {}
    for tf in ("D1", "H4"):
        src_tf = "D1" if tf == "D1" else "H1"
        for inst, df, spread, _ in iter_mt5_files(folder, cfg, args.symbols, src_tf):
            if inst.name in prof:  # Tagesspread = Median der Stundenspreads (nicht der Rollover-Stunde 0)
                hp = np.array([np.nan if v is None else v for v in prof[inst.name]["hourly_points"]], float)
                spread = np.maximum(spread * 0, np.nanmedian(hp) * prof[inst.name]["point"])
            b = Bars(df, spread, inst.commission_price, inst.name)
            if tf == "H4":
                per_month = df.groupby(df["time"].dt.strftime("%Y-%m"))["time"].transform("size").to_numpy()
                dense = np.flatnonzero(per_month >= 300)
                if not len(dense):
                    continue
                b = Bars(df.iloc[dense[0]:].reset_index(drop=True), spread[dense[0]:], inst.commission_price,
                         inst.name).resample(240)
            for key, kw in (("1:1", dict(tp_mode="1:1", min_piv=2)), ("zone", dict(tp_mode="zone", min_piv=2)),
                            ("1:1 ohne Swap", dict(tp_mode="1:1", min_piv=2))):
                sw = 0.0 if "ohne" in key else (0.025 if inst.asset in ("fx", "metal") else SWAP_PA)
                res.setdefault((tf, key), []).extend(sr_trades(b, sw, **kw))
            print(f"{tf} {inst.name:7} {b.t.iloc[0].date()} bis {b.t.iloc[-1].date()}  "
                  f"{sum(1 for t in res[(tf, '1:1')] if t['symbol'] == inst.name)} Trades", flush=True)
    print("\nB  TradingFreaks SR-Channel, Limit am Zonenrand, Stop Zone + 0,5 ATR (Finanzierung FX 2,5 %, sonst 7 % p.a.)")
    verdict = None
    for (tf, key), rows in res.items():
        t = pd.DataFrame(rows)
        split = pd.Timestamp("2016-01-01") if tf == "D1" else pd.Timestamp("2023-01-01")
        ok = report(f"{tf} Ziel {key}", t, split)
        if not t.empty:
            print(f"   long {t[t.dir == 1].r.mean():+.3f} ({(t.dir == 1).sum()})  short {t[t.dir == -1].r.mean():+.3f}"
                  f" ({(t.dir == -1).sum()})  Nächte Median {t.nights.median():.0f}")
        if (tf, key) == ("D1", "1:1"):
            verdict = ok
    print(f"\nURTEIL B (D1, 1:1): {'BESTANDEN' if verdict else 'NICHT BESTANDEN'}")


# ================================================================== C  Percoco M1-FVG
def m15_trend(b15: Bars) -> pd.Series:
    """+1 nach Schluss über dem letzten bestätigten Swing-Hoch, -1 nach Schluss unter dem letzten Swing-Tief.
    Wert gilt ab Ende der M15-Kerze (nur fertige Kerzen)."""
    ph, pl = pivots(b15.h, b15.l, 2)
    tr = np.zeros(b15.n)
    sh = sl = np.nan
    state = 0
    for i in range(b15.n):
        j = i - 2  # Pivot bei j ist mit Kerze i bestätigt
        if j >= 0 and ph[j]:
            sh = b15.h[j]
        if j >= 0 and pl[j]:
            sl = b15.l[j]
        if np.isfinite(sh) and b15.c[i] > sh:
            state, sh = 1, np.nan
        elif np.isfinite(sl) and b15.c[i] < sl:
            state, sl = -1, np.nan
        tr[i] = state
    return pd.Series(tr, index=b15.t + pd.Timedelta(minutes=15))


def percoco(b: Bars, b15: Bars, tp_r: float) -> list[dict]:
    trend = m15_trend(b15).reindex(b.t, method="ffill").fillna(0).to_numpy()
    ph, pl = pivots(b.h, b.l, 2)
    out = []
    for a, z in b.day_starts():
        if b.ny_min[a] > 9 * 60 + 30 or b.ny_min[z - 1] < 11 * 60:
            continue
        start = a + int(np.searchsorted(b.ny_min[a:z], 570))
        end = a + int(np.searchsorted(b.ny_min[a:z], 660))  # 11:00
        if end - start < 60:
            continue
        done = False
        for k in range(start, end):
            d = int(trend[k])
            if d == 0 or done:
                continue
            # bestätigte Swings (Pivot j bestätigt bei j+2 <= k)
            hs = [j for j in range(max(a - 120, 0), k - 1) if (ph if d == 1 else pl)[j]]
            if len(hs) < 2:
                continue
            s1, s0 = hs[-1], hs[-2]
            lvl, prev_lvl = (b.h[s1], b.h[s0]) if d == 1 else (b.l[s1], b.l[s0])
            structure_against = lvl < prev_lvl if d == 1 else lvl > prev_lvl
            broke = (b.c[k] > lvl and b.c[k - 1] <= lvl) if d == 1 else (b.c[k] < lvl and b.c[k - 1] >= lvl)
            if not (structure_against and broke):
                continue
            leg0 = s1 + int(np.argmin(b.l[s1:k + 1]) if d == 1 else np.argmax(b.h[s1:k + 1]))
            fvg = None
            for i in range(k, leg0 + 1, -1):  # jüngste FVG im Ausbruchsbein
                if d == 1 and b.h[i - 2] < b.l[i]:
                    fvg = ((b.h[i - 2] + b.l[i]) / 2, b.l[i - 1], i)
                    break
                if d == -1 and b.l[i - 2] > b.h[i]:
                    fvg = ((b.l[i - 2] + b.h[i]) / 2, b.h[i - 1], i)
                    break
            if fvg is None:
                continue
            mid, stop, fi = fvg
            done = True  # ein Setup pro Tag
            for j in range(k + 1, end):
                # Wer zum Stop will, läuft vorher durch die FVG-Mitte: Füllung zuerst prüfen, sonst fallen
                # genau die Verlierer weg, die in derselben Kerze füllen und ausstoppen.
                if (b.o[j] <= stop) if d == 1 else (b.o[j] + b.spread[j] >= stop):
                    break  # Eröffnung schon hinter dem Stop: Setup ungültig
                filled = (b.l[j] + b.spread[j] <= mid) if d == 1 else (b.h[j] >= mid)
                if filled:
                    e = min(mid, b.o[j] + b.spread[j]) if d == 1 else max(mid, b.o[j])
                    t = trade(b, j, d, e, stop, e + d * tp_r * abs(e - stop), session_last(b, j), "PERCOCO")
                    if t:
                        out.append(t)
                    break
    return out


def run_c(args):
    folder = Path(args.data)
    cfg = load_config(args.config)
    res = {}
    for inst, df, spread, _ in iter_mt5_files(folder, cfg, args.symbols, "M1"):
        per_month = df.groupby(df["time"].dt.strftime("%Y-%m"))["time"].transform("size").to_numpy()
        dense = np.flatnonzero(per_month >= 15000)
        if not len(dense):
            continue
        df, spread = df.iloc[dense[0]:].reset_index(drop=True), spread[dense[0]:]
        b = Bars(df, spread, inst.commission_price, inst.name)
        b15 = b.resample(15)
        for tp in (3.0, 4.0):
            res.setdefault(tp, []).extend(percoco(b, b15, tp))
        print(f"{inst.name:7} M1 {b.t.iloc[0].date()} bis {b.t.iloc[-1].date()}: "
              f"{sum(1 for t in res[3.0] if t['symbol'] == inst.name)} Trades", flush=True)
    print("\nC  Percoco M15-Struktur + M1-CHoCH + FVG-Mitte, 9:30-11:00 New York, Ausstieg spätestens 16:00")
    verdict = None
    for tp, rows in res.items():
        t = pd.DataFrame(rows)
        if t.empty:
            continue
        t["time"] = t["time"].dt.tz_convert(None)
        mid = t.time.min() + (t.time.max() - t.time.min()) / 2
        ok = report(f"Ziel {tp:g}R", t, mid)
        for s, g in t.groupby("symbol"):
            print(f"   {s:7} {len(g):4} Tr  Ø {g.r.mean():+.3f}R  t={tstat(g.r):+.2f}")
        print(f"   long {t[t.dir == 1].r.mean():+.3f}  short {t[t.dir == -1].r.mean():+.3f}  "
              f"je Jahr: " + ", ".join(f"{y}: {g.r.mean():+.2f} ({len(g)})" for y, g in t.groupby(t.time.dt.year)))
        if tp == 3.0:
            verdict = ok
    print(f"\nURTEIL C (3R): {'BESTANDEN' if verdict else 'NICHT BESTANDEN'}")


# ================================================================== D  TwinTraders 1-Min-Scalping
def h1_fvg_book(b60: Bars):
    """Alle H1-FVGs mit Zeitpunkt, ab dem sie bekannt sind (Kerzenende), und Zeitpunkt der Entwertung
    (Stundenschluss jenseits der Lücke). Richtung des Marktes = zuletzt respektierte Lücke: Kurs war in der
    Lücke und schließt danach auf ihrer Ausgangsseite (bullisch über dem oberen Rand), bzw. entgegengesetzt,
    wenn eine Lücke durchbrochen wird. Alles nur mit fertigen Stundenkerzen."""
    H = pd.Timedelta(hours=1)
    t = b60.t
    zones, bias_t, bias_v, bias = [], [], [], 0
    live = []
    for i in range(2, b60.n):
        for z in live:
            if z["inv"] is not None:
                continue
            if z["dir"] == 1:
                if b60.c[i] < z["bot"]:
                    z["inv"], bias = t.iloc[i] + H, -1
                elif b60.l[i] <= z["top"]:
                    z["touched"] = True
                if z["inv"] is None and z["touched"] and b60.c[i] > z["top"]:
                    bias, z["touched"] = 1, False
            else:
                if b60.c[i] > z["top"]:
                    z["inv"], bias = t.iloc[i] + H, 1
                elif b60.h[i] >= z["bot"]:
                    z["touched"] = True
                if z["inv"] is None and z["touched"] and b60.c[i] < z["bot"]:
                    bias, z["touched"] = -1, False
        if b60.h[i - 2] < b60.l[i]:
            z = {"ready": t.iloc[i] + H, "dir": 1, "top": b60.l[i], "bot": b60.h[i - 2], "inv": None, "touched": False}
            zones.append(z)
            live.append(z)
        elif b60.l[i - 2] > b60.h[i]:
            z = {"ready": t.iloc[i] + H, "dir": -1, "top": b60.l[i - 2], "bot": b60.h[i], "inv": None, "touched": False}
            zones.append(z)
            live.append(z)
        live = [z for z in live if z["inv"] is None][-30:]
        bias_t.append(t.iloc[i] + H)
        bias_v.append(bias)
    return zones, pd.Series(bias_v, index=pd.DatetimeIndex(bias_t))


def twin_1m(b1: Bars, tp_r: float) -> list[dict]:
    """H1-FVG in Marktrichtung wird angelaufen (ab 9:00 MEZ = 3:00 NY) -> M5: Sweep (Extrem über/unter den
    6 Kerzen davor) + BOS (Schluss jenseits des Bereichs davor, binnen 12 Kerzen) mit M5-FVG im Bein ->
    Kurs läuft binnen 2 Stunden in die M5-FVG -> M1: Sweep (über/unter den 5 Kerzen davor) + BOS binnen
    10 Kerzen -> Einstieg zum nächsten M1-Open, Stop am M1-Sweep-Extrem, Ziel tp_r x Risiko.
    Abbruch, wenn das M5-Sweep-Extrem überschritten wird. Ein Trade je H1-FVG, spätestens 16:00 NY raus."""
    b5, b60 = b1.resample(5), b1.resample(60)
    zones, bias = h1_fvg_book(b60)
    bias5 = bias.reindex(b5.t, method="ffill").fillna(0).to_numpy()
    t1 = b1.t.dt.tz_convert(None).to_numpy()
    out, used, busy_t = [], set(), b1.t.iloc[0]
    zi, avail = 0, []
    for k in range(7, b5.n - 15):
        tk = b5.t.iloc[k]
        while zi < len(zones) and zones[zi]["ready"] <= tk:
            avail.append(zones[zi])
            zi += 1
        if tk < busy_t or not (180 <= b5.ny_min[k] < 16 * 60):
            continue
        d = int(bias5[k])
        if d == 0:
            continue
        zone = next((z for z in reversed(avail) if z["dir"] == d and (z["inv"] is None or z["inv"] > tk)), None)
        if zone is None or id(zone) in used or not (b5.l[k] <= zone["top"] and b5.h[k] >= zone["bot"]):
            continue
        swept = b5.l[k] < b5.l[k - 6:k].min() if d == 1 else b5.h[k] > b5.h[k - 6:k].max()
        if not swept:
            continue
        ref = b5.h[k - 6:k + 1].max() if d == 1 else b5.l[k - 6:k + 1].min()
        bos = next((j for j in range(k + 1, k + 13) if (b5.c[j] - ref) * d > 0), None)
        if bos is None:
            continue
        fvg = None
        for i in list(range(bos, k + 1, -1)) + list(range(bos + 1, bos + 4)):
            if d == 1 and b5.h[i - 2] < b5.l[i]:
                fvg = (b5.l[i], b5.h[i - 2], i)
                break
            if d == -1 and b5.l[i - 2] > b5.h[i]:
                fvg = (b5.l[i - 2], b5.h[i], i)
                break
        if fvg is None:
            continue
        top, bot, fi = fvg
        ext5 = b5.l[k:fi + 1].min() if d == 1 else b5.h[k:fi + 1].max()
        m0 = int(np.searchsorted(t1, (b5.t.iloc[fi] + pd.Timedelta(minutes=5)).tz_convert(None).to_datetime64()))
        entered, sw, sw_ref = False, None, None
        for m in range(max(m0, 6), min(m0 + 120, b1.n - 2)):
            if b1.ny_min[m] >= 16 * 60 or ((b1.l[m] < ext5) if d == 1 else (b1.h[m] > ext5)):
                break
            if not entered:
                entered = (b1.l[m] <= top) if d == 1 else (b1.h[m] >= bot)
                if not entered:
                    continue
            if sw is not None and m - sw > 10:
                sw = None
            if (b1.l[m] < b1.l[m - 5:m].min()) if d == 1 else (b1.h[m] > b1.h[m - 5:m].max()):
                if sw is None:
                    sw, sw_ref = m, (b1.h[m - 5:m + 1].max() if d == 1 else b1.l[m - 5:m + 1].min())
                continue
            if sw is not None and (b1.c[m] - sw_ref) * d > 0:
                stop = b1.l[sw:m + 1].min() if d == 1 else b1.h[sw:m + 1].max()
                e0 = b1.o[m + 1] + (b1.spread[m + 1] if d == 1 else 0.0)
                tgt = e0 + d * tp_r * abs(e0 - stop)
                last = session_last(b1, m + 1)
                t = trade(b1, m + 1, d, e0, stop, tgt, last, "TWIN1M") if (e0 - stop) * d > 0 else None
                if t:
                    kx, _, _ = exit_trade(b1, m + 1, d, e0, stop, tgt, last)
                    out.append(t)
                    used.add(id(zone))
                    busy_t = b1.t.iloc[kx]
                break
    return out


def run_d(args):
    folder = Path(args.data)
    cfg = load_config(args.config)
    res = {}
    for inst, df, spread, _ in iter_mt5_files(folder, cfg, args.symbols, "M1"):
        per_month = df.groupby(df["time"].dt.strftime("%Y-%m"))["time"].transform("size").to_numpy()
        dense = np.flatnonzero(per_month >= 15000)
        if not len(dense):
            continue
        df, spread = df.iloc[dense[0]:].reset_index(drop=True), spread[dense[0]:]
        b = Bars(df, spread, inst.commission_price, inst.name)
        for tp in (3.0, 4.0):
            res.setdefault(tp, []).extend(twin_1m(b, tp))
        print(f"{inst.name:7} M1 {b.t.iloc[0].date()} bis {b.t.iloc[-1].date()}: "
              f"{sum(1 for t in res[3.0] if t['symbol'] == inst.name)} Trades", flush=True)
    print("\nD  TwinTraders 1-Min-Scalping: H1-FVG -> M5 Sweep/BOS/FVG -> M1 Sweep/BOS, 3:00-16:00 New York")
    verdict = None
    for tp, rows in res.items():
        t = pd.DataFrame(rows)
        if t.empty:
            continue
        t["time"] = t["time"].dt.tz_convert(None)
        mid = t.time.min() + (t.time.max() - t.time.min()) / 2
        report(f"Ziel {tp:g}R, alle US-Indizes", t, mid)
        ok = report(f"Ziel {tp:g}R, nur US100 (wie im Video)", t[t.symbol == "US100"], mid)
        for s, g in t.groupby("symbol"):
            print(f"   {s:7} {len(g):4} Tr  Treffer {np.mean(g.r > 0):.1%}  Ø {g.r.mean():+.3f}R  t={tstat(g.r):+.2f}")
        print(f"   long {t[t.dir == 1].r.mean():+.3f}  short {t[t.dir == -1].r.mean():+.3f}  "
              f"je Jahr: " + ", ".join(f"{y}: {g.r.mean():+.2f} ({len(g)})" for y, g in t.groupby(t.time.dt.year)))
        if tp == 3.0:
            verdict = ok
    print(f"\nURTEIL D (US100, 3R): {'BESTANDEN' if verdict else 'NICHT BESTANDEN'}")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("test", choices=["A", "B", "C", "D"])
    p.add_argument("--data", required=True)
    p.add_argument("--d1")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--symbols", nargs="*")
    args = p.parse_args(argv)
    {"A": run_a, "B": run_b, "C": run_c, "D": run_d}[args.test](args)


if __name__ == "__main__":
    main()
