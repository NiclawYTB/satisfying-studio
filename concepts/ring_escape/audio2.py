"""Calm soundtrack for the circle: kalimba melody note by note on each bounce,
crystal pings when the ball slips out, airy swell into slow motion, soft drone."""
import pickle
import numpy as np
from common2 import *
from calm import Mixer, kalimba, glass, sprinkle, swell, pad, scale_note, write_wav
from timewarp import Warp

rng = np.random.default_rng(SEED + 11)
SIM = pickle.load(open("sim2.pkl", "rb"))
T_ESC = SIM["t_esc"]
T_END = T_ESC + OUTRO
WARP = Warp(SIM["warp_windows"], T_END)
V = lambda t: float(WARP.v_of_t(t))
V_END = V(T_END)
BASE = 60 + KEY

mx = Mixer(V_END, SEED)
# drone: tonic + fifth + third, always consonant with the pentatonic notes
mx.put(pad([BASE - 12, BASE - 5, BASE, BASE + 4], V_END + 1), 0.0, 1.0, 0, send=0.4)

MELODY = [5, 6, 7, 8, 7, 6, 5, 4, 5, 7, 9, 8, 7, 5, 6, 4, 6, 7, 8, 10, 9, 8, 7, 6, 5, 6, 7, 5, 4, 3, 4, 5]
for i, b in enumerate(SIM["bounces"]):
    m = scale_note(MELODY[i % len(MELODY)] + 2 * (i // len(MELODY) % 2), BASE)
    vel = np.clip(b[4] / 1400, 0.5, 1.2)
    mx.put(kalimba(m, vel), V(b[0]), 0.30 * (0.7 + 0.3 * vel), b[2][0] / 600)

for e in SIM["escapes"]:
    t, k = e[0], e[1]
    v = V(t)
    pan = e[2][0] / 600
    if k < N_RINGS - 1:
        mx.put(glass(scale_note(8 + k % 7, BASE)), v, 0.20, pan, send=0.6)
        mx.put(sprinkle(rng, BASE + 24, n=8, spread=0.25), v, 0.10, -pan, send=0.7)
    else:
        for j, s in enumerate((0, 2, 4, 5, 7)):
            mx.put(glass(scale_note(5 + s, BASE), 4.0), v + 0.05 * j, 0.16, (j - 2) * 0.25, send=0.7)
        mx.put(sprinkle(rng, BASE + 24, n=22, spread=0.8, dur=2.5), v, 0.14, 0, send=0.8)
        mx.put(pad([BASE, BASE + 4, BASE + 7, BASE + 12], 4.5, 1.6), v, 1.0, 0, send=0.6)

for (a, b_, sp) in SIM["warp_windows"]:
    mx.put(swell(1.0), V(a) - 0.3, 0.7, 0, send=0.5)

desc = [12, 10, 9, 8, 7, 6, 5, 4]
for i, fb in enumerate(SIM["floor"]):
    vel = np.clip(fb[2] / 1400, 0.4, 1.0)
    mx.put(kalimba(scale_note(desc[min(i, 7)], BASE), vel), V(fb[0]), 0.26 * vel, fb[1][0] / 600)

write_wav("out/audio.wav", mx.render())
print("audio", round(V_END, 2), "s calm")
