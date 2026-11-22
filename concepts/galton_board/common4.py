import colorsys, json, os
import numpy as np

PRM = json.load(open(os.environ.get("SATISFY_PARAMS", "params.json")))
SEED = int(PRM.get("seed", 1))
KEY = int(PRM.get("key_shift", 0))
W, H, FPS = 1080, 1920, 30
CX = 540.0

ROWS = 14
DX, DY = 62.0, 56.0
PY0 = 450.0                      # y of the top peg
PEG_R, BALL_R = 5.0, 7.0
NBINS = ROWS + 1
BIN_TOP, BIN_BOT = PY0 + (ROWS - 1) * DY + 50, 1795.0
PER_LAYER = 4
LAYER_H = 13.0
TAU = 0.072                      # seconds per peg row
GRAV = 3000.0
T_RELEASE = float(PRM.get("release_time", 17.0))
RATE0, RATE1 = float(PRM.get("rate0", 12)), float(PRM.get("rate1", 55))
HUE0 = float(PRM.get("hue_start", 0.0))
HUE_SPAN = float(PRM.get("hue_span", 0.9))
SAT = float(PRM.get("saturation", 0.6))
OUTRO = 4.2


def peg_xy(r, j):
    return CX + (j - r / 2.0) * DX, PY0 + r * DY


def bin_x(b):
    return CX + (b - ROWS / 2.0) * DX


def ball_color(i, n):
    return np.array(colorsys.hsv_to_rgb((HUE0 + HUE_SPAN * i / max(1, n - 1)) % 1.0, SAT, 1.0))
