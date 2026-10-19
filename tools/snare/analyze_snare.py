"""Find snare hits in a drum stem, export the cleanest one-shot, describe it.

usage: analyze_snare.py DRUMS.wav OUT_DIR [CLUSTER]
CLUSTER forces which timbre cluster is the snare, after checking the rhythm.
"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

N_FFT, HOP = 2048, 256
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def stft_mag(x):
    frames = np.lib.stride_tricks.sliding_window_view(
        np.pad(x, (N_FFT // 2, N_FFT // 2)), N_FFT)[::HOP]
    return np.abs(np.fft.rfft(frames * np.hanning(N_FFT), axis=1))


def band(mag, freqs, lo, hi):
    return mag[:, (freqs >= lo) & (freqs < hi)].sum(axis=1)


def highpass(x, sr, cutoff, width=40.0):
    """Zero-phase FFT high-pass with a raised-cosine ramp from cutoff-width to cutoff."""
    spec = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(len(x), 1 / sr)
    gain = np.clip((f - (cutoff - width)) / width, 0, 1)
    gain = 0.5 - 0.5 * np.cos(np.pi * gain)
    return np.fft.irfft(spec * (gain[:, None] if x.ndim > 1 else gain), n=len(x), axis=0)


def onsets(mag, sr):
    flux = np.maximum(np.diff(np.log1p(mag), axis=0), 0).sum(axis=1)
    flux = np.concatenate([[0], flux])
    thresh = np.convolve(flux, np.ones(31) / 31, mode="same") * 1.5 + flux.mean() * 0.5
    min_gap = int(0.08 * sr / HOP)
    picks, last = [], -min_gap
    for i in range(1, len(flux) - 1):
        if (flux[i] > thresh[i] and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1]
                and i - last >= min_gap):
            picks.append(i)
            last = i
    return np.array(picks)


def kmeans(x, k, seed=0):
    rng = np.random.default_rng(seed)
    best = (np.inf, None, None)
    for _ in range(10):
        c = x[rng.choice(len(x), k, replace=False)]
        for _ in range(50):
            lab = np.argmin(((x[:, None] - c[None]) ** 2).sum(-1), axis=1)
            c = np.array([x[lab == j].mean(0) if (lab == j).any() else c[j] for j in range(k)])
        inertia = ((x - c[lab]) ** 2).sum()
        if inertia < best[0]:
            best = (inertia, lab, c)
    return best[1], best[2]


def describe(mono, s0, sr):
    """Measure one hit starting at sample s0. What was already sounding just
    before the hit (an 808 tail, a ringing hat) is subtracted from the spectrum."""
    n = int(0.08 * sr)
    if s0 < n or s0 + int(0.45 * sr) > len(mono):
        return None
    nfft = 1 << 15
    win = np.hanning(n)
    post = np.abs(np.fft.rfft(mono[s0:s0 + n] * win, n=nfft))
    pre = np.abs(np.fft.rfft(mono[s0 - n:s0] * win, n=nfft))
    spec = np.maximum(post - pre, 0)
    freqs = np.fft.rfftfreq(nfft, 1 / sr)
    body = (freqs >= 120) & (freqs < 400)
    body_hz = freqs[body][np.argmax(spec[body])]
    centroid = (spec * freqs).sum() / spec.sum()
    total = spec.sum()
    shares = {name: spec[(freqs >= lo) & (freqs < hi)].sum() / total
              for name, lo, hi in [("sub<120", 0, 120), ("body120-400", 120, 400),
                                   ("mid400-2k", 400, 2000), ("crack2-6k", 2000, 6000),
                                   ("air6k+", 6000, sr / 2)]}
    # Decay above 150 Hz only, so a sustaining 808 does not stretch it.
    hit = highpass(mono[s0:s0 + int(0.45 * sr)], sr, 150)
    w = int(0.01 * sr)
    env = np.sqrt(np.convolve(hit ** 2, np.ones(w) / w, mode="same"))
    peak_i = int(np.argmax(env))
    below = np.where(env[peak_i:] < env[peak_i] * 0.1)[0]  # -20 dB
    decay_ms = below[0] / sr * 1000 if len(below) else 450.0
    return body_hz, centroid, decay_ms, shares


def note_name(hz):
    midi = 69 + 12 * np.log2(hz / 440)
    n = int(round(midi))
    return f"{NOTE_NAMES[n % 12]}{n // 12 - 1} ({(midi - n) * 100:+.0f} cent)"


def main(path, out_dir, force=None):
    x, sr = sf.read(path)
    mono = x.mean(axis=1) if x.ndim > 1 else x
    mag = stft_mag(mono)
    freqs = np.fft.rfftfreq(N_FFT, 1 / sr)
    picks = onsets(mag, sr)

    # Timbre of each hit: log energy in 16 log-spaced bands over the first 60 ms.
    edges = np.geomspace(30, 16000, 17)
    feats, kept = [], []
    for p in picks:
        seg = mag[p:p + int(0.06 * sr / HOP)]
        if len(seg) < 3:
            continue
        feats.append([band(seg, freqs, lo, hi).sum() for lo, hi in zip(edges[:-1], edges[1:])])
        kept.append(p)
    feats, kept = np.array(feats), np.array(kept)
    loud = feats.sum(axis=1)
    sel = loud > np.percentile(loud, 30)
    feats, kept = feats[sel], kept[sel]
    shape = np.log(feats + 1e-9)
    shape -= shape.mean(axis=1, keepdims=True)

    labels, cents = kmeans(shape, 4)
    centers_hz = np.sqrt(edges[:-1] * edges[1:])
    sub = cents[:, centers_hz < 110].mean(1)
    body = cents[:, (centers_hz >= 140) & (centers_hz < 420)].mean(1)
    crack = cents[:, (centers_hz >= 1500) & (centers_hz < 6000)].mean(1)
    air = cents[:, centers_hz >= 8000].mean(1)
    snare_score = body + crack - sub - 0.5 * air
    print(f"{Path(path).parent.name}: {len(picks)} onsets")
    for k in range(4):
        t = kept[labels == k] * HOP / sr
        gap = np.median(np.diff(t)) if len(t) > 2 else float("nan")
        print(f"  cluster {k}: {len(t):3d} hits, median gap {gap:.3f}s, sub {sub[k]:+.1f} "
              f"body {body[k]:+.1f} crack {crack[k]:+.1f} air {air[k]:+.1f} "
              f"| first: {', '.join(f'{v:.2f}' for v in t[:8])}")
    snare_k = int(force) if force is not None else int(np.argmax(snare_score))
    in_k = labels == snare_k
    hits = kept[in_k] * HOP
    typicality = -((shape[in_k] - cents[snare_k]) ** 2).sum(1)
    times = hits / sr
    gap = float(np.median(np.diff(times)))
    print(f"  snare = cluster {snare_k}: {len(hits)} hits, every {gap:.3f}s -> "
          f"{120 / gap:.1f} BPM if on 2+4, {240 / gap:.1f} BPM if half-time")

    # Cleanest hit: among the more typical half, least sound before it and
    # least sub under it (no 808 tail, no kick on the same spot).
    def rms(a):
        return np.sqrt((a ** 2).mean() + 1e-12)
    cost = []
    for s0, typ in zip(hits, typicality):
        seg = mono[s0:s0 + int(0.06 * sr)]
        if typ < np.median(typicality) or s0 < int(0.03 * sr):
            cost.append(np.inf)
            continue
        pre = rms(mono[s0 - int(0.03 * sr):s0 - int(0.005 * sr)]) / rms(seg)
        sub_share = rms(seg - highpass(seg, sr, 120)) / rms(seg)
        cost.append(pre + sub_share)
    best = int(hits[int(np.argmin(cost))])

    start = best - int(0.005 * sr)
    later = kept[kept * HOP > best + int(0.02 * sr)] * HOP
    length = min(int(0.45 * sr), int(later[0]) - int(0.005 * sr) - start if len(later) else 10**9)
    hit = highpass(x[start:start + length], sr, 100)
    fade = np.linspace(1, 0, min(int(0.08 * sr), int(0.3 * len(hit))))
    hit[-len(fade):] *= fade[:, None] if hit.ndim > 1 else fade
    hit *= 0.89 / np.abs(hit).max()
    out = Path(out_dir) / "snare_oneshot.wav"
    sf.write(out, hit.astype(np.float32), sr, subtype="PCM_24")
    print(f"  one-shot from {best / sr:.2f}s, {len(hit) / sr * 1000:.0f} ms, high-passed at 100 Hz -> {out}")

    # Describe the most typical hits one by one and take the median.
    metrics = [m for m in (describe(mono, int(s0), sr)
                           for s0 in hits[np.argsort(-typicality)[:12]]) if m]
    body_hz = float(np.median([m[0] for m in metrics]))
    print(f"  body peak {body_hz:.0f} Hz = {note_name(body_hz)}, "
          f"centroid {np.median([m[1] for m in metrics]):.0f} Hz, "
          f"decay to -20 dB {np.median([m[2] for m in metrics]):.0f} ms (median of {len(metrics)})")
    shares = {k: np.median([m[3][k] for m in metrics]) for k in metrics[0][3]}
    print("  energy share: " + ", ".join(f"{k} {v:.0%}" for k, v in shares.items()))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
