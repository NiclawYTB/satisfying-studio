"""Frame renderer. Usage:
  python3 render.py png <frame> [<frame> ...]
  python3 render.py seg <start> <end> <out.mp4>
"""
import sys, os, pickle, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter1d, gaussian_filter
from common import *

with open("sim.pkl", "rb") as f:
    SIM = pickle.load(f)
AN = np.load("out/analysis.npz")
BANDS, WAVES, KICKS = AN["bands"], AN["waves"], AN["kicks"]
HITS = SIM["hit_info"]
HIT_T = np.array([h["t"] for h in HITS])
PTS, KEY_T = SIM["pts"], SIM["key_t"]
TG, ZG = SIM["tgrid"], SIM["z"]
PARTS = SIM["parts"]
P48, GCTRL, GLIDE = SIM["P48"], SIM["glide_ctrl"], SIM["glide"]

# ---------- precomputed geometry ----------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
RHO = np.sqrt((xx + 0.5 - CX) ** 2 + (yy + 0.5 - CY) ** 2)
Q = 4                                   # LUT samples per pixel
LUTN = int(RHO.max() * Q) + 8
IDX = np.clip(np.round(RHO * Q).astype(np.int32), 0, LUTN - 1)
RG = np.arange(LUTN, dtype=np.float32) / Q

VY0, VY1 = int(CY - 600), int(CY + 600)
VR = RHO[VY0:VY1]
VTH = np.mod(np.arctan2(xx[VY0:VY1] + 0.5 - CX, -(yy[VY0:VY1] + 0.5 - CY)), 2 * np.pi)
del yy, xx

WHITE = np.array([1.0, 1.0, 1.0])
CYAN = BALL_COLOR


def zoom(t):
    return float(np.interp(t, TG, ZG))


def ball_world(t):
    if t <= GLIDE[0]:
        j = np.searchsorted(KEY_T, t, side="right") - 1
        j = int(np.clip(j, 0, len(KEY_T) - 2))
        a = (t - KEY_T[j]) / (KEY_T[j + 1] - KEY_T[j])
        return PTS[j] + (PTS[j + 1] - PTS[j]) * np.clip(a, 0, 1)
    a = min(1.0, (t - GLIDE[0]) / (GLIDE[1] - GLIDE[0]))
    a = 1 - (1 - a) ** 3
    return (1 - a) ** 2 * P48 + 2 * (1 - a) * a * GCTRL


def destroyed(t):
    n = np.searchsorted(HIT_T, t + 1e-9, side="right")
    return 0 if n == 0 else HITS[n - 1]["d1"], n


def kick_pulse(t):
    p = 0.0
    for tk in KICKS[(KICKS <= t) & (KICKS > t - 0.6)]:
        p += np.exp(-(t - tk) / 0.14)
    return min(p, 1.2)


# ---------- radial profile helpers ----------
def add_ring(prof, rc, hw, col, inten):
    i0 = max(0, int((rc - hw - 1.5) * Q))
    i1 = min(LUTN, int((rc + hw + 1.5) * Q) + 1)
    if i1 <= i0:
        return
    cov = np.clip(hw + 0.5 - np.abs(RG[i0:i1] - rc), 0, 1)
    prof[i0:i1] += cov[:, None] * (np.asarray(col) * inten)[None, :]


def add_gauss(prof, rc, sig, col, inten):
    i0 = max(0, int((rc - 4 * sig) * Q))
    i1 = min(LUTN, int((rc + 4 * sig) * Q) + 1)
    if i1 <= i0:
        return
    g = np.exp(-0.5 * ((RG[i0:i1] - rc) / sig) ** 2)
    prof[i0:i1] += g[:, None] * (np.asarray(col) * inten)[None, :]


# ---------- sprites ----------
def gsprite(sig, rad=None):
    rad = rad or int(np.ceil(3.2 * sig))
    a = np.arange(-rad, rad + 1, dtype=np.float32)
    g = np.exp(-0.5 * (a[:, None] ** 2 + a[None, :] ** 2) / sig ** 2)
    return g


SP_PART = gsprite(1.5, 11) + 0.3 * gsprite(4.0, 11)
SP_SPARK = gsprite(0.9, 7) + 0.35 * gsprite(2.6, 7)
_a = np.arange(-90, 91, dtype=np.float32)
_r = np.sqrt(_a[:, None] ** 2 + _a[None, :] ** 2)
SP_BALL_CORE = np.clip(BALL_R + 0.5 - _r, 0, 1)
SP_BALL_HOT = np.exp(-0.5 * (_r / 7.0) ** 2)
SP_BALL_GLOW = np.exp(-0.5 * (_r / 30.0) ** 2)
TRAIL_N = 40
TRAIL_T = 0.17
SP_TRAIL = [gsprite(max(1.5, BALL_R * 0.62 * (1 - i / TRAIL_N) + 1.2)) for i in range(TRAIL_N)]
SP_FLASH = gsprite(34)
SP_BIGFLASH = gsprite(130)


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


# ---------- text ----------
FONT_PATH = os.path.join(FONT_DIR, "Poppins-Bold.ttf")
_fonts, _txt = {}, {}


