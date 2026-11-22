"""Shared drawing helpers: additive sprites, cached text masks, encoding segments."""
import os, subprocess, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
FONT_DIR = os.environ.get("SATISFY_FONTS", os.path.join(os.path.dirname(__file__), "..", "fonts"))
F_BOLD = os.path.join(FONT_DIR, "Poppins-Bold.ttf")
F_MED = os.path.join(FONT_DIR, "Poppins-Medium.ttf")


def gsprite(sig, rad=None):
    rad = rad or int(np.ceil(3.2 * sig))
    a = np.arange(-rad, rad + 1, dtype=np.float32)
    return np.exp(-0.5 * (a[:, None] ** 2 + a[None, :] ** 2) / sig ** 2)


def disk(r, soft=0.8):
    rad = int(np.ceil(r + 2))
    a = np.arange(-rad, rad + 1, dtype=np.float32)
    d = np.sqrt(a[:, None] ** 2 + a[None, :] ** 2)
    return np.clip((r + soft - d) / (2 * soft), 0, 1)


def add_sprite(img, sp, x, y, col):
    h, w = sp.shape
    x0 = int(round(x)) - w // 2
    y0 = int(round(y)) - h // 2
    sx0, sy0 = max(0, -x0), max(0, -y0)
    ex0, ey0 = max(0, x0), max(0, y0)
    ex1, ey1 = min(img.shape[1], x0 + w), min(img.shape[0], y0 + h)
    if ex1 <= ex0 or ey1 <= ey0:
        return
    sub = sp[sy0:sy0 + (ey1 - ey0), sx0:sx0 + (ex1 - ex0)]
    img[ey0:ey1, ex0:ex1] += sub[:, :, None] * np.asarray(col, dtype=np.float32)[None, None, :]


_fonts, _cache = {}, {}


def text_mask(s, size, bold=True, spacing=0, mono=False):
    path = F_BOLD if bold else F_MED
    key = (s, path, size, spacing, mono)
    if key in _cache:
        return _cache[key]
    if (path, size) not in _fonts:
        _fonts[(path, size)] = ImageFont.truetype(path, size)
    f = _fonts[(path, size)]
    adv0 = f.getlength("0")
    widths = [(adv0 if (mono and ch.isdigit()) else f.getlength(ch)) + spacing for ch in s]
    tw = int(sum(widths) - spacing) + 8
    im = Image.new("L", (tw + 40, int(size * 1.5)))
    d = ImageDraw.Draw(im)
    x = 20.0
    for ch, w in zip(s, widths):
        off = (w - spacing - f.getlength(ch)) / 2 if (mono and ch.isdigit()) else 0
        d.text((x + off, im.height / 2), ch, font=f, fill=255, anchor="lm")
        x += w
    m = np.asarray(im, dtype=np.float32) / 255
    g = cv2.GaussianBlur(m, (0, 0), max(2, size / 12))
    _cache[key] = (m, g)
    return m, g


def add_mask(img, m, cx, cy, col):
    h, w = m.shape
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    ys0, xs0 = max(0, -y0), max(0, -x0)
    y1, x1 = min(img.shape[0], y0 + h), min(img.shape[1], x0 + w)
    if y1 <= max(0, y0) or x1 <= max(0, x0):
        return
    img[max(0, y0):y1, max(0, x0):x1] += m[ys0:ys0 + y1 - max(0, y0), xs0:xs0 + x1 - max(0, x0), None] * \
        np.asarray(col, dtype=np.float32)[None, None, :]


def bloom(img, strength=1.0):
    small = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    g1 = cv2.GaussianBlur(small, (0, 0), 3.0)
    g2 = cv2.GaussianBlur(cv2.resize(small, (W // 16, H // 16), interpolation=cv2.INTER_AREA), (0, 0), 2.5)
    img += cv2.resize(g1, (W, H), interpolation=cv2.INTER_LINEAR) * 0.9 * strength
    img += cv2.resize(g2, (W, H), interpolation=cv2.INTER_LINEAR) * 0.7 * strength
    return img


def finish(img, fade=1.0):
    ex = np.maximum(img - 1.0, 0).max(axis=2, keepdims=True)
    img += ex * 0.5
    if fade < 1:
        img *= fade
    np.clip(img, 0, 1, out=img)
    return (img * 255 + 0.5).astype(np.uint8)


def segment_main(render, n_frames):
    """CLI shared by renderers: `n` | `png f...` | `seg start end out.mp4`."""
    mode = sys.argv[1]
    if mode == "n":
        print(n_frames)
    elif mode == "png":
        os.makedirs("frames", exist_ok=True)
        for a in sys.argv[2:]:
            Image.fromarray(render(int(a))).save(f"frames/f{int(a):04d}.png")
            print("saved", a)
    elif mode == "seg":
        s, e, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        tmp = out[:-4] + ".part.mp4"
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18", "-preset",
               "veryfast", "-pix_fmt", "yuv420p", "-r", str(FPS), tmp]
        pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for fi in range(s, e):
            pr.stdin.write(render(fi).tobytes())
        pr.stdin.close()
        if pr.wait() != 0:
            sys.exit(1)
        os.replace(tmp, out)
        print("done", out)
