"""Synthesised soundtrack (royalty-free): beat + a note on every ring hit + drop."""
import pickle
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile
from common import *

rng = np.random.default_rng(SEED + 1)
with open("sim.pkl", "rb") as f:
    SIM = pickle.load(f)

N = int(T_END * SR) + 1
L = np.zeros(N)
R = np.zeros(N)


def mtof(m):
    return 440.0 * 2 ** ((m + KEY - 69) / 12)


def place(sig, t, gain=1.0, pan=0.0):
    i0 = int(round(t * SR))
    if i0 >= N:
        return
    n = min(len(sig), N - i0)
    gl = gain * np.sqrt(0.5 * (1 - pan))
    gr = gain * np.sqrt(0.5 * (1 + pan))
    L[i0:i0 + n] += sig[:n] * gl
    R[i0:i0 + n] += sig[:n] * gr


def tt(dur):
    return np.arange(int(dur * SR)) / SR


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, "hp", fs=SR, output="sos"), x)


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, "lp", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "bp", fs=SR, output="sos"), x)


# ---------- instruments ----------
def kick(big=False):
    t = tt(0.6 if big else 0.4)
    f = 48 + 110 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / (0.32 if big else 0.2))
    click = hp(rng.standard_normal(len(t)), 2000) * np.exp(-t / 0.004) * 0.3
    return np.tanh(1.6 * (body + click))


def hat(open_=False):
    t = tt(0.25 if open_ else 0.06)
    x = hp(rng.standard_normal(len(t)), 7000, 4)
    return x * np.exp(-t / (0.07 if open_ else 0.018))


def clap():
    t = tt(0.3)
    x = bp(rng.standard_normal(len(t)), 900, 3500)
    env = np.exp(-t / 0.11)
    for off in (0.0, 0.011, 0.022):
        env += 0.6 * np.exp(-np.maximum(t - off, 0) / 0.006) * (t >= off)
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05) * 0.4
    return x * env * 0.5 + body


def snare_hit():
    t = tt(0.18)
    return bp(rng.standard_normal(len(t)), 1200, 6000) * np.exp(-t / 0.05) + \
        np.sin(2 * np.pi * 210 * t) * np.exp(-t / 0.04) * 0.5


def saw(freq, t, nh=24):
    out = np.zeros_like(t)
    for h in range(1, nh + 1):
        if freq * h > 9000:
            break
        out += np.sin(2 * np.pi * freq * h * t + h) / h
    return out


def pluck(m, dur=0.9, bright=1.0):
    t = tt(dur)
    f = mtof(m)
    x = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.45)
         + 0.45 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.2) * bright
         + 0.2 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t / 0.1) * bright
         + 0.08 * np.sin(2 * np.pi * 4.2 * f * t) * np.exp(-t / 0.05))
    x *= np.minimum(1, t / 0.002)
    glass = hp(rng.standard_normal(len(t)), 6000) * np.exp(-t / 0.025) * 0.18
    return x + glass


# ---------- harmony ----------
CHORDS = {  # bass, voicing, arpeggio notes for plucks
    "Am": (45, [57, 60, 64], [69, 72, 76, 81]),
    "F": (41, [53, 57, 60], [65, 69, 72, 77]),
    "C": (48, [55, 60, 64], [67, 72, 76, 79]),
    "G": (43, [55, 59, 62], [67, 71, 74, 79]),
}


def chord_at_bar(b):
    return PROG[(b + 2) % 4]


n_bars = int(round(T_END / BAR))
DROP_BAR = int(round(T_DROP / BAR))    # 10
BUILD_BAR = int(round(T_BUILD / BAR))  # 8

