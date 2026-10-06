"""Laedt config.yaml und .env. Geheimnisse kommen nur aus der Umgebung."""
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Path | None = None) -> None:
    """Minimaler .env-Loader (KEY=VALUE). Bereits gesetzte Variablen bleiben unveraendert."""
    path = path or ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_config(path: Path | None = None) -> dict:
    load_env()
    with open(path or ROOT / "config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    for key in ("data_dir", "run_log", "lock_file", "cache_dir", "music_dir"):
        cfg["paths"][key] = str(ROOT / cfg["paths"][key])
    return cfg