def text_mask(s, size):
    key = (s, size)
    if key not in _txt:
        if size not in _fonts:
            _fonts[size] = ImageFont.truetype(FONT_PATH, size)
        im = Image.new("L", (int(size * 3.2), int(size * 1.6)))
        ImageDraw.Draw(im).text((im.width / 2, im.height / 2), s, font=_fonts[size], fill=255,
                                anchor="mm")
        m = np.asarray(im, dtype=np.float32) / 255
        glow = gaussian_filter(m, 10)
        _txt[key] = (m, glow)
    return _txt[key]


def add_mask(img, m, cx, cy, col):
    h, w = m.shape
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    img[y0:y0 + h, x0:x0 + w] += m[:, :, None] * np.asarray(col, dtype=np.float32)[None, None, :]


def ease_out_back(x):
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


NBARS = 96
BAR_COL = palette(np.linspace(0.05, 0.6, 48))


def draw_visualiser(img, t, fi):
    a = np.clip((t - T_DROP) / 0.5, 0, 1)
    s = 0.55 + 0.45 * ease_out_back(a)
    alpha = np.clip((t - T_DROP) / 0.2, 0, 1)
    if alpha <= 0:
        return
    lev = BANDS[min(fi, len(BANDS) - 1)]
    p = kick_pulse(t)
    r_in = 255 * s * (1 + 0.035 * p)
    av = VTH / (2 * np.pi) * NBARS
    b = np.floor(av).astype(np.int32) % NBARS
    frac = av - np.floor(av) - 0.5
    arcd = np.abs(frac) * (2 * np.pi / NBARS) * VR
    m = 47 - np.minimum(b, NBARS - 1 - b)
    blen = (12 + 285 * lev[m]) * s
    hw = 4.4 * s
    cov = (np.clip(hw + 0.5 - arcd, 0, 1) * np.clip(VR - r_in + 0.5, 0, 1)
           * np.clip(r_in + blen - VR + 0.5, 0, 1))
    vis = cov[:, :, None] * BAR_COL[m] * 1.15
    # inner rim
    rim = np.clip(1.6 + 0.5 - np.abs(VR - (r_in - 16)), 0, 1)
    vis += rim[:, :, None] * (palette(0.0) * 0.8 + 0.2) * 0.9
    # waveform ring
    wv = WAVES[min(fi, len(WAVES) - 1)]
    wv = np.convolve(wv, np.ones(9) / 9, mode="same")
    g = 1.0 / max(0.12, np.abs(wv).max())
    wv = np.clip(wv * g, -1, 1)
    th_half = np.where(VTH <= np.pi, VTH, 2 * np.pi - VTH) / np.pi
    wi = np.clip((th_half * (len(wv) - 1)).astype(np.int32), 0, len(wv) - 1)
    rw = (r_in - 52) + 26 * s * wv[wi] * (0.4 + 0.6 * min(1, p + 0.3))
    line = np.clip(1.6 + 0.5 - np.abs(VR - rw), 0, 1)
    vis += line[:, :, None] * 0.95
    # glow
    hh, ww = vis.shape[:2]
    small = vis.reshape(hh // 4, 4, ww // 4, 4, 3).mean(axis=(1, 3))
    small = gaussian_filter(small, (5, 5, 0))
    glow = np.asarray(Image.fromarray(np.uint8(np.clip(small * 4 * 255 / 6, 0, 255)))
                      .resize((ww, hh), Image.BILINEAR), dtype=np.float32) / 255 * 6 / 4
    img[VY0:VY1] += (vis + glow * 1.1) * alpha


def render(fi):
    t = fi / FPS
    z = zoom(t)
    D, nh = destroyed(t)
    p = kick_pulse(t)
    img = None

    # ---- rings via radial profile ----
    prof = np.zeros((LUTN, 3), dtype=np.float32)
    gain = np.zeros(LUTN, dtype=np.float32)
    bright = 0.72 + 0.35 * p
    hw = max(LW * z, 1.25) / 2
    dim = min(1.0, (LW * z) / 1.25) ** 0.5
    for i in range(D, N_RINGS):
        col = RING_COLORS[i]
        inten = bright * dim
        if i == D:
            col = col * 0.6 + 0.4
            inten *= 1.6
        add_ring(prof, RADII[i] * z, hw, col, inten)
    flash = np.zeros_like(prof)
    for h in HITS[max(0, nh - 6):nh]:
        a = t - h["t"]
        final = h["d1"] >= N_RINGS
        fl_t = 0.12 if final else 0.16
        if a < fl_t:
            f = (1 - a / fl_t) ** 1.5 * (0.9 if final else 2.0)
            for i in range(h["d0"], h["d1"]):
                add_ring(flash, RADII[i] * z * (1 + 0.025 * a / fl_t), hw * 1.4,
                         RING_COLORS[i] * 0.4 + 0.6, f)
        if not final and a < 0.45:
            rr = RADII[min(h["d1"], N_RINGS - 1)] * z + 300 * (a / 0.45) ** 0.7
            add_gauss(gain[:, None], rr, 18, (1.0,), 1.3 * (1 - a / 0.45) ** 1.5)
        if final and a < 0.9:
            rr = RADII[h["d0"]] * z + 900 * (a / 0.9) ** 0.6
            add_gauss(flash, rr, 6 + 10 * a, palette(0.0) * 0.4 + 0.6, 0.6 * (1 - a / 0.9) ** 1.5)
    prof *= (1 + gain)[:, None]
    prof += flash
    if prof.any():
        glow = gaussian_filter1d(prof, 3.5 * Q, axis=0) * 0.4 + \
            gaussian_filter1d(prof, 22 * Q, axis=0) * 0.22
        img = (prof + glow)[IDX]
    else:
        img = np.zeros((H, W, 3), dtype=np.float32)

    # ---- particles ----
    if len(PARTS):
        age = t - PARTS[:, 0]
        sel = (age >= 0) & (age < PARTS[:, 5])
        P = PARTS[sel]
        a = age[sel]
        c = P[:, 6]
        k = (1 - np.exp(-c * a)) / c
        px = P[:, 1] + P[:, 3] * k
        py = P[:, 2] + P[:, 4] * k
        fade = (1 - a / P[:, 5]) ** 1.3
        for q in range(len(P)):
            sp = SP_SPARK if P[q, 10] > 0.5 else SP_PART
            add_sprite(img, sp, px[q], py[q], P[q, 7:10] * fade[q] * 1.5)

    # ---- impact flashes ----
    for h in HITS[max(0, nh - 3):nh]:
        a = t - h["t"]
        ip = np.array([CX, CY]) + h["pos"] * h["z"] + h["u"] * BALL_R
        if h["d1"] >= N_RINGS:
            if a < 0.5:
                add_sprite(img, SP_BIGFLASH, ip[0], ip[1], WHITE * 0.8 * (1 - a / 0.5) ** 2)
            if a < 0.22:
                img += np.float32(0.22 * (1 - a / 0.22) ** 2)
        elif a < 0.2:
            add_sprite(img, SP_FLASH, ip[0], ip[1], (BALL_COLOR * 0.6 + 0.4) * (0.9 * (1 - a / 0.2) ** 2))

    # ---- visualiser ----
    if t >= T_DROP:
        draw_visualiser(img, t, fi)

    # ---- counter ----
    val = N_RINGS - D
    last_hit = HIT_T[nh - 1] if nh else -10
    sc = 1 + 0.22 * np.exp(-(t - last_hit) / 0.07) if nh else 1.0
    t_alpha = 1.0 if t < T_DROP + 0.35 else max(0.0, 1 - (t - T_DROP - 0.35) / 0.4)
    if t_alpha > 0:
        size = int(round(150 * sc))
        m, gl = text_mask(str(val), size)
        add_mask(img, m, CX, CY, WHITE * t_alpha)
        add_mask(img, gl, CX, CY, (palette(0.1) * 0.5 + 0.5) * 0.35 * t_alpha)

    # ---- ball + trail ----
    for i in range(TRAIL_N - 1, -1, -1):
        tau = TRAIL_T * i / TRAIL_N
        tb = t - tau
        if tb < 0:
            continue
        bw = ball_world(tb)
        zb = zoom(tb)
        bx, by = CX + bw[0] * zb, CY + bw[1] * zb
        f = (1 - i / TRAIL_N) ** 1.6
        add_sprite(img, SP_TRAIL[i], bx, by, CYAN * 0.32 * f)
    bw = ball_world(t)
    bx, by = CX + bw[0] * z, CY + bw[1] * z
    pulse_c = 1.0
    if t > GLIDE[1]:
        pulse_c = 1 + 0.9 * p
    add_sprite(img, SP_BALL_GLOW, bx, by, CYAN * 0.5 * pulse_c)
    add_sprite(img, SP_BALL_CORE, bx, by, CYAN * 0.9)
    add_sprite(img, SP_BALL_HOT, bx, by, WHITE * 0.8)

    # ---- tone map ----
    ex = np.maximum(img - 1.0, 0).max(axis=2, keepdims=True)
    img += ex * 0.5
    fade_end = np.clip((T_END - t) / 0.35, 0, 1)
    if fade_end < 1:
        img *= fade_end
    np.clip(img, 0, 1, out=img)
    return (img * 255 + 0.5).astype(np.uint8)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "png":
        for a in sys.argv[2:]:
            fi = int(a)
            Image.fromarray(render(fi)).save(f"frames/f{fi:04d}.png")
            print("saved", fi)
    elif mode == "seg":
        s, e, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        tmp = out[:-4] + ".part.mp4"
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
               "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
               "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-pix_fmt", "yuv420p",
               "-r", str(FPS), tmp]
        pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for fi in range(s, e):
            pr.stdin.write(render(fi).tobytes())
            if (fi - s) % 60 == 0:
                print(out, fi, flush=True)
        pr.stdin.close()
        if pr.wait() == 0:
            os.replace(tmp, out)
            print("done", out)
        else:
            sys.exit(1)
