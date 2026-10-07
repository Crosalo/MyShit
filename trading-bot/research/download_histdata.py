"""Freie M1-Daten von histdata.com laden (Bid-Kurse, Zeitzone EST ohne Sommerzeit = UTC-5).

python -m research.download_histdata --months 2025-10:2026-09 --out data/histdata
"""
import argparse
import re
import time
from pathlib import Path

import requests

from .instruments import UNIVERSE

PAGE = "https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/{pair}/{year}/{month}"
GET = "https://www.histdata.com/get.php"
UA = {"User-Agent": "Mozilla/5.0"}


def month_range(spec: str) -> list[tuple[int, int]]:
    start, end = spec.split(":")
    y, m = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    out = []
    while (y, m) <= (ey, em):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def download(pair: str, year: int, month: int, out: Path, session: requests.Session) -> str:
    target = out / f"{pair}_{year}{month:02d}.zip"
    if target.exists() and target.stat().st_size > 10_000:
        return "vorhanden"
    page_url = PAGE.format(pair=pair.lower(), year=year, month=month)
    html = session.get(page_url, headers=UA, timeout=30).text
    tk = re.search(r'id="tk" value="([0-9a-f]+)"', html)
    if not tk:
        return "kein Token (Symbol/Monat nicht verfügbar?)"
    data = {"tk": tk.group(1), "date": str(year), "datemonth": f"{year}{month:02d}",
            "platform": "ASCII", "timeframe": "M1", "fxpair": pair}
    resp = session.post(GET, data=data, headers={**UA, "Referer": page_url}, timeout=120)
    if resp.status_code != 200 or len(resp.content) < 10_000:
        return f"fehlgeschlagen ({resp.status_code}, {len(resp.content)} B)"
    target.write_bytes(resp.content)
    return f"{len(resp.content) // 1024} KB"


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--months", required=True, help="z. B. 2025-10:2026-09")
    p.add_argument("--out", default="data/histdata")
    p.add_argument("--symbols", nargs="*", help="Histdata-Namen, Standard: ganzes Universum")
    p.add_argument("--pause", type=float, default=1.0)
    args = p.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pairs = args.symbols or [i.histdata for i in UNIVERSE]
    session = requests.Session()
    for pair in pairs:
        for year, month in month_range(args.months):
            for attempt in range(3):
                try:
                    status = download(pair, year, month, out, session)
                    break
                except requests.RequestException as exc:
                    status = f"Fehler {exc}"
                    time.sleep(5 * (attempt + 1))
            print(f"{pair} {year}-{month:02d}: {status}", flush=True)
            if status != "vorhanden":
                time.sleep(args.pause)


if __name__ == "__main__":
    main()
