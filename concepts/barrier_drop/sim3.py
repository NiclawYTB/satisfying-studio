"""Ball falling through glass barriers with hit points."""
import pickle
import numpy as np
from common3 import *

rng = np.random.default_rng(SEED + 5)
DT = 1 / 1200


def apex(k):
    return 135 - 50 * k / max(1, NB - 1)           # bounce height shrinks: rhythm speeds up


def crack_lines(x_local):
    lines = []
    for _ in range(rng.integers(2, 4)):
        pts = [(x_local, rng.uniform(0, BAR_H))]
        ang = rng.uniform(0, 2 * np.pi)
        for _ in range(rng.integers(3, 6)):
            ang += rng.uniform(-0.7, 0.7)
            L = rng.uniform(15, 45)
            px = pts[-1][0] + np.cos(ang) * L
            py = np.clip(pts[-1][1] + np.sin(ang) * L * 0.35, 1, BAR_H - 1)
            pts.append((px, py))
        lines.append(np.array(pts, dtype=np.float32))
    return lines


def shards(k, x_imp, t):
    out = []
    xs = [WALL_L]
    while xs[-1] < WALL_R - 20:
        xs.append(min(WALL_R, xs[-1] + rng.uniform(28, 64)))
    y0, y1 = BAR_Y[k] - BAR_H / 2, BAR_Y[k] + BAR_H / 2
    for a, b in zip(xs[:-1], xs[1:]):
        m = rng.uniform(y0, y1)
        tris = [[(a, y0), (b, y0), (b, m)], [(a, y0), (b, m), (a, y1)], [(a, y1), (b, m), (b, y1)]]
        for tri in tris:
            tri = np.array(tri, dtype=np.float32)
            c = tri.mean(axis=0)
            d = c[0] - x_imp
            near = np.exp(-(d / 160) ** 2)
            vx = d * 1.3 + rng.uniform(-90, 90)
            vy = -rng.uniform(80, 420) * (0.4 + near) + rng.uniform(0, 120)
            out.append(dict(t=t, c=c, v=np.array([vx, vy]), verts=tri - c, w=rng.uniform(-7, 7), k=k,
                            life=rng.uniform(1.4, 2.4)))
    return out


x, y = W / 2 + rng.uniform(-90, 90), Y0 - 560.0
vx, vy = rng.choice([-1, 1]) * rng.uniform(140, 260), 0.0
k, hp = 0, HP[0]
t = 0.0
hits, breaks, walls, floor, path, shard_list = [], [], [], [], [], []
cracks = {i: [] for i in range(NB)}        # list of (t, lines)
t_done = None
step = 0
while True:
    vy += GRAV * DT
    x += vx * DT
    y += vy * DT
    t += DT
    step += 1
    if x < WALL_L + BALL_R and vx < 0:
        x, vx = WALL_L + BALL_R, -vx
        walls.append((t, x, y))
    elif x > WALL_R - BALL_R and vx > 0:
        x, vx = WALL_R - BALL_R, -vx
        walls.append((t, x, y))
    if k < NB:
        top = BAR_Y[k] - BAR_H / 2
        if y + BALL_R >= top and vy > 0:
            hp -= 1
            hits.append(dict(t=t, k=k, x=x, hp=hp, vy=vy))
            cracks[k].append((t, crack_lines(x - WALL_L)))
            if hp <= 0:
                breaks.append(dict(t=t, k=k, x=x))
                shard_list += shards(k, x, t)
                k += 1
                vy *= 0.7
                if k < NB:
                    hp = HP[k]
                else:
                    t_done = t
            else:
                y = top - BALL_R
                vy = -np.sqrt(2 * GRAV * apex(k)) * rng.uniform(0.95, 1.05)
                vx = float(np.clip(vx + rng.uniform(-140, 140), -380, 380))
    else:
        if y + BALL_R >= FLOOR_Y - 14 and vy > 0:
            y = FLOOR_Y - 14 - BALL_R
            if vy > 260:
                floor.append(dict(t=t, x=x, vy=vy))
            vy = -vy * 0.55
            vx *= 0.8
        if t > t_done + OUTRO:
            break
    if step % 4 == 0:
        path.append((t, x, y))
    if t > 60:
        break

path = np.array(path)
# camera: critically damped follow of the current barrier
cam = np.zeros(len(path))
pos, vel = Y0 - CAM_FRAC * H, 0.0
w0 = 2 * np.pi * 0.9
bt = np.array([b["t"] for b in breaks])
for i, (tt_, _, _) in enumerate(path):
    kk = int(np.searchsorted(bt, tt_, side="right"))
    target = (BAR_Y[kk] if kk < NB else FLOOR_Y + 60) - CAM_FRAC * H
    dtp = path[1, 0] - path[0, 0]
    acc = w0 * w0 * (target - pos) - 2 * w0 * vel
    vel += acc * dtp
    pos += vel * dtp
    cam[i] = pos
print("t_done", round(t_done, 2), "hits", len(hits), "breaks", len(breaks), "HP", HP)
with open("sim3.pkl", "wb") as f:
    pickle.dump(dict(path=path, cam=cam, hits=hits, breaks=breaks, walls=walls, floor=floor,
                     cracks=cracks, shards=shard_list, t_done=t_done, t_end=t_done + OUTRO), f)
