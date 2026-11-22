"""Gravity ball escaping rotating gapped rings.
Each bounce gets a tiny nudge (a few degrees, a few % speed) picked by look-ahead
so escapes follow a pacing curve instead of stalling for 10 s."""
import pickle, sys
import numpy as np
from common2 import *

DT = 1 / 1200
SAMPLE = 4                     # path samples at 300 Hz


def target_escapes(t):
    return N_RINGS * min(1.0, max(0.0, t - 0.6) / (T_TARGET - 0.6)) ** 1.25


class S:
    __slots__ = ("p", "v", "k", "crossing", "t")

    def __init__(self, p, v, k, crossing, t):
        self.p, self.v, self.k, self.crossing, self.t = p, v, k, crossing, t

    def copy(self):
        return S(self.p.copy(), self.v.copy(), self.k, self.crossing, self.t)


def step(s):
    """Advance one step. Returns None, ('escape', k) or ('bounce', n, gapdist)."""
    s.v[1] += GRAV * DT
    s.p += s.v * DT
    s.t += DT
    if s.k >= N_RINGS:
        return None
    r = np.hypot(s.p[0], s.p[1])
    rk = RADII[s.k]
    inner = rk - LW / 2 - BALL_R
    if s.crossing:
        if r >= rk:
            s.crossing = False
            s.k += 1
            return ("escape", s.k - 1)
        if r < inner:
            s.crossing = False
        return None
    if r > inner:
        ang = np.arctan2(s.p[1], s.p[0])
        d = wrap(ang - gap_center(s.k, s.t))
        lim = P["gap"] - BALL_R / rk
        if abs(d) < lim:
            s.crossing = True
            return None
        n = s.p / r
        vn = s.v[0] * n[0] + s.v[1] * n[1]
        s.p = n * inner
        if vn > 0:
            s.v = s.v - 2 * vn * n
            sp = np.hypot(s.v[0], s.v[1])
            if sp < P["vmin"]:
                s.v *= P["vmin"] / sp
            return ("bounce", n, abs(d) - lim)
    return None


def lookahead(s, t_max=1.6):
    s = s.copy()
    t_end = s.t + t_max
    while s.t < t_end:
        ev = step(s)
        if ev:
            return ev, s.t
    return ("none",), s.t


def nudge(v, a, f):
    c, sn = np.cos(a), np.sin(a)
    return np.array([c * v[0] - sn * v[1], sn * v[0] + c * v[1]]) * f


ANGLES = np.linspace(-0.13, 0.13, 9)
FACTORS = (0.96, 1.0, 1.05)


