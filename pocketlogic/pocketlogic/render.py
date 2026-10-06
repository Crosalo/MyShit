"""Stufe 6: Schnitt mit ffmpeg - kurze Shots mit harten Schnitten und Bewegung, Untertitel,
Soundeffekte, Musik-Ducking, Lautheit auf Ziel-LUFS."""
import json
import logging
import random
import subprocess
import time
from pathlib import Path

log = logging.getLogger(__name__)
MUSIC_EXT = {".mp3", ".m4a", ".wav", ".ogg", ".flac"}
VOICE_COMP = "acompressor=threshold=0.1:ratio=4:attack=5:release=120:makeup=2"  # glaettet Sprachspitzen
WHOOSH_LEAD = 0.30  # Whoosh startet so viel vor dem Schnitt, damit er auf dem Schnitt "ankommt"


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
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height",
         "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def _encode_args(cfg: dict) -> list[str]:
    r = cfg["render"]
    return ["-c:v", "libx264", "-preset", r["preset"], "-crf", str(r["crf"]), "-pix_fmt", "yuv420p",
            "-r", str(r["fps"])]


def _zoom_expr(cfg: dict, shot: dict, frames: int) -> str:
    """Zoom-Ausdruck fuer zoompan: Slam (schnell von gross auf 100 %) oder sanftes Rein/Raus."""
    r = cfg["render"]
    if shot["slam"]:
        sz, sf = r["slam_zoom"], max(1, round(r["slam_seconds"] * r["fps"]))
        return f"if(lt(on,{sf}),{sz}-({sz}-1)*on/{sf},1)"
    mz = r["motion_zoom"]
    if shot["zoom"] == "in":
        return f"1+({mz}-1)*on/{frames}"
    return f"{mz}-({mz}-1)*on/{frames}"


def render_shot(cfg: dict, shot: dict, out: Path) -> Path:
    """Ein Shot als stummes 1080x1920-Video der exakten Laenge, mit Bewegung und Overlay."""
    r = cfg["render"]
    W, H, fps = r["width"], r["height"], r["fps"]
    frames = max(1, round(shot["duration"] * fps))
    zp = (f"zoompan=z='{_zoom_expr(cfg, shot, frames)}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
          f"d=1:s={W}x{H}:fps={fps}")
    if shot["type"] == "clip":
        base = f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={fps},setsar=1"
        if shot["slam"]:  # Text knallt mit rein: erst Overlay, dann Zoom
            vf = f"{base}[v];[v][1:v]overlay=0:0,{zp},format=yuv420p"
        else:             # Text bleibt ruhig, nur das Bild bewegt sich
            vf = f"{base},{zp}[v];[v][1:v]overlay=0:0,format=yuv420p"
        ffmpeg(["-ss", str(shot.get("ss", 0)), "-stream_loop", "-1", "-i", shot["path"], "-i", shot["overlay"],
                "-filter_complex", vf, "-frames:v", str(frames), "-an", *_encode_args(cfg), str(out)])
    else:  # Standbild: 2x hochskaliert gegen Zittern, dann Zoom
        z = _zoom_expr(cfg, shot, frames)
        vf = (f"scale={W * 2}:{H * 2},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
              f"d={frames}:s={W}x{H}:fps={fps},format=yuv420p")
        ffmpeg(["-i", shot["path"], "-vf", vf, "-frames:v", str(frames), *_encode_args(cfg), str(out)])
    return out


# --- Audio ---------------------------------------------------------------------------------

def _sfx_files(cfg: dict) -> tuple[Path, Path]:
    """Erzeugt die Soundeffekte einmalig synthetisch (keine Lizenzfragen)."""
    d = Path(cfg["paths"]["cache_dir"]) / "sfx"
    d.mkdir(parents=True, exist_ok=True)
    impact, whoosh = d / "impact.wav", d / "whoosh.wav"
    if not impact.exists():  # tiefer, kurzer Schlag mit abfallender Tonhoehe
        ffmpeg(["-f", "lavfi", "-i", "aevalsrc='0.9*sin(2*PI*(70-45*t)*t)*exp(-8*t)':d=0.45:s=48000",
                "-af", "afade=t=out:st=0.35:d=0.1", str(impact)])
    if not whoosh.exists():  # gefiltertes Rauschen, das an- und abschwillt
        ffmpeg(["-f", "lavfi", "-i", "anoisesrc=d=0.45:c=pink:a=0.5:r=48000",
                "-af", "highpass=f=500,lowpass=f=6000,afade=t=in:d=0.3:curve=exp,afade=t=out:st=0.3:d=0.15",
                str(whoosh)])
    return impact, whoosh


def sfx_times(cfg: dict, scene_starts: list[float]) -> list[float]:
    """Whoosh bei Szenenwechseln, aber nicht oefter als alle sfx_min_gap_s Sekunden."""
    gap, last, times = cfg["render"]["sfx_min_gap_s"], 0.0, []
    for t in scene_starts[1:]:
        if t - last >= gap:
            times.append(max(0.0, t - WHOOSH_LEAD))
            last = t
    return times


