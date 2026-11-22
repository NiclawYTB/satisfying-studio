"""Deterministic simulation: zoom curve, ball path, ring breaks, particles."""
import pickle
import numpy as np
from common import *

rng = np.random.default_rng(SEED)
HIT_T, HIT_K = hit_schedule()
D_AFTER = np.cumsum(HIT_K)                       # rings destroyed after hit j
D_BEFORE = np.concatenate([[0], D_AFTER[:-1]])

# ---------------- zoom curve ----------------
DT = 1 / 600
tgrid = np.arange(0, T_END + 1, DT)
z = np.empty_like(tgrid)
zc = 1.0
k = 1 - np.exp(-DT / ZOOM_TAU)
for i, t in enumerate(tgrid):
    d = D_AFTER[HIT_T <= t + 1e-9][-1] if t >= HIT_T[0] else 0
    if d >= N_RINGS:
        target = HOLE_TARGET / (RADII[-1] + LW)
    else:
        target = min(1.0, HOLE_TARGET / hole_radius(d))
    zc += (target - zc) * k
    z[i] = zc


def zoom_at(t):
    return float(np.interp(t, tgrid, z))


# ---------------- ball path ----------------
def rot(v, a):
    c, s = np.cos(a), np.sin(a)
    return np.array([c * v[0] - s * v[1], s * v[0] + c * v[1]])


def contact_radius(j):
    """Ball-centre radius (world) when hitting wall before hit j."""
    return hole_radius(D_BEFORE[j]) - BALL_R / zoom_at(HIT_T[j])


P0 = np.array([0.0, 105.0])           # start just under the counter
pts = [P0.copy()]
dirs = []
a0 = np.deg2rad(rng.uniform(-125, -55))
d = np.array([np.cos(a0), np.sin(a0)])
P = P0.copy()
# first leg
Rb0 = contact_radius(0)
b0 = np.dot(P, d)
s = -b0 + np.sqrt(b0 * b0 - (np.dot(P, P) - Rb0 * Rb0))
P = P + d * s
pts.append(P.copy())
dirs.append(d.copy())
hit_info = []
sigma_keep = None
for j in range(len(HIT_T)):
    u = P / np.linalg.norm(P)
    tang = np.array([-u[1], u[0]])
    d_ref = d - 2 * np.dot(d, u) * u
    sig = np.sign(np.dot(d_ref, tang)) or 1.0
    phi_ref = np.arccos(np.clip(np.dot(d_ref, -u), -1, 1))
    if HIT_T[j] < T_BUILD - 1e-9:
        phi = np.clip(phi_ref + rng.uniform(-0.45, 0.45), np.deg2rad(6), np.deg2rad(38))
        if rng.random() < 0.3:
            sig = -sig
    else:
        if sigma_keep is None:
            sigma_keep = sig
        sig = sigma_keep
        frac = (HIT_T[j] - T_BUILD) / (T_DROP - T_BUILD)
        phi = np.deg2rad(62 + 6 * frac) + rng.uniform(-0.05, 0.05)
    d_new = np.cos(phi) * (-u) + sig * np.sin(phi) * tang
    hit_info.append(dict(t=HIT_T[j], pos=P.copy(), u=u, d_in=d.copy(), d_out=d_new.copy(),
                         k=int(HIT_K[j]), d0=int(D_BEFORE[j]), d1=int(D_AFTER[j]),
                         z=zoom_at(HIT_T[j])))
    if j + 1 < len(HIT_T):
        Rb = contact_radius(j + 1)
        b = np.dot(P, d_new)
        c = np.dot(P, P) - Rb * Rb
        s = -b + np.sqrt(b * b - c)
        P = P + d_new * s
        pts.append(P.copy())
    d = d_new
    dirs.append(d.copy())

pts = np.array(pts)
key_t = np.concatenate([[0.0], HIT_T])           # time at each point in pts

