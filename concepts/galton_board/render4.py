"""Renderer: Galton board."""
import pickle
from math import comb
import numpy as np
import cv2
from common4 import *
from gfx import gsprite, disk, add_sprite, text_mask, add_mask, bloom, finish, segment_main

SIM = pickle.load(open("sim4.pkl", "rb"))
BALLS, NBALL = SIM["balls"], SIM["n"]
T_ALL, T_END = SIM["t_all"], SIM["t_end"]
N_FRAMES = int(T_END * FPS)
COLS = np.array([ball_color(i, NBALL) for i in range(NBALL)], np.float32)
T0 = np.array([b["t0"] for b in BALLS])
TL = np.array([b["t_land"] for b in BALLS])

SP_BALL = disk(BALL_R, 0.9) + 0.25 * gsprite(5.0, 12)[12 - int(BALL_R + 2):12 + int(BALL_R + 2) + 1,
                                                       12 - int(BALL_R + 2):12 + int(BALL_R + 2) + 1]
SP_PEG = disk(PEG_R, 0.8)
SP_DISK = disk(BALL_R, 0.9)
SP_PEGLIGHT = gsprite(9, 28)
SP_TR = gsprite(3.5, 11)
GOLD = np.array([1.0, 0.82, 0.42], np.float32)

# static scene
yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
STATIC = np.broadcast_to(np.array([0.018, 0.02, 0.045], np.float32) * (1 - yy) +
                         np.array([0.03, 0.018, 0.04], np.float32) * yy, (H, W, 3)).copy()
for r in range(ROWS):
    for j in range(r + 1):
        x, y = peg_xy(r, j)
        add_sprite(STATIC, SP_PEG, x, y, (0.42, 0.44, 0.55))
lines = np.zeros((H, W), np.uint8)
for b in range(NBINS + 1):
    x = int(round(bin_x(b) - DX / 2))
    cv2.line(lines, (x, int(BIN_TOP)), (x, int(BIN_BOT)), 255, 2, cv2.LINE_AA)
cv2.line(lines, (int(bin_x(0) - DX / 2), int(BIN_BOT + 2)), (int(bin_x(ROWS) + DX / 2), int(BIN_BOT + 2)), 255, 3,
         cv2.LINE_AA)
cv2.line(lines, (int(CX - 75), 330), (int(CX - 18), 405), 255, 3, cv2.LINE_AA)
cv2.line(lines, (int(CX + 75), 330), (int(CX + 18), 405), 255, 3, cv2.LINE_AA)
STATIC += (lines.astype(np.float32) / 255)[:, :, None] * np.array([0.32, 0.34, 0.45], np.float32)

# theoretical bell curve
xs, ys = [], []
for b in range(NBINS):
    n = NBALL * comb(ROWS, b) / 2 ** ROWS
    xs.append(bin_x(b))
    ys.append(BIN_BOT - BALL_R - (n / PER_LAYER) * LAYER_H - 16)
CX_F = np.linspace(xs[0], xs[-1], 300)
CY_F = np.interp(CX_F, xs, ys)
CY_F = np.convolve(np.pad(CY_F, 12, mode="edge"), np.ones(25) / 25, mode="valid")


def contact(r, j):
    x, y = peg_xy(r, j)
    return x, y - PEG_R - BALL_R


def ball_pos(b, t):
    if t < b["t_first"]:
        s = (t - b["t0"]) / (b["t_first"] - b["t0"])
        x1, y1 = contact(0, 0)
        return x1, 400 + (y1 - 400) * s * s
    if t < b["t_last"]:
        s = (t - b["t_first"]) / TAU
        r = int(s)
        f = s - r
        x0, y0 = contact(r, b["js"][r])
        x1, y1 = contact(r + 1, b["js"][r + 1])
        return x0 + (x1 - x0) * f, y0 + (y1 - y0) * f ** 1.7 - 9 * np.sin(np.pi * f)
    dt = t - b["t_last"]
    x0, y0 = contact(ROWS - 1, b["js"][-1])
    rx, ry = b["rest"]
    p = min(1.0, dt / (b["t_land"] - b["t_last"]))
    side = x0 + (b["d_last"] - 0.5) * DX
    x = x0 + (side - x0) * min(1, p * 3) if p < 0.33 else side + (rx - side) * ((p - 0.33) / 0.67) ** 0.7
    return x, min(ry, y0 + 0.5 * GRAV * dt * dt)


