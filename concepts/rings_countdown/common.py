import json, os
import numpy as np

PRM = json.load(open(os.environ.get("SATISFY_PARAMS", "params.json")))
FONT_DIR = os.environ.get("SATISFY_FONTS", os.path.join(os.path.dirname(__file__), "..", "..", "fonts"))
SEED = int(PRM.get("seed", 7))
KEY = int(PRM.get("key_shift", 0))

W, H = 1080, 1920
FPS = 30
CX, CY = 540.0, 940.0

BPM = float(PRM.get("bpm", 128))
BEAT = 60.0 / BPM            # 0.46875 s
BAR = 4 * BEAT
T_BUILD = 32 * BEAT          # 15.0 s : hits switch to 8th notes
T_DROP = 40 * BEAT           # 18.75 s : last ring breaks, drop
T_END = 52 * BEAT            # 24.375 s
N_FRAMES = int(round(T_END * FPS))

N_RINGS = int(PRM.get("n_rings", 145))
R0 = 190.0
SPACING = (1128.0 - R0) / (N_RINGS - 1)
LW = 2.4
RADII = R0 + SPACING * np.arange(N_RINGS)

HOLE_TARGET = 470.0          # max on-screen hole radius (camera pulls back beyond)
BALL_R = 16.0                # on-screen ball radius
ZOOM_TAU = 0.18

SR = 44100

# ring palette along radius (0 = inner, 1 = outer)
_PAL_STOPS = [tuple([p[0], tuple(p[1])]) for p in PRM.get("palette", [
    (0.00, (255, 40, 110)),
    (0.14, (255, 70, 80)),
    (0.32, (255, 140, 60)),
    (0.50, (255, 214, 90)),
    (0.68, (255, 150, 60)),
    (0.86, (255, 60, 120)),
    (1.00, (225, 40, 160)),
])]
BALL_COLOR = np.array(PRM.get("ball_color", [0.45, 1.0, 0.92]))
PROG = PRM.get("progression", ["Am", "F", "C", "G"])


def palette(t):
    t = np.clip(np.asarray(t, dtype=np.float64), 0, 1)
    xs = [s[0] for s in _PAL_STOPS]
    out = np.stack([np.interp(t, xs, [s[1][c] for s in _PAL_STOPS]) for c in range(3)], axis=-1)
    return out / 255.0


RING_COLORS = palette(np.arange(N_RINGS) / (N_RINGS - 1))


def hit_schedule():
    """Hit times (on the beat, then 8th notes) and rings destroyed per hit."""
    times = [j * BEAT for j in range(1, 33)] + [T_BUILD + m * BEAT / 2 for m in range(1, 17)]
    ks = [1] * 8 + [2] * 8 + [3] * 8 + [4] * 8 + [3] * 15
    ks.append(N_RINGS - sum(ks))
    assert len(times) == len(ks) == 48 and abs(times[-1] - T_DROP) < 1e-9
    return np.array(times), np.array(ks)


def hole_radius(destroyed):
    if destroyed >= N_RINGS:
        return RADII[-1] + LW
    return RADII[destroyed] - LW / 2
