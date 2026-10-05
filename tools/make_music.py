"""Generate an original royalty-free instrumental bed (no vocals) for short video clips.

Usage: python3 tools/make_music.py OUT.wav SECONDS [BPM]
Warm lo-fi style: electric piano chords, soft pad, sub bass, gentle kick, snap and hats.
"""
import sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 44100
out, secs = sys.argv[1], float(sys.argv[2])
bpm = float(sys.argv[3]) if len(sys.argv) > 3 else 84
beat = 60 / bpm
n = int(SR * (secs + 0.5))
L = np.zeros(n)
R = np.zeros(n)
rng = np.random.default_rng(7)


def midi(m):
    return 440 * 2 ** ((m - 69) / 12)


def add(sig, t0, pan=0.0, gain=1.0):
    i = int(t0 * SR)
    if i >= n:
        return
    sig = sig[: n - i] * gain
    k = min(len(sig), int(SR * 0.02))
    sig[-k:] *= np.linspace(1, 0, k)
    a = min(len(sig), int(SR * 0.002))
    sig[:a] *= np.linspace(0, 1, a)
    L[i:i + len(sig)] += sig * (1 - max(pan, 0))
    R[i:i + len(sig)] += sig * (1 + min(pan, 0))


def epiano(f, dur):
    t = np.arange(int(SR * dur)) / SR
    env = np.exp(-t * 2.2) * (1 - np.exp(-t * 200))
    trem = 1 + 0.08 * np.sin(2 * np.pi * 4.5 * t)
    tone = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 4) + 0.12 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t * 7)
    return tone * env * trem


def pad(fs, dur):
    t = np.arange(int(SR * dur)) / SR
    s = np.zeros_like(t)
    for f in fs:
        for d in (-0.12, 0.0, 0.12):
            ph = rng.random() * 2 * np.pi
            s += 2 * ((f * (1 + d / 100) * t + ph / (2 * np.pi)) % 1) - 1
    s = sosfilt(butter(2, 900, fs=SR, output="sos"), s)
    a = np.minimum(1, t / 0.6) * np.minimum(1, (dur - t) / 0.6)
    return s * a / (len(fs) * 3)


def kick():
    t = np.arange(int(SR * 0.35)) / SR
    f = 110 * np.exp(-t * 18) + 45
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def snap():
    t = np.arange(int(SR * 0.18)) / SR
    s = sosfilt(butter(2, [1200, 6000], btype="band", fs=SR, output="sos"), rng.standard_normal(len(t)))
    return s * np.exp(-t * 28)


def hat():
    t = np.arange(int(SR * 0.05)) / SR
    s = sosfilt(butter(2, [7000, 12000], btype="band", fs=SR, output="sos"), rng.standard_normal(len(t)))
    return s * np.exp(-t * 90)


def bass(f, dur):
    t = np.arange(int(SR * dur)) / SR
    return np.sin(2 * np.pi * f * t) * np.minimum(1, t / 0.01) * np.exp(-t * 1.2)


# Am7 - Fmaj7 - Cmaj7 - G6, one chord per bar
chords = [[57, 60, 64, 67], [53, 57, 60, 64], [48, 55, 59, 64], [55, 59, 62, 64]]
roots = [45, 41, 48, 43]
bar = 4 * beat
bars = int(np.ceil(secs / bar)) + 1
for b in range(bars):
    t0 = b * bar
    ch = chords[b % 4]
    add(pad([midi(m) for m in ch], bar + 0.3), t0, gain=0.22)
    for k, m in enumerate(ch):  # gently rolled chord
        add(epiano(midi(m + 12), bar), t0 + k * 0.03, pan=(k - 1.5) * 0.2, gain=0.16)
    add(epiano(midi(ch[-1] + 12), beat * 1.5), t0 + beat * 2.5, pan=0.3, gain=0.10)
    add(bass(midi(roots[b % 4]), bar), t0, gain=0.42)
    add(bass(midi(roots[b % 4]), beat), t0 + beat * 2.5, gain=0.25)
    if b >= 1:  # drums come in after the first bar
        for q in range(4):
            if q in (0, 2):
                add(kick(), t0 + q * beat, gain=0.55)
            if q in (1, 3):
                add(snap(), t0 + q * beat, pan=0.1, gain=0.16)
        for e in range(8):
            add(hat(), t0 + e * beat / 2 + (0.02 if e % 2 else 0), pan=-0.3, gain=0.06 if e % 2 else 0.09)

# soft vinyl-like air
air = sosfilt(butter(2, [300, 4000], btype="band", fs=SR, output="sos"), rng.standard_normal(n)) * 0.006
L += air
R += air
mix = np.stack([L, R], 1)[: int(SR * secs)]
t = np.arange(len(mix)) / SR
fade = np.minimum(1, t / 1.0) * np.minimum(1, (secs - t) / 2.0)
mix *= fade[:, None]
mix /= np.max(np.abs(mix)) + 1e-9
mix *= 0.85
wavfile.write(out, SR, (mix * 32767).astype(np.int16))
print("wrote", out, f"{secs:.1f}s at {bpm:.0f} bpm")
