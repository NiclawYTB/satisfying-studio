import colorsys, json, os
import numpy as np

PRM = json.load(open(os.environ.get("SATISFY_PARAMS", "params.json")))
FONT_DIR = os.environ.get("SATISFY_FONTS", os.path.join(os.path.dirname(__file__), "..", "..", "fonts"))
SEED = int(PRM.get("seed", 29))
KEY = int(PRM.get("key_shift", 0))
T_TARGET = float(PRM.get("target_time", 22.0))
PROG = PRM.get("progression", ["Am", "F", "C", "G"])

W, H = 1080, 1920
FPS = 30
SR = 44100
CX, CY = 540.0, 1010.0

N_RINGS = int(PRM.get("n_rings", 21))
R0 = 130.0
SPACING = (510.0 - R0) / (N_RINGS - 1)
LW = 7.0
RADII = R0 + SPACING * np.arange(N_RINGS)
BALL_R = 13.0
GRAV = 1500.0

# tunable: gap half-width, base rotation (rad/s), phase offset between rings,
# extra speed for outer rings, min speed after a bounce
P = dict(gap=np.deg2rad(PRM.get("gap_deg", 36)), omega=PRM.get("omega", 2.9),
         spiral=np.deg2rad(PRM.get("spiral_deg", 7)), twist=PRM.get("twist", 0.03), vmin=600.0,
         phi0=np.pi / 2)

OUTRO = 3.6                     # seconds after the last escape


def gap_center(k, t):
    return P["phi0"] + k * P["spiral"] + P["omega"] * (1 + P["twist"] * k) * t


def wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


HUE0 = float(PRM.get("hue_start", 0.95))
HUE_SPAN = float(PRM.get("hue_span", -0.8))
SAT = float(PRM.get("saturation", 0.82))
RING_COLORS = np.array([colorsys.hsv_to_rgb((HUE0 + HUE_SPAN * k / (N_RINGS - 1)) % 1.0, SAT, 1.0)
                        for k in range(N_RINGS)])
