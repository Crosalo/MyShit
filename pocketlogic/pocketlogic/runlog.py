"""Run-Log als JSON Lines: ein Eintrag pro Run, dient auch der Themen-Rotation."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def read_log(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    entries = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # kaputte Zeile ueberspringen statt abstuerzen
    return entries


def append_log(path: str, entry: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **entry}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def recent(entries: list[dict], days: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out = []
    for e in entries:
        try:
            if datetime.fromisoformat(e["ts"]) >= cutoff:
                out.append(e)
        except (KeyError, ValueError):
            continue
    return out


def published(entries: list[dict]) -> list[dict]:
    """Nur echte, erfolgreiche Runs sperren Themen und Clips (keine Testlaeufe, keine Fehler)."""
    return [e for e in entries if e.get("status") == "ok" and not e.get("dry_run")]
