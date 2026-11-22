"""Renderer: ball falling through glass barriers."""
import pickle
import numpy as np
import cv2
from common3 import *
from gfx import gsprite, disk, add_sprite, text_mask, add_mask, bloom, finish, segment_main
from timewarp import Warp

SIM = pickle.load(open("sim3.pkl", "rb"))
PATH, CAM = SIM["path"], SIM["cam"]
HITS, BREAKS = SIM["hits"], SIM["breaks"]
H_T = np.array([h["t"] for h in HITS])
B_T = np.array([b["t"] for b in BREAKS])
T_DONE, T_END = SIM["t_done"], SIM["t_end"]
WARP = Warp([(T_DONE - 0.12, T_DONE + 0.45, 0.28)], T_END)
N_FRAMES = int(float(WARP.v_of_t(T_END)) * FPS)
rng = np.random.default_rng(SEED + 9)

# background: soft vertical gradient + parallax dust
yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
BG = (np.array([0.02, 0.025, 0.06], np.float32) * (1 - yy) + np.array([0.035, 0.015, 0.05], np.float32) * yy)
BG = np.broadcast_to(BG, (H, W, 3)).copy()
DUST = rng.uniform([0, 0], [W, 4000], size=(160, 2))
DUST_A = rng.uniform(0.05, 0.22, 160)
SP_DUST = gsprite(1.3, 5)

# barrier sprite masks (rounded rect)
BW, BH_PAD = int(WALL_R - WALL_L), 14
roi_h = int(BAR_H + 2 * BH_PAD)
fill_u8 = np.zeros((roi_h, BW + 2 * BH_PAD), np.uint8)
edge_u8 = np.zeros_like(fill_u8)
r_c = 14
cv2.rectangle(fill_u8, (BH_PAD + r_c, BH_PAD), (BH_PAD + BW - r_c, BH_PAD + int(BAR_H)), 255, -1, cv2.LINE_AA)
cv2.rectangle(fill_u8, (BH_PAD, BH_PAD + r_c), (BH_PAD + BW, BH_PAD + int(BAR_H) - r_c), 255, -1, cv2.LINE_AA)
for cx_, cy_ in ((BH_PAD + r_c, BH_PAD + r_c), (BH_PAD + BW - r_c, BH_PAD + r_c),
                 (BH_PAD + r_c, BH_PAD + int(BAR_H) - r_c), (BH_PAD + BW - r_c, BH_PAD + int(BAR_H) - r_c)):
    cv2.circle(fill_u8, (cx_, cy_), r_c, 255, -1, cv2.LINE_AA)
FILL = fill_u8.astype(np.float32) / 255
er = cv2.erode(fill_u8, np.ones((7, 7), np.uint8))
EDGE = np.clip(FILL - er.astype(np.float32) / 255, 0, 1)
HL = np.zeros_like(FILL)
HL[BH_PAD + 6:BH_PAD + 9, BH_PAD + 20:BH_PAD + BW - 20] = 1.0
HL = cv2.GaussianBlur(HL, (0, 0), 1.2) * FILL

SP_GLOW = gsprite(30, 90)
SP_HOT = gsprite(7, 24)
TRAIL_N, TRAIL_T = 30, 0.16
SP_TRAIL = [gsprite(max(1.5, BALL_R * 0.7 * (1 - i / TRAIL_N) + 1)) for i in range(TRAIL_N)]
SP_SPARK = gsprite(1.1, 7) + 0.3 * gsprite(3.0, 7)
SP_FLASH = gsprite(46)

# impact sparks (screen-independent world coords)
SPARKS = []
for h in HITS:
    col = COLORS[h["k"]] * 0.5 + 0.5
    for q in range(16):
        a = -np.pi / 2 + rng.uniform(-1.3, 1.3)
        s = rng.uniform(150, 520)
        SPARKS.append((h["t"], h["x"], BAR_Y[h["k"]] - BAR_H / 2, np.cos(a) * s, np.sin(a) * s,
                       rng.uniform(0.25, 0.6), *col))
SPARKS = np.array(SPARKS)
GOLD = np.array([1.0, 0.82, 0.42], np.float32)


