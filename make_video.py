#!/usr/bin/env python3
"""Generate one satisfying video.

  python3 make_video.py --concept ring_escape --seed 1234 --out videos/x.mp4
  python3 make_video.py --concept random --seed 99 --out videos/y.mp4

Writes the .mp4 and a .json next to it (concept, params, caption, duration).
Every seed gives different colours, counts, key and pacing.
"""
import argparse, json, os, random, shutil, subprocess, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
CONCEPTS = ["rings_countdown", "ring_escape"]

PALETTES = {
    "sunset": [[0, [255, 40, 110]], [0.14, [255, 70, 80]], [0.32, [255, 140, 60]], [0.5, [255, 214, 90]],
               [0.68, [255, 150, 60]], [0.86, [255, 60, 120]], [1, [225, 40, 160]]],
    "ocean": [[0, [40, 120, 255]], [0.3, [0, 220, 255]], [0.5, [120, 255, 230]], [0.7, [0, 180, 255]],
              [1, [130, 60, 255]]],
    "toxic": [[0, [60, 255, 120]], [0.3, [180, 255, 60]], [0.5, [255, 240, 80]], [0.7, [120, 255, 90]],
              [1, [0, 200, 160]]],
    "candy": [[0, [255, 80, 200]], [0.3, [190, 90, 255]], [0.5, [110, 170, 255]], [0.7, [200, 100, 255]],
              [1, [255, 90, 170]]],
    "fire": [[0, [255, 40, 40]], [0.3, [255, 110, 30]], [0.5, [255, 200, 60]], [0.7, [255, 120, 40]],
             [1, [220, 30, 60]]],
    "ice": [[0, [180, 240, 255]], [0.3, [90, 200, 255]], [0.5, [230, 250, 255]], [0.7, [120, 170, 255]],
            [1, [170, 130, 255]]],
}
BALLS = {"sunset": [0.45, 1.0, 0.92], "ocean": [1.0, 0.55, 0.75], "toxic": [1.0, 0.4, 0.9],
         "candy": [0.5, 1.0, 0.9], "fire": [0.45, 0.9, 1.0], "ice": [1.0, 0.7, 0.3]}
PROGS = [["Am", "F", "C", "G"], ["Am", "C", "G", "F"], ["Am", "G", "F", "C"]]

HASHTAGS = ["#satisfying", "#satisfyingvideo", "#oddlysatisfying", "#asmr", "#fyp", "#pourtoi",
            "#relaxing", "#physics", "#neon", "#visualizer"]
CAPTIONS = {
    "ring_escape": [
        "Elle s'échappe en combien de temps ? ⏱️ Mets ton pronostic 👇",
        "{n} anneaux, 1 seule boule. Elle va y arriver ? 👀",
        "Attends le dernier anneau… 🤯",
        "Devine le chrono final avant la fin ⏱️👇",
        "Ton cerveau va adorer ce son 🔊",
        "Moins de {t}s ou plus ? Réponds avant la fin 👇",
    ],
    "rings_countdown": [
        "Le compte à rebours le plus satisfaisant 😮‍💨",
        "Regarde jusqu'à 0… 🔊 Son à fond",
        "{n} anneaux détruits en rythme 🎧",
        "Ça devient incroyable à la fin 🔥",
        "Chaque impact tombe pile sur le beat 🎶",
    ],
}


def random_params(concept, seed):
    r = random.Random(seed)
    prm = {"seed": seed, "key_shift": r.choice([-3, -2, 0, 2, 3]), "progression": r.choice(PROGS)}
    if concept == "rings_countdown":
        pal = r.choice(list(PALETTES))
        prm.update(palette_name=pal, palette=PALETTES[pal], ball_color=BALLS[pal],
                   n_rings=r.randint(135, 165), bpm=r.choice([120, 124, 128, 132]))
    else:
        prm.update(n_rings=r.randint(15, 22), hue_start=r.random(),
                   hue_span=r.choice([-0.8, 0.8, -0.55, 0.55, -1.0]),
                   saturation=round(r.uniform(0.74, 0.9), 2), gap_deg=round(r.uniform(33, 38), 1),
                   omega=round(r.uniform(2.6, 3.1) * r.choice([1, -1]), 2),
                   spiral_deg=round(r.uniform(5, 10), 1), target_time=round(r.uniform(18, 24), 1))
    return prm


