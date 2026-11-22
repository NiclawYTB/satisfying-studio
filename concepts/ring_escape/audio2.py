"""Soundtrack: each bounce plays the next note of an original melody, escapes chime + shatter."""
import pickle
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile
from common2 import *

rng = np.random.default_rng(SEED + 11)
SIM = pickle.load(open("sim2.pkl", "rb"))
T_ESC = SIM["t_esc"]
T_END = T_ESC + OUTRO
N = int(T_END * SR) + 1
L = np.zeros(N)
R = np.zeros(N)
time = np.arange(N) / SR


def mtof(m):
    return 440.0 * 2 ** ((m + KEY - 69) / 12)


def tt(d):
    return np.arange(int(d * SR)) / SR


def hp(x, fc, o=2):
    return sosfilt(butter(o, fc, "hp", fs=SR, output="sos"), x)


def lp(x, fc, o=2):
    return sosfilt(butter(o, fc, "lp", fs=SR, output="sos"), x)


def place(sig, t, g=1.0, pan=0.0, bus=None):
    i0 = int(round(t * SR))
    if i0 >= N:
        return
    n = min(len(sig), N - i0)
    bl, br = (L, R) if bus is None else bus
    bl[i0:i0 + n] += sig[:n] * g * np.sqrt(0.5 * (1 - pan))
    br[i0:i0 + n] += sig[:n] * g * np.sqrt(0.5 * (1 + pan))


def marimba(m, vel=1.0):
    t = tt(1.4)
    f = mtof(m)
    x = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.55)
         + 0.35 * vel * np.sin(2 * np.pi * 3.93 * f * t) * np.exp(-t / 0.07)
         + 0.12 * vel * np.sin(2 * np.pi * 2.0 * f * t) * np.exp(-t / 0.25)
         + 0.06 * vel * np.sin(2 * np.pi * 9.2 * f * t) * np.exp(-t / 0.015))
    return x * np.minimum(1, t / 0.0015)


def bell(m, dur=1.6):
    t = tt(dur)
    f = mtof(m)
    x = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.9)
         + 0.5 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-t / 0.35)
         + 0.25 * np.sin(2 * np.pi * 5.40 * f * t) * np.exp(-t / 0.12)
         + 0.1 * np.sin(2 * np.pi * 8.93 * f * t) * np.exp(-t / 0.05))
    return x * np.minimum(1, t / 0.001)


def shatter(big=False):
    t = tt(0.9 if big else 0.4)
    x = hp(rng.standard_normal(len(t)), 5000, 4) * np.exp(-t / (0.22 if big else 0.07))
    # glassy crackles
    for _ in range(18 if big else 7):
        t0 = rng.uniform(0, 0.25 if big else 0.12)
        f = rng.uniform(3000, 9000)
        x += np.sin(2 * np.pi * f * (t - t0)) * np.exp(-np.maximum(t - t0, 0) / 0.012) * (t >= t0) * 0.5
    return x


def thump():
    t = tt(0.35)
    return np.sin(2 * np.pi * np.cumsum(55 + 70 * np.exp(-t / 0.03)) / SR) * np.exp(-t / 0.12)


def saw(freq, t, nh=14):
    out = np.zeros_like(t)
    for h in range(1, nh + 1):
        if freq * h > 8000:
            break
        out += np.sin(2 * np.pi * freq * h * t + h * 1.3) / h
    return out


# ---- melody (original): chord tones, 8 notes per chord, Am F C G ----
TONES = {
    "Am": [69, 72, 76, 81, 84, 88],
    "F": [65, 69, 72, 77, 81, 84],
    "C": [67, 72, 76, 79, 84, 88],
    "G": [67, 71, 74, 79, 83, 86],
}
PADV = {"Am": [45, 57, 60, 64], "F": [41, 53, 57, 60], "C": [48, 55, 60, 64], "G": [43, 55, 59, 62]}
PATS = [[0, 1, 2, 3, 2, 1, 2, 3], [1, 2, 3, 4, 3, 2, 1, 2],
        [2, 3, 4, 5, 4, 3, 2, 3], [3, 2, 1, 2, 3, 4, 3, 1]]