def ball_at(t):
    return np.interp(t, PATH[:, 0], PATH[:, 1]), np.interp(t, PATH[:, 0], PATH[:, 2])


def render(fi):
    t = float(WARP.t_of_v(fi / FPS))
    cam = float(np.interp(t, PATH[:, 0], CAM))
    img = BG.copy()
    for (dx, dy), a in zip(DUST, DUST_A):
        sy = (dy - cam * 0.35) % 4000 - 1000
        if 0 <= sy < H:
            add_sprite(img, SP_DUST, dx, sy, np.array([0.7, 0.75, 1.0], np.float32) * np.float32(a))
    nb = int(np.searchsorted(B_T, t, side="right"))
    nh = int(np.searchsorted(H_T, t, side="right"))
    layer = np.zeros((H, W, 3), np.uint8)

    # ---- barriers ----
    for k in range(NB):
        tb = B_T[k] if k < len(B_T) else 1e9
        if t > tb + 0.05:
            continue
        sy = BAR_Y[k] - cam
        if sy < -100 or sy > H + 100:
            continue
        hk = [h for h in HITS[:nh] if h["k"] == k]
        hp_now = HP[k] - len(hk)
        dy = 0.0
        flash = 0.0
        if hk:
            a = t - hk[-1]["t"]
            dy = 7 * np.exp(-a / 0.09) * np.cos(2 * np.pi * 9 * a)
            flash = np.exp(-a / 0.08)
        y0 = int(round(sy + dy - BAR_H / 2 - BH_PAD))
        x0 = int(WALL_L - BH_PAD)
        if y0 < 0 or y0 + roi_h > H:
            continue
        col = COLORS[k].astype(np.float32)
        roi = img[y0:y0 + roi_h, x0:x0 + FILL.shape[1]]
        roi += FILL[:, :, None] * (col * 0.24 + flash * 0.55)
        roi += EDGE[:, :, None] * col * 1.15
        roi += HL[:, :, None] * 0.35
        if t > tb:
            roi += FILL[:, :, None] * 1.2 * (1 - (t - tb) / 0.05)
        # cracks
        cm = np.zeros(FILL.shape, np.uint8)
        for (tc, lines) in SIM["cracks"][k]:
            if tc <= t:
                for ln in lines:
                    pts = (ln + np.array([BH_PAD, BH_PAD], np.float32)).round().astype(np.int32)
                    cv2.polylines(cm, [pts], False, 255, 2, cv2.LINE_AA)
        if cm.any():
            roi += (cm.astype(np.float32) / 255 * FILL)[:, :, None] * 0.85
        if hp_now > 0:
            sc = 1 + 0.35 * flash
            m, g = text_mask(str(hp_now), int(round(54 * sc)))
            add_mask(img, g, W / 2, sy + dy + 2, (-0.9, -0.9, -0.9))
            add_mask(img, m, W / 2, sy + dy, (1.0, 1.0, 1.0))

    # ---- golden finish platform ----
    fy = FLOOR_Y - cam
    if fy < H + 60:
        y0 = int(fy - 14)
        if 0 <= y0 < H - 30:
            img[y0:y0 + 28, int(WALL_L):int(WALL_R)] += GOLD * 0.55
            img[y0:y0 + 3, int(WALL_L):int(WALL_R)] += GOLD * 0.9
        if T_DONE <= t:
            a = t - T_DONE
            m, g = text_mask("ARRIVÉE", 40, spacing=8)
            add_mask(img, m, W / 2, fy + 60, GOLD * min(1, a / 0.4))

    # ---- shards ----
    for s in SIM["shards"]:
        a = t - s["t"]
        if a < 0 or a > s["life"]:
            continue
        c = s["c"] + s["v"] * a + np.array([0, 0.5 * GRAV * 0.55 * a * a])
        th = s["w"] * a
        R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]], np.float32)
        pts = (s["verts"] @ R.T + c - np.array([0, cam])).round().astype(np.int32)
        if pts[:, 1].max() < 0 or pts[:, 1].min() > H:
            continue
        f = (1 - a / s["life"]) ** 1.2
        colr = np.clip((COLORS[s["k"]] * 0.55 + 0.25) * f * 255, 0, 255)
        cv2.fillPoly(layer, [pts], tuple(int(v) for v in colr), cv2.LINE_AA)
        cv2.polylines(layer, [pts], True, tuple(int(min(255, v * 1.6)) for v in colr), 1, cv2.LINE_AA)

    # ---- sparks ----
    if len(SPARKS):
        age = t - SPARKS[:, 0]
        sel = (age >= 0) & (age < SPARKS[:, 5])
        for row, a in zip(SPARKS[sel], age[sel]):
            px = row[1] + row[3] * a
            py = row[2] + row[4] * a + 0.5 * 1800 * a * a - cam
            add_sprite(img, SP_SPARK, px, py, row[6:9] * (1 - a / row[5]) * 1.3)

    # ---- impact flashes ----
    for h in HITS[max(0, nh - 2):nh]:
        a = t - h["t"]
        if a < 0.18:
            add_sprite(img, SP_FLASH, h["x"], BAR_Y[h["k"]] - BAR_H / 2 - cam,
                       (COLORS[h["k"]] * 0.5 + 0.5) * (0.7 * (1 - a / 0.18) ** 2))

    # ---- ball ----
    kc = min(nb, NB - 1)
    bcol = (COLORS[kc] * 0.6 + 0.4).astype(np.float32) if t < T_DONE else GOLD
    for i in range(TRAIL_N - 1, 0, -1):
        tb_ = t - TRAIL_T * i / TRAIL_N
        if tb_ < 0:
            continue
        bx_, by_ = ball_at(tb_)
        add_sprite(img, SP_TRAIL[i], bx_, by_ - float(np.interp(tb_, PATH[:, 0], CAM)),
                   bcol * 0.3 * (1 - i / TRAIL_N) ** 1.5)
    bx, by = ball_at(t)
    by -= cam
    sx = sy_ = 1.0
    if nh:
        a = t - H_T[nh - 1]
        e = np.exp(-a / 0.045) * np.cos(2 * np.pi * 7 * a)
        sx, sy_ = 1 + 0.32 * e, 1 - 0.28 * e
    add_sprite(img, SP_GLOW, bx, by, bcol * 0.42)
    cv2.ellipse(layer, (int(round(bx)), int(round(by))),
                (max(1, int(BALL_R * sx)), max(1, int(BALL_R * sy_))), 0, 0, 360,
                tuple(int(v * 255) for v in (bcol * 0.75 + 0.25)), -1, cv2.LINE_AA)
    img += layer.astype(np.float32) / 255
    add_sprite(img, SP_HOT, bx, by, (0.8, 0.8, 0.8))

    # ---- slow-motion zoom ----
    za = float(WARP.slow_amount(t))
    if za > 0.01:
        s = 1 + 0.12 * za
        M = np.float32([[s, 0, (1 - s) * bx], [0, s, (1 - s) * by]])
        img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR)
    img = bloom(img, 0.9)

    # ---- HUD ----
    left = NB - nb
    last = B_T[nb - 1] if nb else -10
    sc = 1 + 0.25 * np.exp(-(t - last) / 0.08)
    m, g = text_mask(str(left), int(round(170 * sc)))
    add_mask(img, m, W / 2, 230, (1, 1, 1))
    add_mask(img, g, W / 2, 230, (0.25, 0.25, 0.25))
    if t < T_DONE:
        lm, _ = text_mask("BARRIÈRES", 42, bold=False, spacing=9)
        add_mask(img, lm, W / 2, 335, (0.75, 0.75, 0.75))
    else:
        s2 = 1 + 0.35 * np.exp(-(t - T_DONE) / 0.12)
        lm, lg = text_mask("BRAVO !", int(round(60 * s2)), spacing=6)
        add_mask(img, lm, W / 2, 340, GOLD)
        add_mask(img, lg, W / 2, 340, GOLD * 0.5)
    fade = float(np.clip((N_FRAMES / FPS - fi / FPS) / 0.4, 0, 1))
    return finish(img, fade)


if __name__ == "__main__":
    segment_main(render, N_FRAMES)