def _loudnorm_measure(path: Path, lufs: float) -> dict:
    """Misst die Lautheit (loudnorm gibt JSON auf stderr aus)."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
                        f"loudnorm=I={lufs}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, timeout=300)
    err = p.stderr
    try:
        return json.loads(err[err.rindex("{"):err.rindex("}") + 1])
    except ValueError as e:
        raise RuntimeError("Lautheitsmessung fehlgeschlagen") from e


def pick_music(cfg: dict) -> Path | None:
    d = Path(cfg["paths"]["music_dir"])
    files = [f for f in d.glob("*") if f.suffix.lower() in MUSIC_EXT] if d.exists() else []
    return random.choice(files) if files else None


def prepare_audio(cfg: dict, tts: dict, total: float, scene_starts: list[float], run: Path) -> tuple[Path, str | None]:
    """Stimme + optional Musik (Ducking) + Soundeffekte mischen, dann exakt auf Ziel-LUFS bringen."""
    r = cfg["render"]
    lufs = r["loudness_lufs"]
    inputs = ["-i", str(Path(tts["audio"]).resolve())]
    chain = [f"[0:a]{VOICE_COMP},apad,atrim=0:{total},asplit=2[vo1][vo2]"]
    mixes = ["[vo1]"]
    idx = 1

    music = pick_music(cfg)
    if music:
        inputs += ["-stream_loop", "-1", "-i", str(music.resolve())]
        chain += [f"[{idx}:a]atrim=0:{total},volume={r['music_volume']}[mu]",
                  "[mu][vo2]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=350[duck]"]
        mixes.append("[duck]")
        idx += 1
    else:
        chain.append("[vo2]anullsink")

    if r.get("sfx"):
        impact, whoosh = _sfx_files(cfg)
        events = [(impact, 0.0)] + [(whoosh, t) for t in sfx_times(cfg, scene_starts)]
        labels = []
        for k, (f, t) in enumerate(events):
            inputs += ["-i", str(f)]
            chain.append(f"[{idx}:a]adelay=delays={int(t * 1000)}:all=1[fx{k}]")
            labels.append(f"[fx{k}]")
            idx += 1
        chain.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0,apad,atrim=0:{total},"
                     f"volume={r['sfx_volume']}[sfx]")
        mixes.append("[sfx]")

    chain.append(f"{''.join(mixes)}amix=inputs={len(mixes)}:duration=first:normalize=0[a]"
                 if len(mixes) > 1 else f"{mixes[0]}anull[a]")
    mix = run / "audio_mix.wav"
    ffmpeg([*inputs, "-filter_complex", ";".join(chain), "-map", "[a]", "-ar", "48000", "-t", str(total), str(mix)])

    # Messen, dann exakte Verstaerkung + Limiter bei -1.5 dBFS
    gain = lufs - float(_loudnorm_measure(mix, lufs)["input_i"])
    norm = run / "audio_norm.wav"
    ffmpeg(["-i", str(mix), "-af", f"volume={gain:.2f}dB,alimiter=limit=0.84:attack=2:release=60:level=disabled",
            "-ar", "48000", str(norm)])
    return norm, music.name if music else None


# --- Endschnitt ----------------------------------------------------------------------------

def render_video(cfg: dict, visuals: dict, tts: dict, subs: Path, run: Path) -> dict:
    r = cfg["render"]
    seg_dir = run / "segments"
    seg_dir.mkdir(exist_ok=True)
    for old in seg_dir.glob("*.mp4"):
        old.unlink()
    shots = visuals["shots"]
    total = round(sum(s["duration"] for s in shots), 3)

    t0 = time.monotonic()
    segs = [render_shot(cfg, sh, seg_dir / f"shot_{i:02d}.mp4") for i, sh in enumerate(shots)]
    t_shots = time.monotonic() - t0

    t_audio = time.monotonic()
    audio, music = prepare_audio(cfg, tts, total, visuals["scene_starts"], run)
    t_audio = time.monotonic() - t_audio

    # Harte Schnitte: Shots aneinanderhaengen, dann Untertitel einbrennen
    inputs = []
    for s in segs:
        inputs += ["-i", str(s.relative_to(run))]
    n = len(segs)
    vchain = (f"{''.join(f'[{i}:v]' for i in range(n))}concat=n={n}:v=1:a=0[cat];"
              f"[cat]subtitles={subs.name}:fontsdir={cfg['paths']['font_dir']}[vout]")
    final = run / "final.mp4"
    t1 = time.monotonic()
    ffmpeg([*inputs, "-i", audio.name, "-filter_complex", vchain, "-map", "[vout]", "-map", f"{n}:a",
            *_encode_args(cfg), "-c:a", "aac", "-b:a", r["audio_bitrate"], "-t", str(total),
            "-movflags", "+faststart", final.name], cwd=run)
    t_final = time.monotonic() - t1

    info = probe(final)
    dur = float(info["format"]["duration"])
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    if dur >= 60 or (v["width"], v["height"]) != (r["width"], r["height"]):
        raise RuntimeError(f"Ausgabe ungueltig: {v['width']}x{v['height']}, {dur:.1f}s")
    longest = max(s["duration"] for s in shots)
    log.info("Render: %d Shots (laengster %.1fs) %.1fs, Audio %.1fs, Endschnitt %.1fs, Video %.1fs",
             n, longest, t_shots, t_audio, t_final, dur)
    return {"video": str(final), "duration": round(dur, 2), "music": music, "shots": n,
            "longest_shot_s": longest,
            "loudness_lufs": round(float(_loudnorm_measure(final, r["loudness_lufs"])["input_i"]), 1),
            "render_seconds": {"shots": round(t_shots, 1), "audio": round(t_audio, 1),
                               "final": round(t_final, 1)}}
