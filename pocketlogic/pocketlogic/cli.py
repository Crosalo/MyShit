"""Pocket Logic CLI.

Beispiele:
  python -m pocketlogic.cli --dry-run               # alle Stufen ausser Upload
  python -m pocketlogic.cli --stage topic           # nur Stufe 1
  python -m pocketlogic.cli --stage script --run data/runs/2026-10-06_0700
  python -m pocketlogic.cli --from-stage tts --run <ordner>
  python -m pocketlogic.cli --topic "Why minimum payments keep you in debt"
"""
import argparse
import fcntl
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

from .config import load_config
from .runlog import append_log
from .script import generate_script
from .topic import choose_topic
from .tts import voice_with_length_guard

STAGES = ["topic", "script", "tts"]  # weitere Stufen (visuals, subtitles, render, upload) folgen

log = logging.getLogger("pocketlogic")


def _load(run: Path, name: str) -> dict:
    p = run / f"{name}.json"
    if not p.exists():
        raise SystemExit(f"{p} fehlt - zuerst die vorherige Stufe ausfuehren")
    return json.loads(p.read_text())


def _save(run: Path, name: str, data: dict) -> None:
    (run / f"{name}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))


def run_stage(stage: str, cfg: dict, run: Path, args) -> None:
    if stage == "topic":
        _save(run, "topic", choose_topic(cfg, manual=args.topic))
    elif stage == "script":
        _save(run, "script", generate_script(cfg, _load(run, "topic")))
    elif stage == "tts":
        script, res = voice_with_length_guard(cfg, _load(run, "topic"), _load(run, "script"), run / "tts")
        _save(run, "script", script)   # evtl. gekuerzte Fassung
        _save(run, "tts", {k: v for k, v in res.items() if k != "words"})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="pocketlogic")
    ap.add_argument("--dry-run", action="store_true", help="alles ausser Upload")
    ap.add_argument("--stage", choices=STAGES, help="nur diese Stufe ausfuehren")
    ap.add_argument("--from-stage", choices=STAGES, help="ab dieser Stufe fortsetzen")
    ap.add_argument("--run", type=Path, help="bestehender Run-Ordner (fuer --stage/--from-stage)")
    ap.add_argument("--topic", help="Thema manuell vorgeben")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = load_config()

    run = args.run or Path(cfg["paths"]["data_dir"]) / "runs" / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    run.mkdir(parents=True, exist_ok=True)

    if args.stage:
        stages = [args.stage]
    elif args.from_stage:
        stages = STAGES[STAGES.index(args.from_stage):]
    else:
        stages = STAGES

    # Lock-Datei: nie zwei Runs gleichzeitig
    lock_path = Path(cfg["paths"]["lock_file"])
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock = open(lock_path, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log.error("Ein anderer Run laeuft bereits (%s)", lock_path)
        return 2

    timings, status, error = {}, "ok", None
    current = None
    try:
        for current in stages:
            t0 = time.monotonic()
            log.info("Stufe %s ...", current)
            run_stage(current, cfg, run, args)
            timings[current] = round(time.monotonic() - t0, 1)
            log.info("Stufe %s fertig (%.1fs)", current, timings[current])
    except Exception as e:  # noqa: BLE001 - jede Stufe soll sauber geloggt werden
        status, error = "error", f"{current}: {e}"
        log.error("Fehler in Stufe %s: %s", current, e)
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)

    # Nur volle Runs (nicht Einzelstufen) zaehlen fuer die Rotation
    if not args.stage:
        topic = json.loads((run / "topic.json").read_text()) if (run / "topic.json").exists() else {}
        script = json.loads((run / "script.json").read_text()) if (run / "script.json").exists() else {}
        tts = json.loads((run / "tts.json").read_text()) if (run / "tts.json").exists() else {}
        append_log(cfg["paths"]["run_log"], {
            "run": run.name, "status": status, "error": error, "dry_run": args.dry_run,
            "topic": topic.get("topic"), "category": topic.get("category"), "format": topic.get("format"),
            "hook": script.get("hook"), "title": script.get("title"), "duration": tts.get("duration"),
            "timings": timings,
        })
    print(f"Run-Ordner: {run}")
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
