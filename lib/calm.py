"""Calm, ASMR-like synthesized sounds (no music, royalty-free).
Everything sits on a major pentatonic scale so overlapping notes always sound consonant."""
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 44100
PENT = [0, 2, 4, 7, 9]          # major pentatonic


def tt(d):
    return np.arange(int(d * SR)) / SR


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lp(x, fc, o=2):
    return sosfilt(butter(o, fc, "lp", fs=SR, output="sos"), x)


def hp(x, fc, o=2):
    return sosfilt(butter(o, fc, "hp", fs=SR, output="sos"), x)


def scale_note(i, base=60):
    """i-th note of the major pentatonic scale starting at midi `base`."""
    return base + 12 * (i // 5) + PENT[i % 5]


def kalimba(m, vel=1.0, dur=1.8):
    t = tt(dur)
    f = mtof(m)
    x = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.75)
         + 0.22 * vel * np.sin(2 * np.pi * 2.0 * f * t) * np.exp(-t / 0.3)
         + 0.10 * vel * np.sin(2 * np.pi * 5.43 * f * t) * np.exp(-t / 0.06))
    return lp(x * np.minimum(1, t / 0.004), 5000) * 0.9


def glass(m, dur=2.6):
    """Soft glass / crystal bowl ping."""
    t = tt(dur)
    f = mtof(m)
    x = (np.sin(2 * np.pi * f * t) * np.exp(-t / 1.1)
         + 0.35 * np.sin(2 * np.pi * 2.32 * f * t) * np.exp(-t / 0.5)
         + 0.15 * np.sin(2 * np.pi * 4.25 * f * t) * np.exp(-t / 0.2)
         + 0.05 * np.sin(2 * np.pi * 6.63 * f * t) * np.exp(-t / 0.08))
    return x * np.minimum(1, t / 0.002) * 0.7


def pop(m, vel=1.0):
    """Little bubble / water-drop pop."""
    t = tt(0.16)
    f0 = mtof(m)
    f = f0 * (0.55 + 0.45 * (1 - np.exp(-t / 0.012)))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / 0.045) * np.minimum(1, t / 0.002) * vel


def tick(m, vel=1.0):
    """Marble on a peg: very short soft wooden tick."""
    t = tt(0.09)
    f = mtof(m)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.025) + 0.3 * np.sin(2 * np.pi * 2.7 * f * t) * np.exp(-t / 0.01)
    return x * np.minimum(1, t / 0.001) * vel


def sprinkle(rng, base=84, n=14, spread=0.35, dur=1.6):
    """Crystalline shimmer: many tiny glass pings (a soft 'shatter')."""
    out = np.zeros(int(dur * SR))
    for k in range(n):
        t0 = rng.uniform(0, spread) * (k / n) ** 0.6
        m = scale_note(rng.integers(0, 10), base)
        s = glass(m, dur=0.9) * rng.uniform(0.25, 0.6) * np.exp(-k / n)
        i0 = int(t0 * SR)
        k1 = min(len(s), len(out) - i0)
        out[i0:i0 + k1] += s[:k1]
    return out


def swell(dur=1.2):
    """Soft airy swell (filtered noise), used before a slow-motion moment."""
    t = tt(dur)
    rng = np.random.default_rng(int(dur * 1000))
    x = lp(hp(rng.standard_normal(len(t)), 1500), 6000) * np.sin(np.pi * t / dur) ** 2
    return x * 0.12


def pad(notes, dur, level=1.0):
    t = tt(dur)
    x = np.zeros_like(t)
    for m in notes:
        for det in (-0.06, 0.0, 0.07):
            f = mtof(m + det)
            x += np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t) + 0.08 * np.sin(2 * np.pi * 3 * f * t)
    trem = 1 + 0.08 * np.sin(2 * np.pi * 0.2 * t)
    env = np.minimum(1, t / 2.0) * np.clip((dur - t) / 1.5, 0, 1)
    return lp(x * env * trem, 1200) * 0.02 * level


class Mixer:
    def __init__(self, dur, seed=0):
        self.n = int((dur + 3.5) * SR)
        self.dur = dur
        self.dry = np.zeros((self.n, 2))
        self.wet = np.zeros((self.n, 2))
        self.rng = np.random.default_rng(seed)

    def put(self, sig, t, g=1.0, pan=0.0, send=0.35):
        i0 = int(round(t * SR))
        if i0 < 0 or i0 >= self.n:
            return
        k = min(len(sig), self.n - i0)
        pan = float(np.clip(pan, -1, 1))
        gl, gr = g * np.sqrt(0.5 * (1 - pan)), g * np.sqrt(0.5 * (1 + pan))
        s = sig[:k]
        self.dry[i0:i0 + k, 0] += s * gl
        self.dry[i0:i0 + k, 1] += s * gr
        if send:
            self.wet[i0:i0 + k, 0] += s * gl * send
            self.wet[i0:i0 + k, 1] += s * gr * send

    def render(self, wet=0.55, peak=0.5, lowpass=9000):
        ir_n = int(3.2 * SR)
        out = self.dry.copy()
        for c in range(2):
            ir = self.rng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / SR / 0.95)
            ir = lp(ir, 4500)
            ir[: int(0.012 * SR)] = 0
            ir /= np.sqrt((ir ** 2).sum())
            out[:, c] += fftconvolve(self.wet[:, c], ir)[: self.n] * wet
        out = lp(out.T, lowpass, 4 if lowpass < 6000 else 2).T
        n = int(self.dur * SR)
        out = out[:n]
        fade = np.clip((self.dur - np.arange(n) / SR) / 0.8, 0, 1)
        out *= fade[:, None]
        mx = np.abs(out).max() + 1e-9
        return np.tanh(1.1 * out / mx) / np.tanh(1.1) * peak


def write_wav(path, st):
    from scipy.io import wavfile
    wavfile.write(path, SR, (np.clip(st, -1, 1) * 32767).astype(np.int16))
