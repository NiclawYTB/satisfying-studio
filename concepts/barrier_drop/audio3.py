"""Calm soundtrack for the falling ball: glass pings rising on each hit of a barrier,
crystal shimmer when it breaks, soft ticks on the walls, drone underneath."""
import pickle
import numpy as np
from common3 import *
from calm import Mixer, kalimba, glass, sprinkle, pop, tick, swell, pad, scale_note, write_wav
from timewarp import Warp

rng = np.random.default_rng(SEED + 21)
SIM = pickle.load(open("sim3.pkl", "rb"))
T_DONE, T_END = SIM["t_done"], SIM["t_end"]
WARP = Warp([(T_DONE - 0.12, T_DONE + 0.45, 0.28)], T_END)
V = lambda t: float(WARP.v_of_t(t))
V_END = V(T_END)
BASE = 60 + KEY
mx = Mixer(V_END, SEED)
mx.put(pad([BASE - 12, BASE - 5, BASE, BASE + 4], V_END + 1), 0.0, 1.0, 0, send=0.4)

count = {}
for h in SIM["hits"]:
    j = count.get(h["k"], 0)
    count[h["k"]] = j + 1
    pan = (h["x"] - W / 2) / 600
    m = scale_note(5 + (h["k"] % 3) + 2 * j, BASE)
    mx.put(kalimba(m, 1.0), V(h["t"]), 0.30, pan)
    mx.put(pop(m - 12, 0.8), V(h["t"]), 0.10, pan, send=0.2)
for b in SIM["breaks"]:
    pan = (b["x"] - W / 2) / 600
    if b["k"] < NB - 1:
        mx.put(glass(scale_note(10 - (b["k"] % 6), BASE)), V(b["t"]), 0.17, pan, send=0.6)
        mx.put(sprinkle(rng, BASE + 24, n=10, spread=0.3), V(b["t"]), 0.11, -pan, send=0.7)
    else:
        for i, s in enumerate((0, 2, 4, 5, 7)):
            mx.put(glass(scale_note(5 + s, BASE), 4.0), V(b["t"]) + 0.05 * i, 0.15, (i - 2) * 0.25, send=0.7)
        mx.put(sprinkle(rng, BASE + 24, n=24, spread=0.9, dur=2.6), V(b["t"]), 0.14, 0, send=0.8)
        mx.put(swell(1.0), V(b["t"]) - 0.35, 0.7)
        mx.put(pad([BASE, BASE + 4, BASE + 7, BASE + 12], 4.0, 1.6), V(b["t"]), 1.0, 0, send=0.6)
for w in SIM["walls"]:
    if w[0] < T_DONE:
        mx.put(tick(scale_note(2, BASE), 0.5), V(w[0]), 0.10, (w[1] - W / 2) / 600, send=0.3)
desc = [9, 7, 5, 4, 2, 0]
for i, f in enumerate(SIM["floor"]):
    vel = float(np.clip(f["vy"] / 1500, 0.3, 1.0))
    mx.put(kalimba(scale_note(desc[min(i, 5)], BASE), vel), V(f["t"]), 0.26 * vel, (f["x"] - W / 2) / 600)
write_wav("out/audio.wav", mx.render())
print("audio", round(V_END, 2), "s calm")