# pad (two filtered versions crossfaded = opening filter)
pad = np.zeros(N)
bass = np.zeros(N)
for b in range(n_bars):
    name = chord_at_bar(b)
    bn, voic, _ = CHORDS[name]
    t0 = b * BAR
    t = tt(BAR + 0.15)
    env = np.minimum(1, t / 0.08) * np.minimum(1, np.maximum(0, (BAR + 0.15 - t) / 0.15))
    x = np.zeros_like(t)
    for m in voic + [voic[0] + 12]:
        for det in (-0.12, 0.0, 0.11):
            x += saw(mtof(m + det), t, 14)
    i0 = int(t0 * SR)
    n = min(len(x), N - i0)
    pad[i0:i0 + n] += (x * env)[:n]
    # bass: 8th-note offbeat pulses in groove sections
    if b >= 2:
        for e in range(8):
            if b >= DROP_BAR or e % 2 == 1:
                tb = tt(BEAT / 2)
                y = saw(mtof(bn), tb, 30) * np.exp(-tb / 0.18) * np.minimum(1, tb / 0.004)
                j0 = int((t0 + e * BEAT / 2) * SR)
                nn = min(len(y), N - j0)
                if nn > 0:
                    bass[j0:j0 + nn] += y[:nn]

pad_dark = lp(pad, 700)
pad_bright = lp(pad, 3500)
time = np.arange(N) / SR
open_env = np.clip((time - T_BUILD) / (T_DROP - T_BUILD), 0, 1)
open_env = np.where(time >= T_DROP, 1.0, open_env)
pad_mix = pad_dark * (1 - open_env) + pad_bright * open_env
bass = lp(bass, 900)

# sidechain ducking from kicks
kick_times = []
for b in range(n_bars):
    for q in range(4):
        tk = b * BAR + q * BEAT
        if b == BUILD_BAR + 1:          # kick drops out during last build bar
            continue
        kick_times.append(tk)
duck = np.ones(N)
for tk in kick_times:
    i0 = int(tk * SR)
    tdk = tt(BEAT)
    d = 1 - 0.7 * np.exp(-tdk / 0.09)
    n = min(len(d), N - i0)
    duck[i0:i0 + n] = np.minimum(duck[i0:i0 + n], d[:n])

pad_gain = np.where(time < T_DROP, 0.05 + 0.03 * open_env, 0.085)
L += pad_mix * pad_gain * duck
R += pad_mix * pad_gain * duck
bass_gain = np.where(time < T_DROP, 0.16, 0.24) * (time < T_BUILD + BAR) + 0.24 * (time >= T_DROP)
L += bass * bass_gain * duck
R += bass * bass_gain * duck

