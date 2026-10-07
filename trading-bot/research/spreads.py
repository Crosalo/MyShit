"""Echte Spreads messen: Dukascopy liefert M1-Kerzen getrennt für Bid und Ask.

Ergebnis pro Symbol: Median-Spread je UTC-Stunde (24 Werte) -> data/spreads.json.
Dukascopy limitiert stark, deshalb langsam und mit Wiederholungen.

python -m research.spreads --days 2026-09-15 2026-09-16 2026-09-23
"""
import argparse
import json
import lzma
import struct
import time
from datetime import date
from pathlib import Path

import numpy as np
import requests

from .instruments import UNIVERSE

URL = "https://datafeed.dukascopy.com/datafeed/{sym}/{y}/{m:02d}/{d:02d}/{side}_candles_min_1.bi5"


def fetch(sym: str, day: date, side: str, session: requests.Session) -> np.ndarray | None:
    url = URL.format(sym=sym, y=day.year, m=day.month - 1, d=day.day, side=side)
    for attempt in range(6):
        try:
            r = session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
        except requests.RequestException:
            time.sleep(10 * (attempt + 1))
            continue
        if r.status_code == 200 and r.content:
            raw = lzma.decompress(r.content)
            recs = np.frombuffer(raw, dtype=">u4").reshape(-1, 6)
            return recs  # time, open, close, low, high, volume(float-Bits)
        time.sleep(10 * (attempt + 1))
    return None


def hourly_profile(bid: np.ndarray, ask: np.ndarray) -> list[float]:
    """Median (Ask-Close - Bid-Close) je Stunde, in Roh-Integern."""
    n = min(len(bid), len(ask))
    secs = bid[:n, 0]
    spread = ask[:n, 2].astype(np.int64) - bid[:n, 2].astype(np.int64)
    hours = (secs // 3600).astype(int)
    return [float(np.median(spread[hours == h])) if np.any(hours == h) else float("nan") for h in range(24)]


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--days", nargs="+", required=True)
    p.add_argument("--out", default="data/spreads.json")
    p.add_argument("--pause", type=float, default=3.0)
    args = p.parse_args(argv)
    out = Path(args.out)
    result = json.loads(out.read_text()) if out.exists() else {}
    session = requests.Session()
    for inst in UNIVERSE:
        if inst.name in result:
            continue
        profiles, levels = [], []
        for d in args.days:
            day = date.fromisoformat(d)
            bid = fetch(inst.dukascopy, day, "BID", session)
            time.sleep(args.pause)
            ask = fetch(inst.dukascopy, day, "ASK", session)
            time.sleep(args.pause)
            if bid is None or ask is None or len(bid) == 0:
                continue
            profiles.append(hourly_profile(bid, ask))
            levels.append(float(np.median(bid[:, 2])))
        if not profiles:
            print(f"{inst.name}: keine Daten", flush=True)
            continue
        result[inst.name] = {"raw_hourly": np.nanmedian(np.array(profiles), axis=0).tolist(),
                             "raw_price_level": float(np.median(levels))}
        out.write_text(json.dumps(result, indent=1))
        print(f"{inst.name}: ok", flush=True)


if __name__ == "__main__":
    main()
