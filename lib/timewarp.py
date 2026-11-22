"""Slow-motion time remapping between simulation time (t) and video time (v)."""
import numpy as np


class Warp:
    def __init__(self, windows, t_end, dt=1 / 1000):
        """windows: list of (a, b, speed) in sim time; speed < 1 = slow motion."""
        self.windows = [tuple(map(float, w)) for w in windows]
        t = np.arange(0, t_end + 1.0, dt)
        s = np.ones_like(t)
        for a, b, sp in self.windows:
            r = min(0.12, (b - a) / 3)
            w = np.clip(np.minimum((t - a) / r, (b - t) / r), 0, 1)
            w = w * w * (3 - 2 * w)
            s = np.minimum(s, 1 - (1 - sp) * w)
        self.t, self.s = t, s
        self.v = np.concatenate([[0.0], np.cumsum(dt / s[:-1])])

    def v_of_t(self, t):
        return np.interp(t, self.t, self.v)

    def t_of_v(self, v):
        return np.interp(v, self.v, self.t)

    def slow_amount(self, t):
        """0 = normal speed, 1 = deepest slow motion (sim time)."""
        s = np.interp(t, self.t, self.s)
        mn = min([w[2] for w in self.windows], default=1.0)
        return np.clip((1 - s) / max(1e-6, 1 - mn), 0, 1)

    def to_dict(self):
        return dict(windows=self.windows, t_end=float(self.t[-1] - 1.0))

    @staticmethod
    def from_dict(d):
        return Warp(d["windows"], d["t_end"])