def render(fi):
    t = fi / FPS
    img = STATIC.copy()
    landed = np.flatnonzero(TL <= t)
    for i in landed:
        rx, ry = BALLS[i]["rest"]
        a = t - TL[i]
        boost = 1 + 0.8 * np.exp(-a / 0.08)
        add_sprite(img, SP_DISK, rx, ry - 3 * np.exp(-a / 0.05), COLS[i] * 0.8 * boost)
    fly = np.flatnonzero((T0 <= t) & (TL > t))
    for i in fly:
        b = BALLS[i]
        for k, dtt in enumerate((0.045, 0.03, 0.015)):
            if t - dtt > b["t0"]:
                px, py = ball_pos(b, t - dtt)
                add_sprite(img, SP_TR, px, py, COLS[i] * (0.10 + 0.06 * k))
        x, y = ball_pos(b, t)
        add_sprite(img, SP_BALL, x, y, COLS[i] * 1.15)
        if b["t_first"] <= t < b["t_last"] + TAU:
            r = min(ROWS - 1, int((t - b["t_first"]) / TAU))
            a = t - (b["t_first"] + r * TAU)
            px, py = peg_xy(r, b["js"][r])
            add_sprite(img, SP_PEGLIGHT, px, py, COLS[i] * 0.55 * np.exp(-a / 0.1))
            add_sprite(img, SP_PEG, px, py, COLS[i] * 0.9 * np.exp(-a / 0.12))
    # bell curve reveal
    if t > T_ALL + 0.25:
        p = min(1.0, (t - T_ALL - 0.25) / 1.4)
        n = max(2, int(len(CX_F) * p))
        lay = np.zeros((H, W), np.uint8)
        pts = np.stack([CX_F[:n], CY_F[:n]], 1).round().astype(np.int32)
        cv2.polylines(lay, [pts], False, 255, 4, cv2.LINE_AA)
        img += (lay.astype(np.float32) / 255)[:, :, None] * GOLD * 1.2
        add_sprite(img, gsprite(14, 44), CX_F[n - 1], CY_F[n - 1], GOLD * 0.9 * (1 - p * 0.6))
    img = bloom(img, 0.55)
    # HUD
    cnt = len(landed)
    last = TL[landed].max() if cnt else -10
    sc = 1 + 0.08 * np.exp(-(t - last) / 0.06)
    m, g = text_mask(str(cnt), int(round(150 * sc)), mono=True)
    add_mask(img, m, W / 2, 150, (1, 1, 1))
    add_mask(img, g, W / 2, 150, (0.2, 0.2, 0.2))
    if t < T_ALL + 0.2:
        lm, _ = text_mask("BILLES", 42, bold=False, spacing=10)
        add_mask(img, lm, W / 2, 250, (0.75, 0.75, 0.75))
    else:
        s2 = 1 + 0.3 * np.exp(-(t - T_ALL - 0.2) / 0.12)
        lm, lg = text_mask("LA COURBE PARFAITE", int(round(46 * s2)), spacing=5)
        add_mask(img, lm, W / 2, 255, GOLD)
        add_mask(img, lg, W / 2, 255, GOLD * 0.5)
    fade = float(np.clip((T_END - t) / 0.4, 0, 1))
    return finish(img, fade)


if __name__ == "__main__":
    segment_main(render, N_FRAMES)
