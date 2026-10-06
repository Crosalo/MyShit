"""Stufe 3: edge-tts mit wortgenauen Zeitmarken (WordBoundary)."""
import asyncio
import json
import os
import ssl
import subprocess
from pathlib import Path

import aiohttp
import edge_tts

from .script import generate_script, word_count


async def _synth(text: str, cfg: dict, mp3: Path) -> list[dict]:
    t = cfg["tts"]
    # edge-tts nutzt sonst fest certifi; so greifen auch eigene CA-Bundles (SSL_CERT_FILE) und Proxys.
    connector = None
    if os.environ.get("SSL_CERT_FILE"):
        connector = aiohttp.TCPConnector(ssl=ssl.create_default_context(cafile=os.environ["SSL_CERT_FILE"]))
    comm = edge_tts.Communicate(text, t["voice"], rate=t["rate"], boundary="WordBoundary",
                                connector=connector, proxy=os.environ.get("HTTPS_PROXY"))
    words = []
    with open(mp3, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 10_000_000          # 100-ns-Einheiten -> Sekunden
                words.append({"word": chunk["text"], "start": round(start, 3),
                              "end": round(start + chunk["duration"] / 10_000_000, 3)})
    return words


def audio_duration(mp3: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp3)],
        capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def synthesize(cfg: dict, text: str, out_dir: Path, retries: int = 3) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    mp3 = out_dir / "voice.mp3"
    last = None
    for i in range(retries):
        try:
            words = asyncio.run(asyncio.wait_for(_synth(text, cfg, mp3), timeout=90))
            if not words:
                raise RuntimeError("keine Wortzeitmarken erhalten")
            dur = audio_duration(mp3)
            (out_dir / "words.json").write_text(json.dumps(words, indent=1))
            return {"audio": str(mp3), "words": words, "duration": round(dur, 2)}
        except Exception as e:  # Netzwerk/Timeout -> erneut versuchen
            last = e
    raise RuntimeError(f"TTS fehlgeschlagen: {last}")


def voice_with_length_guard(cfg: dict, topic: dict, script: dict, out_dir: Path) -> tuple[dict, dict]:
    """Ist die Vertonung > max_seconds, laesst Claude das Skript kuerzen und vertont neu."""
    res = synthesize(cfg, script["script"], out_dir)
    for _ in range(2):
        if res["duration"] <= cfg["tts"]["max_seconds"]:
            break
        ratio = cfg["tts"]["max_seconds"] / res["duration"]
        target = max(60, int(word_count(script["script"]) * ratio * 0.95))
        script = generate_script(cfg, topic, shorten_to=target)
        res = synthesize(cfg, script["script"], out_dir)
    if res["duration"] > cfg["tts"]["max_seconds"]:
        raise RuntimeError(f"Audio zu lang: {res['duration']}s")
    return script, res
