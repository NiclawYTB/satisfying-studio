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
    pan = (h["x"] - W / 2) * 0.6 / 600
    m = scale_note(2 + (h["k"] % 3) + j, BASE)          # mid register, never shrill
    mx.put(kalimba(m, 0.35), V(h["t"]), 0.26, pan, send=0.45)
for b in SIM["breaks"]:
    pan = (b["x"] - W / 2) * 0.6 / 600
    if b["k"] < NB - 1:
        mx.put(glass(scale_note(5 - (b["k"] % 4), BASE - 12)), V(b["t"]), 0.15, pan, send=0.6)
        mx.put(kalimba(scale_note(4, BASE - 12), 0.3), V(b["t"]), 0.12, -pan, send=0.5)
    else:
        for i, s in enumerate((0, 2, 4, 5, 7)):
            mx.put(glass(scale_note(s, BASE - 12), 4.0), V(b["t"]) + 0.06 * i, 0.12, (i - 2) * 0.2, send=0.7)
        mx.put(swell(1.0), V(b["t"]) - 0.35, 0.5)
        mx.put(pad([BASE - 12, BASE - 8, BASE - 5, BASE], 4.0, 1.6), V(b["t"]), 1.0, 0, send=0.6)
desc = [7, 5, 4, 2, 0, 0]
for i, f in enumerate(SIM["floor"]):
    vel = float(np.clip(f["vy"] / 1500, 0.3, 1.0))
    mx.put(kalimba(scale_note(desc[min(i, 5)], BASE - 12), 0.3), V(f["t"]), 0.24 * vel, (f["x"] - W / 2) / 900)
write_wav("out/audio.wav", mx.render(peak=0.45, lowpass=3800))
print("audio", round(V_END, 2), "s calm")