def caption_for(concept, prm, stats, seed):
    r = random.Random(seed * 7 + 1)
    base = r.choice(CAPTIONS[concept])
    t_hint = int(round(stats.get("t_esc", 20) / 5.0) * 5) or 20
    text = base.format(n=prm.get("n_rings", ""), t=t_hint)
    tags = ["#satisfying", "#fyp", "#pourtoi"] + r.sample(HASHTAGS[1:5] + HASHTAGS[6:], 3)
    return text + " " + " ".join(dict.fromkeys(tags))


def run(cmd, cwd, env, log):
    p = subprocess.run(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    log.write(p.stdout)
    if p.returncode != 0:
        print(p.stdout[-3000:])
        raise SystemExit(f"failed: {' '.join(cmd)}")
    return p.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--concept", default="random")
    ap.add_argument("--seed", type=int, default=int(time.time()) % 100000)
    ap.add_argument("--out", required=True)
    ap.add_argument("--set", action="append", default=[], help="override param key=json")
    a = ap.parse_args()
    concept = a.concept if a.concept != "random" else random.Random(a.seed).choice(CONCEPTS)
    prm = random_params(concept, a.seed)
    for kv in a.set:
        k, v = kv.split("=", 1)
        prm[k] = json.loads(v)

    out = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    work = f"/tmp/satisfy_{concept}_{a.seed}"
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(os.path.join(work, "out"))
    os.makedirs(os.path.join(work, "frames"))
    with open(os.path.join(work, "params.json"), "w") as f:
        json.dump(prm, f)
    cdir = os.path.join(ROOT, "concepts", concept)
    env = dict(os.environ, SATISFY_PARAMS=os.path.join(work, "params.json"),
               SATISFY_FONTS=os.path.join(ROOT, "fonts"), PYTHONPATH=cdir)
    log = open(os.path.join(work, "log.txt"), "w")
    py = sys.executable
    t0 = time.time()
    stats = {}
    if concept == "rings_countdown":
        run([py, os.path.join(cdir, "sim.py")], work, env, log)
        run([py, os.path.join(cdir, "audio.py")], work, env, log)
        nf = int(run([py, "-c", "from common import N_FRAMES; print(N_FRAMES)"], work, env, log).split()[-1])
        renderer = os.path.join(cdir, "render.py")
        stats["n_rings"] = prm["n_rings"]
    else:
        txt = run([py, os.path.join(cdir, "sim2.py")], work, env, log)
        run([py, os.path.join(cdir, "audio2.py")], work, env, log)
        renderer = os.path.join(cdir, "render2.py")
        nf = int(run([py, renderer, "n"], work, env, log).split()[-1])
        for line in txt.splitlines():
            if line.startswith("t_esc"):
                stats["t_esc"] = round(float(line.split()[1]), 2)
        stats["n_rings"] = prm["n_rings"]
    half = nf // 2
    procs = [subprocess.Popen([py, renderer, "seg", str(s), str(e), f"out/seg{i}.mp4"], cwd=work, env=env,
                              stdout=log, stderr=subprocess.STDOUT)
             for i, (s, e) in enumerate([(0, half), (half, nf)])]
    if any(p.wait() != 0 for p in procs):
        raise SystemExit("render failed, see " + work + "/log.txt")
    with open(os.path.join(work, "out", "list.txt"), "w") as f:
        f.write("file 'seg0.mp4'\nfile 'seg1.mp4'\n")
    ff = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    run(ff + ["-f", "concat", "-safe", "0", "-i", "out/list.txt", "-c", "copy", "out/v.mp4"], work, env, log)
    tmp = out[:-4] + ".part.mp4"
    run(ff + ["-i", "out/v.mp4", "-i", "out/audio.wav", "-map", "0:v", "-map", "1:a", "-c:v", "copy",
              "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", tmp], work, env, log)
    os.replace(tmp, out)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                "default=nw=1:nk=1", out], stdout=subprocess.PIPE, text=True).stdout)
    meta = dict(concept=concept, seed=a.seed, params=prm, stats=stats, duration=round(dur, 2),
                caption=caption_for(concept, prm, stats, a.seed), size_mb=round(os.path.getsize(out) / 1e6, 1),
                render_s=round(time.time() - t0))
    with open(out[:-4] + ".json", "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    shutil.rmtree(work, ignore_errors=True)
    print(json.dumps({k: meta[k] for k in ("concept", "seed", "duration", "size_mb", "render_s", "caption")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
