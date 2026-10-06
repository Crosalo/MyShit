"""Stufe 6: Schnitt mit ffmpeg - Szenen, Ueberblendungen, Untertitel, Musik-Ducking, -14 LUFS."""
import json
import logging
import random
import subprocess
import time
from pathlib import Path

log = logging.getLogger(__name__)
MUSIC_EXT = {".mp3", ".m4a", ".wav", ".ogg", ".flac"}
VOICE_COMP = "acompressor=threshold=0.1:ratio=4:attack=5:release=120:makeup=2"  # glaettet Sprachspitzen


def ffmpeg(args: list[str], cwd: Path | None = None, timeout: int = 900) -> None:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args]
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"ffmpeg Timeout nach {timeout}s") from e
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg Fehler: {p.stderr.strip()[-600:]}")


def probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate",
         "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def _encode_args(cfg: dict) -> list[str]:
    r = cfg["render"]
    return ["-c:v", "libx264", "-preset", r["preset"], "-crf", str(r["crf"]), "-pix_fmt", "yuv420p",
            "-r", str(r["fps"])]


def render_segment(cfg: dict, scene: dict, length: float, out: Path) -> Path:
    """Eine Szene als stummes 1080x1920-Video der exakten Laenge."""
    r = cfg["render"]
    W, H, fps = r["width"], r["height"], r["fps"]
    frames = max(1, round(length * fps))
    if scene["type"] == "clip":
        vf = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"fps={fps},setsar=1[v];[v][1:v]overlay=0:0,format=yuv420p")
        ffmpeg(["-stream_loop", "-1", "-i", scene["path"], "-i", scene["overlay"],
                "-filter_complex", vf, "-frames:v", str(frames), "-an", *_encode_args(cfg), str(out)])
    else:  # Standbild mit dezentem Ken-Burns-Zoom (2x hochskaliert gegen Zittern)
        z = cfg["visuals"]["ken_burns_zoom"]
        step = (z - 1) / frames
        vf = (f"scale={W * 2}:{H * 2},zoompan=z='min(zoom+{step:.6f},{z})':"
              f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={fps},format=yuv420p")
        ffmpeg(["-i", scene["path"], "-vf", vf, "-frames:v", str(frames), *_encode_args(cfg), str(out)])
    return out


def _loudnorm_measure(path: Path, lufs: float) -> dict:
    """Pass 1: misst die Lautheit (loudnorm gibt JSON auf stderr aus)."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
                        f"loudnorm=I={lufs}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, timeout=300)
    err = p.stderr
    try:
        return json.loads(err[err.rindex("{"):err.rindex("}") + 1])
    except ValueError as e:
        raise RuntimeError("Lautheitsmessung fehlgeschlagen") from e


def prepare_audio(cfg: dict, tts: dict, total: float, run: Path) -> tuple[Path, str | None]:
    """Stimme (+ optional Musik mit Sidechain-Ducking) mischen und zweistufig auf Ziel-LUFS bringen."""
    r = cfg["render"]
    lufs = r["loudness_lufs"]
    voice = str(Path(tts["audio"]).resolve())
    mix = run / "audio_mix.wav"
    music = pick_music(cfg)
    if music:
        chain = (f"[0:a]{VOICE_COMP},apad,atrim=0:{total},asplit=2[vo1][vo2];"
                 f"[1:a]atrim=0:{total},volume={r['music_volume']}[mu];"
                 "[mu][vo1]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=350[duck];"
                 "[vo2][duck]amix=inputs=2:duration=first:normalize=0[a]")
        ffmpeg(["-i", voice, "-stream_loop", "-1", "-i", str(music.resolve()),
                "-filter_complex", chain, "-map", "[a]", "-ar", "48000", str(mix)])
    else:
        ffmpeg(["-i", voice, "-af", f"{VOICE_COMP},apad,atrim=0:{total}", "-ar", "48000", str(mix)])

    # Pass 1 messen, Pass 2 exakte Verstaerkung + Limiter bei -1.5 dBFS
    gain = lufs - float(_loudnorm_measure(mix, lufs)["input_i"])
    norm = run / "audio_norm.wav"
    ffmpeg(["-i", str(mix), "-af",
            f"volume={gain:.2f}dB,alimiter=limit=0.84:attack=2:release=60:level=disabled,"
            f"afade=t=out:st={total - 0.4:.3f}:d=0.4", "-ar", "48000", str(norm)])
    return norm, music.name if music else None


def pick_music(cfg: dict) -> Path | None:
    d = Path(cfg["paths"]["music_dir"])
    files = [f for f in d.glob("*") if f.suffix.lower() in MUSIC_EXT] if d.exists() else []
    return random.choice(files) if files else None


def render_video(cfg: dict, visuals: dict, tts: dict, subs: Path, run: Path) -> dict:
    r = cfg["render"]
    T = r["transition_s"]
    seg_dir = run / "segments"
    seg_dir.mkdir(exist_ok=True)
    scenes = visuals["scenes"]
    total = round(tts["duration"] + r["tail_s"], 3)

    t0 = time.monotonic()
    segs = []
    for i, sc in enumerate(scenes):
        length = sc["duration"] + (T if i < len(scenes) - 1 else 0)  # Puffer fuer die Ueberblendung
        segs.append(render_segment(cfg, sc, length, seg_dir / f"seg_{i:02d}.mp4"))
    t_segments = time.monotonic() - t0

    # Videokette: xfade zwischen den Szenen; der Schnitt liegt jeweils auf der Szenengrenze
    inputs, vchain, offset, prev = [], [], 0.0, "0:v"
    for s in segs:
        inputs += ["-i", str(s.relative_to(run))]
    for i in range(1, len(segs)):
        offset += scenes[i - 1]["duration"]
        label = f"x{i}"
        vchain.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={T}:offset={offset:.3f}[{label}]")
        prev = label
    font_dir = cfg["paths"]["font_dir"]
    vchain.append(f"[{prev}]subtitles={subs.name}:fontsdir={font_dir}[vout]")

    # Audio separat vorbereiten (Ducking + Zwei-Pass-Lautheit), dann nur noch muxen
    t_audio = time.monotonic()
    audio, music = prepare_audio(cfg, tts, total, run)
    t_audio = time.monotonic() - t_audio
    inputs += ["-i", audio.name]

    final = run / "final.mp4"
    t1 = time.monotonic()
    ffmpeg([*inputs, "-filter_complex", ";".join(vchain), "-map", "[vout]", "-map", f"{len(segs)}:a",
            *_encode_args(cfg), "-c:a", "aac", "-b:a", r["audio_bitrate"], "-t", str(total),
            "-movflags", "+faststart", final.name], cwd=run)
    t_final = time.monotonic() - t1

    info = probe(final)
    dur = float(info["format"]["duration"])
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    if dur >= 60 or (v["width"], v["height"]) != (r["width"], r["height"]):
        raise RuntimeError(f"Ausgabe ungueltig: {v['width']}x{v['height']}, {dur:.1f}s")
    log.info("Render: Szenen %.1fs, Audio %.1fs, Endschnitt %.1fs, Video %.1fs",
             t_segments, t_audio, t_final, dur)
    return {"video": str(final), "duration": round(dur, 2), "music": music,
            "loudness_lufs": round(float(_loudnorm_measure(final, r["loudness_lufs"])["input_i"]), 1),
            "render_seconds": {"segments": round(t_segments, 1), "audio": round(t_audio, 1),
                               "final": round(t_final, 1)}}
