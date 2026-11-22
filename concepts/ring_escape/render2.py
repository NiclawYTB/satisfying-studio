"""Renderer for the ring-escape video.
  python3 render2.py png <frame> ...
  python3 render2.py seg <start> <end> <out.mp4>
"""
import sys, os, pickle, subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from common2 import *
from timewarp import Warp

SIM = pickle.load(open("sim2.pkl", "rb"))
T_ESC = SIM["t_esc"]
T_END = T_ESC + OUTRO
WARP = Warp(SIM.get("warp_windows", []), T_END)
N_FRAMES = int(float(WARP.v_of_t(T_END)) * FPS)
PATH = SIM["path"]
BOUNCES = SIM["bounces"]
B_T = np.array([b[0] for b in BOUNCES])
ESC = SIM["escapes"]
E_T = np.array([e[0] for e in ESC])
FLOOR = SIM["floor"]
F_T = np.array([f[0] for f in FLOOR]) if FLOOR else np.zeros(0)
GAP = P["gap"]
G_SH = 1300.0

# ---------- band pixels of the rings ----------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
dx, dy = xx + 0.5 - CX, yy + 0.5 - CY
RHO = np.sqrt(dx * dx + dy * dy)
TH = np.arctan2(dy, dx)
J = np.clip(np.round((RHO - R0) / SPACING).astype(np.int32), 0, N_RINGS - 1)
DIST = RHO - RADII[J]
BC_all = np.clip(LW / 2 + 0.5 - np.abs(DIST), 0, 1)
mask = BC_all > 0
BI = np.flatnonzero(mask)
BJ = J.ravel()[BI]
BC = BC_all.ravel()[BI].astype(np.float32)
BT = TH.ravel()[BI].astype(np.float32)
BR = RHO.ravel()[BI].astype(np.float32)
del yy, xx, dx, dy, RHO, TH, J, DIST, BC_all, mask

WHITE = np.array([1.0, 1.0, 1.0], dtype=np.float32)

# ---------- sprites ----------
def gsprite(sig, rad=None):
    rad = rad or int(np.ceil(3.2 * sig))
    a = np.arange(-rad, rad + 1, dtype=np.float32)
    return np.exp(-0.5 * (a[:, None] ** 2 + a[None, :] ** 2) / sig ** 2)


SP_SHARD = gsprite(1.5, 10) + 0.28 * gsprite(4.0, 10)
SP_SPARK = gsprite(1.0, 7) + 0.3 * gsprite(2.6, 7)
_a = np.arange(-80, 81, dtype=np.float32)
_r = np.sqrt(_a[:, None] ** 2 + _a[None, :] ** 2)
SP_CORE = np.clip(BALL_R + 0.5 - _r, 0, 1)
SP_HOT = np.exp(-0.5 * (_r / 6.0) ** 2)
SP_GLOW = np.exp(-0.5 * (_r / 26.0) ** 2)
TRAIL_N, TRAIL_T = 44, 0.22
SP_TRAIL = [gsprite(max(1.4, BALL_R * 0.75 * (1 - i / TRAIL_N) + 1.0)) for i in range(TRAIL_N)]
SP_FLASH = gsprite(40)
SP_BIG = gsprite(150)


def add_sprite(img, sp, x, y, col):
    h, w = sp.shape
    x0 = int(round(x)) - w // 2
    y0 = int(round(y)) - h // 2
    sx0, sy0 = max(0, -x0), max(0, -y0)
    ex0, ey0 = max(0, x0), max(0, y0)
    ex1, ey1 = min(W, x0 + w), min(H, y0 + h)
    if ex1 <= ex0 or ey1 <= ey0:
        return
    sub = sp[sy0:sy0 + (ey1 - ey0), sx0:sx0 + (ex1 - ex0)]
    img[ey0:ey1, ex0:ex1] += sub[:, :, None] * np.asarray(col, dtype=np.float32)[None, None, :]


