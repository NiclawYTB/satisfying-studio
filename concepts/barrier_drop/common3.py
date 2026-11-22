import colorsys, json, os
import numpy as np

PRM = json.load(open(os.environ.get("SATISFY_PARAMS", "params.json")))
SEED = int(PRM.get("seed", 1))
KEY = int(PRM.get("key_shift", 0))
W, H, FPS = 1080, 1920, 30

NB = int(PRM.get("n_barriers", 15))
GAP = 345.0                    # vertical distance between barriers
Y0 = 760.0                     # world y of the first barrier (centre line)
BAR_H = 60.0
WALL_L, WALL_R = 70.0, W - 70.0
BALL_R = 22.0
GRAV = 2600.0
OUTRO = 3.0
CAM_FRAC = 0.62                # current barrier sits at 62 % of the screen height
BAR_Y = Y0 + GAP * np.arange(NB)
FLOOR_Y = Y0 + GAP * NB + 40.0

_r = np.random.default_rng(SEED)
HP = [int(min(5, 1 + int(k * 3.0 / NB) + (_r.random() < 0.35))) for k in range(NB)]
HUE0 = float(PRM.get("hue_start", 0.55))
HUE_SPAN = float(PRM.get("hue_span", 0.45))
SAT = float(PRM.get("saturation", 0.55))
COLORS = np.array([colorsys.hsv_to_rgb((HUE0 + HUE_SPAN * k / max(1, NB - 1)) % 1.0, SAT, 1.0)
                   for k in range(NB)])