def simulate(seed=1):
    rng = np.random.default_rng(seed)
    s = S(np.array([0.0, -40.0]), np.array([300.0, -260.0]), 0, False, 0.0)
    bounces, escapes, floor, path = [], [], [], []
    t_esc = None
    want_since = None
    i = 0
    wall_x = (BALL_R - CX, W - CX - BALL_R)
    wall_y = (BALL_R - CY, H - CY - BALL_R)
    while True:
        if s.k < N_RINGS:
            ev = step(s)
            if ev and ev[0] == "escape":
                escapes.append((s.t, ev[1], s.p.copy(), s.v.copy()))
                if s.k == N_RINGS:
                    t_esc = s.t
            elif ev and ev[0] == "bounce":
                n = ev[1]
                want = len(escapes) < target_escapes(s.t + 0.5)
                if want and want_since is None:
                    want_since = s.t
                if not want:
                    want_since = None
                over = 0.0 if want_since is None else min(1.0, (s.t - want_since) / 1.5)
                amax = 0.13 + 0.17 * over
                fmax = 0.05 + 0.08 * over
                best, best_sc = None, 1e9
                for a in np.linspace(-amax, amax, 11):
                    for f in (1 - fmax, 1.0, 1 + fmax):
                        c = s.copy()
                        c.v = nudge(c.v, a, f)
                        (res, te) = lookahead(c)
                        natural = abs(a) / 0.13 * 0.3 + abs(f - 1) * 3
                        if want:
                            sc = natural if res[0] == "escape" else \
                                2 + (res[2] if res[0] == "bounce" else 3)
                        else:
                            sc = natural if res[0] == "bounce" else 5 + natural
                        if res[0] == "bounce" and te - s.t < 0.16:
                            sc += 6          # avoid rolling / grazing chatter
                        sc += rng.uniform(0, 0.15)
                        if sc < best_sc:
                            best_sc, best = sc, (a, f)
                s.v = nudge(s.v, *best)
                bounces.append((s.t, s.k, s.p.copy(), n.copy(), float(np.hypot(*s.v))))
        else:
            s.v[1] += GRAV * DT
            s.p += s.v * DT
            s.t += DT
            hit = False
            for ax, (lo, hi) in ((0, wall_x), (1, wall_y)):
                if s.p[ax] < lo and s.v[ax] < 0:
                    s.p[ax] = lo; s.v[ax] = -s.v[ax] * 0.84; hit = True
                elif s.p[ax] > hi and s.v[ax] > 0:
                    s.p[ax] = hi; s.v[ax] = -s.v[ax] * 0.84; hit = True
            if hit and np.hypot(*s.v) > 280:
                floor.append((s.t, s.p.copy(), float(np.hypot(*s.v))))
            if s.t > t_esc + OUTRO + 0.3:
                break
        i += 1
        if i % SAMPLE == 0:
            path.append((s.t, s.p[0], s.p[1]))
        if s.t > 45:
            break
    return dict(bounces=bounces, escapes=escapes, floor=floor, t_esc=t_esc, path=np.array(path))


def search(seed0, tries=30):
    best, best_sc = None, 1e9
    for seed in range(seed0, seed0 + tries):
        r = simulate(seed)
        if r["t_esc"] is None:
            continue
        et = np.array([0] + [e[0] for e in r["escapes"]])
        mw = np.diff(et).max()
        sc = max(0, mw - 2.8) * 4 + max(0, abs(r["t_esc"] - T_TARGET) - 3.0)
        if sc < best_sc:
            best, best_sc = r, sc
        if sc == 0:
            break
    return best


def slow_windows(r):
    """Slow motion when the ball slips through a gap: the last ring + up to 3 others (chains first)."""
    esc = [e[0] for e in r["escapes"]]
    te_f = esc[-1]
    wins = [(te_f - 0.42, te_f + 0.35, 0.2)]
    cands = []
    for i, te in enumerate(esc[:-1]):
        j = i
        while j + 1 < len(esc) - 1 and esc[j + 1] - esc[j] < 0.3:
            j += 1
        cands.append((j - i + 1, te, esc[j]))
    picked = []
    for n, te, ce in sorted(cands, key=lambda c: (-c[0], c[1])):
        if te < 2.0 or ce > te_f - 3.0:
            continue
        if all(abs(te - p[0]) > 4.0 for p in picked):
            picked.append((te, ce))
        if len(picked) == int(PRM.get("n_slowmo", 1)):
            break
    for te, ce in picked:
        wins.append((te - 0.25, ce + 0.28, 0.3))
    return sorted(wins)


if __name__ == "__main__":
    r = search(SEED)
    r["warp_windows"] = slow_windows(r)
    print("slowmo", [tuple(round(x, 2) for x in w) for w in r["warp_windows"]])
    et = np.array([0] + [e[0] for e in r["escapes"]])
    print("t_esc", r["t_esc"], "bounces", len(r["bounces"]), "floor", len(r["floor"]))
    print("escapes:", [round(e[0], 2) for e in r["escapes"]])
    print("max wait", np.diff(et).max().round(2))
    with open("sim2.pkl", "wb") as f:
        pickle.dump(r, f)
