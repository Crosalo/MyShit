"""Raeumt alte Arbeitsdateien auf: Zwischenstufen nach work_days, ganze Runs nach video_days,
ungenutzte Cache-Dateien (Clips, Vorschaubilder, Suchergebnisse) nach cache_days."""
import logging
import shutil
import time
from pathlib import Path

log = logging.getLogger(__name__)
WORK_PARTS = ("segments", "visuals", "tts", "audio_mix.wav", "audio_norm.wav")


def _age_days(p: Path) -> float:
    return (time.time() - p.stat().st_mtime) / 86400


def cleanup(cfg: dict, keep: Path | None = None) -> dict:
    ret = cfg["retention"]
    data = Path(cfg["paths"]["data_dir"])
    freed, removed_runs = 0, 0
    runs = data / "runs"
    for run in sorted(runs.iterdir()) if runs.exists() else []:
        if not run.is_dir() or (keep and run.resolve() == keep.resolve()):
            continue
        age = _age_days(run)
        if age > ret["video_days"]:
            freed += sum(f.stat().st_size for f in run.rglob("*") if f.is_file())
            shutil.rmtree(run)
            removed_runs += 1
        elif age > ret["work_days"]:
            for part in WORK_PARTS:
                p = run / part
                if p.exists():
                    freed += sum(f.stat().st_size for f in ([p] if p.is_file() else p.rglob("*")) if f.is_file())
                    shutil.rmtree(p) if p.is_dir() else p.unlink()
    cache = Path(cfg["paths"]["cache_dir"])
    for f in cache.rglob("*") if cache.exists() else []:
        if f.is_file() and f.parent.name in ("clips", "thumbs", "api") and _age_days(f) > ret["cache_days"]:
            freed += f.stat().st_size
            f.unlink()
    log.info("Aufgeraeumt: %d alte Runs entfernt, %.0f MB frei", removed_runs, freed / 1e6)
    return {"removed_runs": removed_runs, "freed_mb": round(freed / 1e6)}
