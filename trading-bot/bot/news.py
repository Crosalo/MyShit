"""Wirtschaftskalender als Handelsfilter.

News sind hier ein FILTER, kein Signal: rund um wichtige Termine (NFP, CPI,
Zinsentscheide ...) eröffnet der Bot keine neuen Trades für die betroffenen
Währungen. Quelle: ForexFactory-Wochenkalender (JSON). Der Feed hat ein
strenges Rate-Limit, deshalb wird er gecacht und nur alle paar Stunden geladen.
"""
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

log = logging.getLogger(__name__)

INDEX_CURRENCIES = {
    "US30": ["USD"], "US100": ["USD"], "US500": ["USD"], "NAS100": ["USD"],
    "SPX500": ["USD"], "DJ30": ["USD"], "USTEC": ["USD"], "US2000": ["USD"],
    "GER40": ["EUR"], "GER30": ["EUR"], "DE40": ["EUR"], "EU50": ["EUR"],
    "STOXX50": ["EUR"], "FRA40": ["EUR"], "ESP35": ["EUR"],
    "UK100": ["GBP"], "JPN225": ["JPY"], "JP225": ["JPY"], "AUS200": ["AUD"],
    "HK50": ["CNY"],
}
CALENDAR_CURRENCIES = {"USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "CNY"}


def symbol_currencies(symbol: str, overrides: dict | None = None) -> list[str]:
    """Welche Kalender-Währungen bewegen dieses Symbol?"""
    if overrides and symbol in overrides:
        return list(overrides[symbol])
    base = symbol.upper().split(".")[0].rstrip("+-_")
    if base in INDEX_CURRENCIES:
        return INDEX_CURRENCIES[base]
    if len(base) >= 6:
        pair = [base[:3], base[3:6]]
        found = [c for c in pair if c in CALENDAR_CURRENCIES]
        # Metalle (XAU/XAG) und Krypto hängen am USD
        if found:
            return found
    return ["USD"]


@dataclass
class Event:
    time_utc: datetime
    currency: str
    impact: str
    title: str


def parse_events(raw: list[dict]) -> list[Event]:
    events = []
    for item in raw:
        try:
            when = datetime.fromisoformat(item["date"]).astimezone(timezone.utc)
        except (KeyError, ValueError):
            continue
        events.append(
            Event(when, item.get("country", ""), item.get("impact", ""), item.get("title", ""))
        )
    return events


class NewsCalendar:
    def __init__(self, cfg: dict, cache_file: Path, http_get=requests.get, clock=time.time):
        self.cfg = cfg
        self.cache_file = Path(cache_file)
        self.http_get = http_get
        self.clock = clock
        self.events: list[Event] = []
        self.fetched_at = 0.0
        self.last_attempt = 0.0
        self._load_cache()

    def _load_cache(self):
        if not self.cache_file.exists():
            return
        try:
            data = json.loads(self.cache_file.read_text(encoding="utf-8"))
            self.events = parse_events(data["events"])
            self.fetched_at = float(data["fetched_at"])
        except (ValueError, KeyError) as exc:
            log.warning("News-Cache unlesbar: %s", exc)

    def refresh(self, force: bool = False):
        now = self.clock()
        refresh_s = self.cfg["refresh_minutes"] * 60
        if not force and now - self.fetched_at < refresh_s:
            return
        # Nach einem Fehlschlag höchstens alle 10 Minuten neu versuchen (Rate-Limit)
        if not force and now - self.last_attempt < 600:
            return
        self.last_attempt = now
        try:
            resp = self.http_get(self.cfg["url"], timeout=15, headers={"User-Agent": "mt5-bot/1.0"})
            resp.raise_for_status()
            raw = resp.json()
        except Exception as exc:  # Netzwerk, 429, kaputtes JSON
            log.warning("Wirtschaftskalender nicht ladbar: %s", exc)
            return
        self.events = parse_events(raw)
        self.fetched_at = now
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache_file.write_text(
            json.dumps({"fetched_at": now, "events": raw}), encoding="utf-8"
        )
        log.info("Wirtschaftskalender geladen: %d Termine", len(self.events))

    def healthy(self) -> bool:
        return bool(self.events) and self.clock() - self.fetched_at < self.cfg["max_age_hours"] * 3600

    def blocking_event(self, symbol: str, now_utc: datetime) -> Event | str | None:
        """Event (oder Grund als Text), das neue Trades auf `symbol` gerade verbietet."""
        if not self.cfg["enabled"]:
            return None
        if not self.healthy():
            return "Kalender veraltet/nicht verfügbar" if self.cfg["fail_closed"] else None
        currencies = set(symbol_currencies(symbol, self.cfg.get("symbol_currencies")))
        before = timedelta(minutes=self.cfg["minutes_before"])
        after = timedelta(minutes=self.cfg["minutes_after"])
        for ev in self.events:
            if ev.impact not in self.cfg["impacts"]:
                continue
            if ev.currency != "All" and ev.currency not in currencies:
                continue
            if ev.time_utc - before <= now_utc <= ev.time_utc + after:
                return ev
        return None

    def upcoming(self, now_utc: datetime, hours: int = 24) -> list[Event]:
        end = now_utc + timedelta(hours=hours)
        return [
            e for e in self.events
            if e.impact in self.cfg["impacts"] and now_utc <= e.time_utc <= end
        ]