# ---------- particles ----------
rng = np.random.default_rng(5)
parts = []   # t0, x0, y0, vx, vy, life, r, g, b, kind
for (te, k, pe, ve) in ESC:
    final = k == N_RINGS - 1
    rk = RADII[k]
    gc = gap_center(k, te)
    n = int(2 * np.pi * rk / (5 if final else 7))
    th = gc + GAP + rng.uniform(0, 2 * np.pi - 2 * GAP, n)
    cs, sn = np.cos(th), np.sin(th)
    rr = rk + rng.uniform(-2.5, 2.5, n)
    x0, y0 = CX + rr * cs, CY + rr * sn
    vrad = rng.uniform(40, 520 if final else 300, n)
    om = P["omega"] * (1 + P["twist"] * k)
    vtan = om * rk * rng.uniform(0.5, 1.0, n)
    vx = vrad * cs - vtan * sn
    vy = vrad * sn + vtan * cs
    pang = np.arctan2(pe[1], pe[0])
    w = np.exp(-(wrap(th - pang) / 0.6) ** 2)
    sp = np.hypot(*ve)
    vx += ve[0] / sp * rng.uniform(150, 600, n) * w
    vy += ve[1] / sp * rng.uniform(150, 600, n) * w
    life = rng.uniform(1.0, 2.4 if final else 1.8, n)
    col = RING_COLORS[k] * 0.8 + 0.2
    for q in range(n):
        parts.append((te, x0[q], y0[q], vx[q], vy[q], life[q], *col, 0))
for (tb, k, pb, nb, spd) in BOUNCES:
    cxp, cyp = CX + pb[0] + nb[0] * BALL_R, CY + pb[1] + nb[1] * BALL_R
    col = RING_COLORS[k] * 0.5 + 0.5
    for q in range(12):
        a = np.arctan2(-nb[1], -nb[0]) + rng.uniform(-1.2, 1.2)
        s = rng.uniform(120, 420) * min(1.5, spd / 900)
        parts.append((tb, cxp, cyp, np.cos(a) * s, np.sin(a) * s, rng.uniform(0.2, 0.45), *col, 1))
PARTS = np.array(parts, dtype=np.float64)

# ---------- text ----------
F_BOLD = os.path.join(FONT_DIR, "Poppins-Bold.ttf")
F_MED = os.path.join(FONT_DIR, "Poppins-Medium.ttf")
_fonts, _cache = {}, {}


def font(path, size):
    if (path, size) not in _fonts:
        _fonts[(path, size)] = ImageFont.truetype(path, size)
    return _fonts[(path, size)]


def text_mask(s, path, size, spacing=0, mono=False):
    key = (s, path, size, spacing, mono)
    if key in _cache:
        return _cache[key]
    f = font(path, size)
    adv0 = f.getlength("0")
    chars = list(s)
    widths = [(adv0 if (mono and ch.isdigit()) else f.getlength(ch)) + spacing for ch in chars]
    tw = int(sum(widths) - spacing) + 8
    im = Image.new("L", (tw + 40, int(size * 1.5)))
    d = ImageDraw.Draw(im)
    x = 20.0
    for ch, w in zip(chars, widths):
        cw = f.getlength(ch)
        off = (w - spacing - cw) / 2 if (mono and ch.isdigit()) else 0
        d.text((x + off, im.height / 2), ch, font=f, fill=255, anchor="lm")
        x += w
    m = np.asarray(im, dtype=np.float32) / 255
    g = cv2.GaussianBlur(m, (0, 0), size / 12)
    _cache[key] = (m, g)
    return m, g


def add_mask(img, m, cx, cy, col):
    h, w = m.shape
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    img[y0:y0 + h, x0:x0 + w] += m[:, :, None] * np.asarray(col, dtype=np.float32)[None, None, :]


