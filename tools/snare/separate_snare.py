#!/usr/bin/env python3
"""Pull the snare out of a song.

Stage 1: Demucs (htdemucs_ft) splits the song into drums, bass, other, vocals.
Stage 2: drumsep splits the drum stem into kick, snare, cymbals, toms.

Stage 2 only runs when the drumsep checkpoint (49469ca8.th) is given. It is
loaded with torch's weights_only unpickler and an allowlist of Demucs model
classes, so a tampered checkpoint cannot run code on load.

Usage:
    python separate_snare.py SONG.mp3 [--out DIR] [--drumsep 49469ca8.th]
"""
import argparse
import fractions
import pickle
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from demucs.apply import apply_model
from demucs.audio import AudioFile, convert_audio
from demucs.demucs import Demucs
from demucs.hdemucs import HDemucs
from demucs.htdemucs import HTDemucs
from demucs.pretrained import get_model
from demucs.states import load_model

ALLOWED_CLASSES = (Demucs, HDemucs, HTDemucs)

# drumsep was trained with Spanish stem names.
DRUMSEP_NAMES = {
    "bombo": "kick",
    "redoblante": "snare",
    "platillos": "cymbals",
    "toms": "toms",
}


def separate(model, wav, shifts):
    """Run a Demucs-style model on a (channels, time) tensor, the way
    demucs.separate does: normalize, separate, undo the normalization."""
    ref = wav.mean(0)
    mean, std = ref.mean(), ref.std()
    sources = apply_model(model, ((wav - mean) / std)[None], shifts=shifts,
                          split=True, overlap=0.25, progress=True)[0]
    return {name: src * std + mean for name, src in zip(model.sources, sources)}


def save(wav, path, samplerate):
    # soundfile wants (time, channels); write 24-bit so quiet tails survive.
    sf.write(path, wav.clamp(-1, 1).T.numpy().astype(np.float32), samplerate,
             subtype="PCM_24")
    print(f"  wrote {path}")


def load_drumsep(path):
    try:
        with torch.serialization.safe_globals([*ALLOWED_CLASSES, fractions.Fraction]):
            package = torch.load(path, map_location="cpu", weights_only=True)
    except pickle.UnpicklingError as exc:
        raise SystemExit(f"{path}: refused to load, it contains objects outside "
                         f"the allowlist.\n{exc}")
    if package.get("klass") not in ALLOWED_CLASSES:
        raise SystemExit(f"{path}: unexpected model class {package.get('klass')!r}")
    model = load_model(package)
    model.eval()
    return model


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("song", type=Path)
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "output")
    parser.add_argument("--model", default="htdemucs_ft",
                        help="Demucs model for stage 1 (default: htdemucs_ft)")
    parser.add_argument("--drumsep", type=Path,
                        help="Path to the drumsep checkpoint 49469ca8.th")
    parser.add_argument("--shifts", type=int, default=1,
                        help="Random shifts per pass; higher is cleaner but slower")
    args = parser.parse_args()

    # Load drumsep first so a missing or refused checkpoint fails before the
    # slow first stage.
    if args.drumsep and not args.drumsep.is_file():
        raise SystemExit(f"drumsep checkpoint not found: {args.drumsep}")
    drumsep = load_drumsep(args.drumsep) if args.drumsep else None

    out = args.out / args.song.stem
    out.mkdir(parents=True, exist_ok=True)

    print(f"[1/2] {args.model}: {args.song.name} -> drums")
    demucs = get_model(args.model)
    with torch.no_grad():
        song = AudioFile(args.song).read(streams=0, samplerate=demucs.samplerate,
                                         channels=demucs.audio_channels)
        stems = separate(demucs, song, args.shifts)
    drums = stems["drums"]
    save(drums, out / "drums.wav", demucs.samplerate)

    if drumsep is None:
        print("[2/2] skipped: no --drumsep checkpoint given")
        return

    print("[2/2] drumsep: drums -> kick, snare, cymbals, toms")
    drums = convert_audio(drums, demucs.samplerate, drumsep.samplerate,
                          drumsep.audio_channels)
    with torch.no_grad():
        parts = separate(drumsep, drums, args.shifts)
    for name, wav in parts.items():
        save(wav, out / f"{DRUMSEP_NAMES.get(name, name)}.wav", drumsep.samplerate)


if __name__ == "__main__":
    main()