# drums
for tk in kick_times:
    b = int(tk // BAR)
    g = 0.55 if b < 2 else (0.75 if b < DROP_BAR else 0.9)
    place(kick(), tk, g)
for b in range(n_bars):
    t0 = b * BAR
    if 2 <= b < BUILD_BAR or b >= DROP_BAR:
        for e in range(8):
            if e % 2 == 1:
                place(hat(open_=b >= DROP_BAR), t0 + e * BEAT / 2, 0.11 if b >= DROP_BAR else 0.08,
                      pan=0.25)
            elif b >= DROP_BAR:
                place(hat(), t0 + e * BEAT / 2, 0.05, pan=-0.25)
    if 4 <= b < BUILD_BAR or b >= DROP_BAR:
        for q in (1, 3):
            place(clap(), t0 + q * BEAT, 0.33)

# build-up: snare roll + riser
for b in (BUILD_BAR, BUILD_BAR + 1):
    sub = 8 if b == BUILD_BAR else 16
    for e in range(sub):
        tsn = b * BAR + e * BAR / sub
        prog_ = (tsn - T_BUILD) / (T_DROP - T_BUILD)
        place(snare_hit(), tsn, 0.08 + 0.22 * prog_)
tr = tt(T_DROP - T_BUILD)
prog_r = tr / tr[-1]
n_lo = bp(rng.standard_normal(len(tr)), 500, 2500)
n_hi = hp(rng.standard_normal(len(tr)), 3500)
riser = (n_lo * (1 - prog_r) + n_hi * prog_r) * prog_r ** 2 * 0.25
sweep = np.sin(2 * np.pi * np.cumsum(220 * 2 ** (2.5 * prog_r)) / SR) * prog_r ** 2 * 0.06
place(riser + sweep, T_BUILD, 1.0)

# drop impact: crash + sub boom
tc = tt(2.0)
crash = hp(rng.standard_normal(len(tc)), 4000) * np.exp(-tc / 0.6)
crash2 = hp(rng.standard_normal(len(tc)), 4000) * np.exp(-tc / 0.6)
place(crash, T_DROP, 0.16, pan=-0.6)
place(crash2, T_DROP, 0.16, pan=0.6)
tbm = tt(1.6)
boom = np.sin(2 * np.pi * np.cumsum(38 + 30 * np.exp(-tbm / 0.08)) / SR) * np.exp(-tbm / 0.5)
place(boom, T_DROP, 0.7)
place(kick(big=True), T_DROP, 0.6)

# ---------- plucks on every hit ----------
hits = SIM["hit_info"]
PENT = [0, 3, 5, 7, 10]
arp_pat = [0, 1, 2, 3, 2, 1]
ai = 0
for j, hi in enumerate(hits):
    t = hi["t"]
    x_screen = CX + hi["pos"][0] * hi["z"]
    pan = float(np.clip((x_screen - CX) / 520, -1, 1)) * 0.6
    if t < T_BUILD - 1e-9:
        bar = int((t + 1e-6) // BAR)
        _, _, arp = CHORDS[chord_at_bar(bar)]
        m = arp[arp_pat[ai % len(arp_pat)]]
        ai += 1
        place(pluck(m), t, 0.32, pan)
    elif hi["d1"] < N_RINGS:
        q = j - 32
        m = 57 + 12 * (q // 5) + PENT[q % 5]
        place(pluck(m, 0.6, 1.2), t, 0.26 + 0.1 * q / 15, pan)
    else:   # final: full chord
        for m in (57, 64, 69, 72, 76, 81):
            place(pluck(m, 1.8), t, 0.2, pan * 0.3)

# drop section stabs on offbeats
for b in range(DROP_BAR, n_bars):
    _, voic, arp = CHORDS[chord_at_bar(b)]
    for e in (1, 3, 6):
        ts = b * BAR + e * BEAT / 2
        for m in arp[:3]:
            place(pluck(m, 0.5, 1.3), ts, 0.09, pan=0.2 * (1 if e % 2 else -1))

# ---------- master ----------
fade = np.clip((T_END - time) / 0.7, 0, 1)
L *= fade
R *= fade
mx = max(np.abs(L).max(), np.abs(R).max())
L = np.tanh(1.4 * L / mx) / np.tanh(1.4) * 0.93
R = np.tanh(1.4 * R / mx) / np.tanh(1.4) * 0.93
st = np.stack([L, R], axis=1)
wavfile.write("out/audio.wav", SR, (st * 32767).astype(np.int16))

# ---------- analysis for the visualiser ----------
mono = (L + R) / 2
NB = 48
edges = np.geomspace(40, 12000, NB + 1)
nfft = 4096
freqs = np.fft.rfftfreq(nfft, 1 / SR)
win = np.hanning(nfft)
bands = np.zeros((N_FRAMES, NB))
waves = np.zeros((N_FRAMES, 512))
for fi in range(N_FRAMES):
    c = int(fi / FPS * SR)
    seg_ = np.zeros(nfft)
    a, bnd = c - nfft // 2, c + nfft // 2
    src = mono[max(a, 0):min(bnd, N)]
    seg_[max(0, -a):max(0, -a) + len(src)] = src
    spec = np.abs(np.fft.rfft(seg_ * win))
    for k in range(NB):
        sel = (freqs >= edges[k]) & (freqs < edges[k + 1])
        bands[fi, k] = spec[sel].max() if sel.any() else spec[np.argmin(np.abs(freqs - edges[k]))]
    w0 = mono[c:c + 1024] if c + 1024 <= N else np.zeros(1024)
    waves[fi] = w0[::2]
db = 20 * np.log10(bands + 1e-6)
db = np.clip((db - (db.max() - 60)) / 60, 0, 1)
tilt = np.linspace(0.85, 1.25, NB)        # lift highs a little
lev = np.clip(db * tilt, 0, 1) ** 1.6
sm = np.zeros_like(lev)
for fi in range(N_FRAMES):
    sm[fi] = lev[fi] if fi == 0 else np.maximum(lev[fi], sm[fi - 1] * np.exp(-1 / FPS / 0.12))
np.savez("out/analysis.npz", bands=sm, waves=waves, kicks=np.array(kick_times))
print("audio ok", N / SR, "s; peak", np.abs(st).max())