def ball_pos(t):
    return (CX + np.interp(t, PATH[:, 0], PATH[:, 1]), CY + np.interp(t, PATH[:, 0], PATH[:, 2]))


def escaped(t):
    return int(np.searchsorted(E_T, t, side="right"))


def fmt_time(t):
    t = min(t, T_ESC)
    m = int(t // 60)
    s = t - 60 * m
    return f"{m:02d}:{int(s):02d}.{int((s % 1) * 100):02d}"


def render(fi):
    t = float(WARP.t_of_v(fi / FPS))
    k_out = escaped(t)
    flat = np.zeros((H * W, 3), dtype=np.float32)

    # ---- rings ----
    bright = np.zeros(N_RINGS, dtype=np.float32)
    whiten = np.zeros(N_RINGS, dtype=np.float32)
    bright[k_out:] = 1.0
    if k_out < N_RINGS:
        bright[k_out] = 1.25
    nb = int(np.searchsorted(B_T, t, side="right"))
    for b in BOUNCES[max(0, nb - 4):nb]:
        a = t - b[0]
        f = np.exp(-a / 0.11)
        bright[b[1]] += 1.3 * f
        whiten[b[1]] = max(whiten[b[1]], 0.6 * f)
    for (te, k, _, _) in ESC:
        a = t - te
        if 0 <= a < 0.09:
            bright[k] = 2.4 * (1 - a / 0.09)
            whiten[k] = 0.8
    gapc = np.array([gap_center(k, t) for k in range(N_RINGS)], dtype=np.float32)
    live = bright[BJ] > 0
    if live.any():
        bj = BJ[live]
        d = np.abs(wrap(BT[live] - gapc[bj]))
        cov = np.clip((d - GAP) * BR[live] + 0.5, 0, 1) * BC[live] * bright[bj]
        col = RING_COLORS[bj].astype(np.float32) * (1 - whiten[bj, None]) + whiten[bj, None]
        flat[BI[live]] = cov[:, None] * col
    img = flat.reshape(H, W, 3)
    small = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    g1 = cv2.GaussianBlur(small, (0, 0), 3.0)
    g2 = cv2.GaussianBlur(cv2.resize(small, (W // 16, H // 16), interpolation=cv2.INTER_AREA), (0, 0), 2.5)
    img += cv2.resize(g1, (W, H), interpolation=cv2.INTER_LINEAR) * 1.1
    img += cv2.resize(g2, (W, H), interpolation=cv2.INTER_LINEAR) * 0.9

    # ---- particles ----
    age = t - PARTS[:, 0]
    sel = (age >= 0) & (age < PARTS[:, 5])
    Pp, a = PARTS[sel], age[sel]
    px = Pp[:, 1] + Pp[:, 3] * a
    py = Pp[:, 2] + Pp[:, 4] * a + 0.5 * G_SH * a * a
    fade = (1 - a / Pp[:, 5]) ** 1.2
    for q in range(len(Pp)):
        if -20 < px[q] < W + 20 and -20 < py[q] < H + 20:
            add_sprite(img, SP_SPARK if Pp[q, 9] > 0.5 else SP_SHARD, px[q], py[q],
                       Pp[q, 6:9] * fade[q] * 1.4)

    # ---- escape flashes ----
    for (te, k, pe, _) in ESC[max(0, k_out - 3):k_out]:
        a = t - te
        if k == N_RINGS - 1:
            if a < 0.6:
                add_sprite(img, SP_BIG, CX + pe[0], CY + pe[1], WHITE * 0.9 * (1 - a / 0.6) ** 2)
            if a < 0.25:
                img += np.float32(0.2 * (1 - a / 0.25) ** 2)
        elif a < 0.22:
            add_sprite(img, SP_FLASH, CX + pe[0], CY + pe[1],
                       (RING_COLORS[k] * 0.5 + 0.5) * 0.9 * (1 - a / 0.22) ** 2)

    # ---- ball + trail ----
    kc = min(k_out, N_RINGS - 1)
    bcol = (RING_COLORS[kc] * 0.75 + 0.25) if t < T_ESC else np.array([1.0, 0.9, 0.55])
    for i in range(TRAIL_N - 1, 0, -1):
        tb = t - TRAIL_T * i / TRAIL_N
        if tb < 0:
            continue
        bx, by = ball_pos(tb)
        f = (1 - i / TRAIL_N) ** 1.5
        add_sprite(img, SP_TRAIL[i], bx, by, bcol * 0.34 * f)
    bx, by = ball_pos(t)
    add_sprite(img, SP_GLOW, bx, by, bcol * 0.45)
    add_sprite(img, SP_CORE, bx, by, bcol * 0.8 + 0.2)
    add_sprite(img, SP_HOT, bx, by, WHITE * 0.7)

    # ---- slow-motion zoom towards the ball ----
    za = float(WARP.slow_amount(t))
    if za > 0.01:
        s = 1 + 0.16 * za
        zx, zy = CX + (bx - CX) * 0.7, CY + (by - CY) * 0.7
        M = np.float32([[s, 0, (1 - s) * zx], [0, s, (1 - s) * zy]])
        img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR)

    # ---- counter (top) ----
    left = N_RINGS - k_out
    last = E_T[k_out - 1] if k_out else -10
    sc = 1 + 0.25 * np.exp(-(t - last) / 0.08)
    m, g = text_mask(str(left), F_BOLD, int(round(190 * sc)))
    add_mask(img, m, CX, 300, WHITE)
    add_mask(img, g, CX, 300, WHITE * 0.25)
    if t < T_ESC:
        lm, lg = text_mask("ANNEAUX", F_MED, 44, spacing=10)
        add_mask(img, lm, CX, 412, WHITE * 0.72)
    else:
        a = t - T_ESC
        s2 = 1 + 0.35 * np.exp(-a / 0.12)
        lm, lg = text_mask("LIBRE !", F_BOLD, int(round(64 * s2)), spacing=6)
        gold = np.array([1.0, 0.85, 0.35], dtype=np.float32)
        add_mask(img, lm, CX, 418, gold)
        add_mask(img, lg, CX, 418, gold * 0.6)

    # ---- timer (bottom) ----
    tm, tg = text_mask(fmt_time(t), F_BOLD, 86, mono=True)
    tcol = WHITE * 0.9
    if t >= T_ESC:
        a = t - T_ESC
        blink = 0.75 + 0.25 * np.cos(a * 2 * np.pi * 1.6)
        tcol = np.array([1.0, 0.85, 0.35], dtype=np.float32) * blink
        add_mask(img, tg, CX, 1700, tcol * 0.5)
    add_mask(img, tm, CX, 1700, tcol)

    # ---- tone map ----
    ex = np.maximum(img - 1.0, 0).max(axis=2, keepdims=True)
    img += ex * 0.5
    fe = np.clip((N_FRAMES / FPS - fi / FPS) / 0.4, 0, 1)
    if fe < 1:
        img *= fe
    np.clip(img, 0, 1, out=img)
    return (img * 255 + 0.5).astype(np.uint8)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "png":
        for a in sys.argv[2:]:
            fi = int(a)
            Image.fromarray(render(fi)).save(f"frames/f{fi:04d}.png")
            print("saved", fi)
    elif mode == "n":
        print(N_FRAMES)
    elif mode == "seg":
        s, e, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        tmp = out[:-4] + ".part.mp4"
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
               "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
               "-c:v", "libx264", "-crf", "17", "-preset", "veryfast", "-pix_fmt", "yuv420p",
               "-r", str(FPS), tmp]
        pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for fi in range(s, e):
            pr.stdin.write(render(fi).tobytes())
        pr.stdin.close()
        if pr.wait() == 0:
            os.replace(tmp, out)
            print("done", out)
        else:
            sys.exit(1)
