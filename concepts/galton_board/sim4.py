"""Galton board: release schedule, left/right decisions, landing slots."""
import pickle
import numpy as np
from common4 import *

rng = np.random.default_rng(SEED + 3)
# release times from a linearly increasing rate
ts = []
t = 0.4
while t < T_RELEASE:
    ts.append(t)
    rate = RATE0 + (RATE1 - RATE0) * t / T_RELEASE
    t += 1.0 / rate
N = len(ts)
balls = []
fill = [0] * NBINS
for i, t0 in enumerate(ts):
    d = rng.integers(0, 2, ROWS)
    js = np.concatenate([[0], np.cumsum(d)])          # peg index per row (row 0..ROWS-1), last = bin
    b = int(js[-1])
    n = fill[b]
    fill[b] += 1
    layer, col = divmod(n, PER_LAYER)
    off = 0.0 if layer % 2 == 0 else 3.5
    rx = bin_x(b) - DX / 2 + 10 + off + col * 14.0
    ry = BIN_BOT - BALL_R - 1 - layer * LAYER_H
    t_first = t0 + 0.10
    t_last = t_first + (ROWS - 1) * TAU
    y_last = PY0 + (ROWS - 1) * DY - PEG_R - BALL_R
    t_land = t_last + np.sqrt(2 * max(10.0, ry - y_last) / GRAV) + 0.04
    balls.append(dict(t0=t0, js=js[:ROWS].astype(int), d_last=int(d[-1]), bin=b, rest=(rx, ry),
                      t_first=t_first, t_last=t_last, t_land=t_land, slot=n))
t_all = max(bb["t_land"] for bb in balls)
print("balls", N, "last landing", round(t_all, 2), "max bin", max(fill), "fill", fill)
with open("sim4.pkl", "wb") as f:
    pickle.dump(dict(balls=balls, n=N, fill=fill, t_all=t_all, t_end=t_all + OUTRO), f)
