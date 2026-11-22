"""Calm soundtrack for the Galton board: a soft tick per marble on the pegs, a water-drop note when
it lands (pitch = bin, like a xylophone from left to right), glass arpeggio as the curve appears."""
import pickle
import numpy as np
from common4 import *
from calm import Mixer, kalimba, glass, sprinkle, pop, tick, pad, scale_note, write_wav

rng = np.random.default_rng(SEED + 31)
SIM = pickle.load(open("sim4.pkl", "rb"))
T_ALL, T_END = SIM["t_all"], SIM["t_end"]
BASE = 60 + KEY
mx = Mixer(T_END, SEED)
mx.put(pad([BASE - 12, BASE - 5, BASE, BASE + 4], T_END + 1), 0.0, 1.0, 0, send=0.4)
t0s = np.array([b["t0"] for b in SIM["balls"]])
for i, b in enumerate(SIM["balls"]):
    dens = np.sum(np.abs(t0s - b["t0"]) < 0.5)          # marbles per second around this one
    g = min(1.0, 9.0 / max(1, dens))
    r = int(rng.integers(1, ROWS - 1))
    pan = (b["js"][r] - r / 2) * DX / 500
    mx.put(tick(scale_note(12 - r // 2, BASE), 0.8), b["t_first"] + r * TAU, 0.09 * g ** 0.7, pan, send=0.3)
    land_note = scale_note(2 + b["bin"], BASE - 12)
    mx.put(pop(land_note + 12, 1.0), b["t_land"], 0.24 * g ** 0.6, (b["rest"][0] - CX) / 560, send=0.35)
    if i < 12:
        mx.put(kalimba(land_note + 12, 0.8), b["t_land"], 0.16, (b["rest"][0] - CX) / 560)
for k in range(9):
    mx.put(glass(scale_note(4 + k, BASE)), T_ALL + 0.25 + k * 1.4 / 9, 0.12, -0.6 + k * 0.15, send=0.7)
mx.put(sprinkle(rng, BASE + 24, n=20, spread=1.2, dur=3.0), T_ALL + 1.6, 0.12, 0, send=0.8)
mx.put(pad([BASE, BASE + 4, BASE + 7, BASE + 12], 4.0, 1.5), T_ALL + 1.4, 1.0, 0, send=0.6)
write_wav("out/audio.wav", mx.render(peak=0.62))
print("audio", round(T_END, 2), "s calm")