bounces = SIM["bounces"]
chord_changes = [(0.0, "Am")]
for i, b in enumerate(bounces):
    ch = PROG[(i // 8) % 4]
    if i % 8 == 0 and i > 0:
        chord_changes.append((b[0], ch))
    m = TONES[ch][PATS[(i // 8 + (i // 32)) % 4][i % 8]]
    x_screen = CX + b[2][0]
    pan = float(np.clip((x_screen - CX) / 540, -1, 1)) * 0.5
    vel = np.clip(b[4] / 1400, 0.5, 1.3)
    place(marimba(m, vel), b[0], 0.28 * (0.75 + 0.25 * vel), pan)
chord_changes.append((T_ESC, "Am"))

# ---- escapes ----
PENT = [0, 3, 5, 7, 10]
for e in SIM["escapes"]:
    t, k = e[0], e[1]
    j = int(round(k * 14 / (N_RINGS - 1)))
    m = 69 + 12 * (j // 5) + PENT[j % 5]
    pan = float(np.clip(e[2][0] / 540, -1, 1)) * 0.6
    final = k == N_RINGS - 1
    if not final:
        place(bell(m), t, 0.13, pan)
        place(shatter(), t, 0.055, pan)
        place(thump(), t, 0.35)
    else:
        for mm in (57, 64, 69, 72, 76, 81, 88):
            place(bell(mm, 3.0), t + 0.012 * (mm % 5), 0.075)
        place(shatter(True), t, 0.2)
        tb = tt(2.0)
        boom = np.sin(2 * np.pi * np.cumsum(40 + 40 * np.exp(-tb / 0.06)) / SR) * np.exp(-tb / 0.6)
        place(boom, t, 0.75)
        tc = tt(2.5)
        place(hp(rng.standard_normal(len(tc)), 4500) * np.exp(-tc / 0.7), t, 0.07, -0.5)
        place(hp(rng.standard_normal(len(tc)), 4500) * np.exp(-tc / 0.7), t, 0.07, 0.5)

# ---- outro: wall bounces walk down the A minor chord ----
desc = [81, 76, 72, 69, 64, 60, 57, 52]
for i, fb in enumerate(SIM["floor"]):
    pan = float(np.clip(fb[1][0] / 540, -1, 1)) * 0.6
    vel = np.clip(fb[2] / 1400, 0.4, 1.2)
    place(marimba(desc[min(i, len(desc) - 1)], vel), fb[0], 0.26 * vel, pan)

# ---- pad following the melody's chord ----
pad = np.zeros(N)
for ci in range(len(chord_changes)):
    t0, ch = chord_changes[ci]
    t1 = chord_changes[ci + 1][0] if ci + 1 < len(chord_changes) else T_END
    if ci == len(chord_changes) - 1:
        t1 = T_END
    d = t1 - t0 + 0.4
    t = tt(d)
    env = np.minimum(1, t / 0.35) * np.clip((d - t) / 0.4, 0, 1)
    x = np.zeros_like(t)
    for m in PADV[ch][1:]:
        for det in (-0.1, 0.0, 0.09):
            x += saw(mtof(m + det), t)
    x += 1.5 * np.sin(2 * np.pi * mtof(PADV[ch][0]) * t)
    i0 = int(t0 * SR)
    n = min(len(x), N - i0)
    pad[i0:i0 + n] += (x * env)[:n]
pad = lp(pad, 1400)
swell = 0.035 + 0.02 * np.clip((time - 2) / (T_ESC - 2), 0, 1)
swell = np.where(time > T_ESC, 0.06 * np.exp(-(time - T_ESC) / 3.0) + 0.02, swell)
L += pad * swell
R += pad * swell

# ---- reverb ----
irl = rng.standard_normal(int(1.9 * SR)) * np.exp(-np.arange(int(1.9 * SR)) / SR / 0.45)
irr = rng.standard_normal(int(1.9 * SR)) * np.exp(-np.arange(int(1.9 * SR)) / SR / 0.45)
irl = lp(irl, 6000); irr = lp(irr, 6000)
irl /= np.sqrt((irl ** 2).sum()); irr /= np.sqrt((irr ** 2).sum())
wet_l = fftconvolve(L, irl)[:N]
wet_r = fftconvolve(R, irr)[:N]
L = L + 0.35 * wet_l
R = R + 0.35 * wet_r

fade = np.clip((T_END - time) / 0.6, 0, 1)
L *= fade; R *= fade
mx = max(np.abs(L).max(), np.abs(R).max())
L = np.tanh(1.3 * L / mx) / np.tanh(1.3) * 0.8
R = np.tanh(1.3 * R / mx) / np.tanh(1.3) * 0.8
st = np.stack([L, R], 1)
wavfile.write("out/audio.wav", SR, (st * 32767).astype(np.int16))
print("audio", round(T_END, 2), "s")