# screen speeds report
for j in range(1, len(pts)):
    seg = np.linalg.norm(pts[j] - pts[j - 1])
    dt = key_t[j] - key_t[j - 1]
    zm = zoom_at(key_t[j])
    if j % 6 == 0 or j > 44:
        print(f"leg {j:2d} t={key_t[j]:6.3f}  world {seg:7.1f}  screen speed {seg*zm/dt:7.0f}px/s"
              f"  ({seg*zm/dt/FPS:5.1f}px/frame)  zoom {zm:.3f}")

# post-drop glide to centre (quadratic bezier, world coords)
P48 = pts[-1]
d48 = hit_info[-1]["d_out"]
GLIDE = (T_DROP, T_DROP + 0.75)
glide_ctrl = P48 + d48 * np.linalg.norm(P48) * 0.55


def ball_world(t):
    if t <= T_DROP:
        j = np.searchsorted(key_t, t, side="right") - 1
        j = min(j, len(key_t) - 2)
        a = (t - key_t[j]) / (key_t[j + 1] - key_t[j])
        return pts[j] + (pts[j + 1] - pts[j]) * a
    a = min(1.0, (t - GLIDE[0]) / (GLIDE[1] - GLIDE[0]))
    a = 1 - (1 - a) ** 3
    return (1 - a) ** 2 * P48 + 2 * (1 - a) * a * glide_ctrl + a * a * np.zeros(2)


# ---------------- particles (screen space) ----------------
# columns: t0, x0, y0, vx, vy, life, drag, r, g, b, size(0 small/1 spark)
parts = []
for hi in hit_info:
    zt = hi["z"]
    final = hi["d1"] >= N_RINGS
    imp_ang = np.arctan2(hi["u"][1], hi["u"][0])
    dout = hi["d_out"]
    for ri in range(hi["d0"], hi["d1"]):
        rho = RADII[ri] * zt
        n = int(min(110, 2 * np.pi * rho / 10))
        th = rng.uniform(0, 2 * np.pi, n)
        cs, sn = np.cos(th), np.sin(th)
        x0 = CX + rho * cs
        y0 = CY + rho * sn
        if final:
            vr = rng.uniform(-350, 650, n)
            vt = rng.uniform(-200, 200, n)
            life = rng.uniform(0.7, 1.6, n)
        else:
            vr = -rng.uniform(30, 230, n)
            vt = rng.uniform(-80, 80, n)
            life = rng.uniform(0.4, 0.85, n)
        vx = vr * cs - vt * sn
        vy = vr * sn + vt * cs
        dang = np.angle(np.exp(1j * (th - imp_ang)))
        w = np.exp(-(dang / 0.5) ** 2)
        boost = rng.uniform(250, 750, n) * w
        vx += dout[0] * boost
        vy += dout[1] * boost
        col = RING_COLORS[ri] * 0.75 + 0.25
        for q in range(n):
            parts.append((hi["t"], x0[q], y0[q], vx[q], vy[q], life[q], 2.4,
                          col[0], col[1], col[2], 0))
    # cyan sparks at the impact point
    ip = np.array([CX, CY]) + hi["pos"] * zt + hi["u"] * BALL_R
    ns = 70 if final else 22
    for q in range(ns):
        dd = rot(dout, rng.uniform(-1.0, 1.0))
        sp = rng.uniform(250, 1100 if final else 800)
        parts.append((hi["t"], ip[0], ip[1], dd[0] * sp, dd[1] * sp, rng.uniform(0.18, 0.5),
                      3.5, *(BALL_COLOR * 0.85 + 0.15), 1))

parts = np.array(parts, dtype=np.float64)
print("particles:", len(parts))

with open("sim.pkl", "wb") as f:
    pickle.dump(dict(hit_info=hit_info, pts=pts, key_t=key_t, tgrid=tgrid, z=z,
                     parts=parts, P48=P48, glide_ctrl=glide_ctrl, glide=GLIDE), f)
print("hits", len(hit_info), "final zoom", z[-1])
