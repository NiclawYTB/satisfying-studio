#!/usr/bin/env python3
"""Generate one satisfying video.

  python3 make_video.py --concept ring_escape --seed 1234 --out videos/x.mp4
  python3 make_video.py --concept random --seed 99 --out videos/y.mp4

Writes the .mp4 and a .json next to it (concept, params, caption, duration).
Every seed gives different colours, counts, key and pacing.
"""
import argparse, json, os, random, shutil, subprocess, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
CONCEPTS = ["ring_escape", "barrier_drop", "galton_board"]

HASHTAGS = ["#satisfying", "#satisfyingvideo", "#oddlysatisfying", "#asmr", "#relaxing", "#calm",
            "#physics", "#fyp", "#pourtoi"]
CAPTIONS = {
    "ring_escape": [
        "Elle s'échappe en combien de temps ? ⏱️ Mets ton pronostic 👇",
        "{n} anneaux, 1 seule boule. Elle va y arriver ? 👀",
        "Attends le dernier anneau… 🤯",
        "Devine le chrono final avant la fin ⏱️👇",
        "Le son quand elle sort… 😮‍💨🔊",
    ],
    "barrier_drop": [
        "{n} barrières de verre… elle va toutes les casser ? 🔨",
        "Le bruit du verre est trop satisfaisant 🔊",
        "Combien de rebonds au total ? Réponds avant la fin 👇",
        "Regarde jusqu'à l'arrivée ✨",
        "ASMR verre cassé 💎 son à fond",
    ],
    "galton_board": [
        "{n} billes et à la fin… la courbe parfaite 🤯",
        "Le hasard dessine toujours la même forme 👀",
        "Regarde jusqu'à la fin, c'est hypnotisant ✨",
        "La planche de Galton : les maths en vrai 🧠",
        "Son apaisant 🔊 regarde la courbe se former",
    ],
}
KEYS = [-3, -2, 0, 2, 3, 5]


def random_params(concept, seed):
    r = random.Random(seed)
    prm = {"seed": seed, "key_shift": r.choice(KEYS)}
    if concept == "ring_escape":
        prm.update(n_rings=r.randint(15, 22), hue_start=r.random(),
                   hue_span=r.choice([-0.8, 0.8, -0.55, 0.55, -1.0]),
                   saturation=round(r.uniform(0.6, 0.85), 2), gap_deg=round(r.uniform(33, 38), 1),
                   omega=round(r.uniform(2.6, 3.1) * r.choice([1, -1]), 2),
                   spiral_deg=round(r.uniform(5, 10), 1), target_time=round(r.uniform(17, 21), 1),
                   n_slowmo=1)
    elif concept == "barrier_drop":
        prm.update(n_barriers=r.randint(18, 21), hue_start=r.random(), hue_span=r.choice([0.3, 0.45, -0.45, 0.6]),
                   saturation=round(r.uniform(0.45, 0.65), 2))
    else:
        prm.update(hue_start=r.random(), hue_span=r.choice([0.9, -0.9, 0.6, 1.0]),
                   saturation=round(r.uniform(0.5, 0.7), 2), rate1=r.choice([50, 55, 60]))
    return prm


def caption_for(concept, prm, stats, seed):
    r = random.Random(seed * 7 + 1)
    base = r.choice(CAPTIONS[concept])
    t_hint = int(round(stats.get("t_esc", 20) / 5.0) * 5) or 20
    text = base.format(n=stats.get("n", ""), t=t_hint)
    tags = ["#satisfying", "#fyp", "#pourtoi"] + r.sample(HASHTAGS[1:7], 3)
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
               SATISFY_FONTS=os.path.join(ROOT, "fonts"), PYTHONPATH=cdir + os.pathsep + os.path.join(ROOT, "lib"))
    log = open(os.path.join(work, "log.txt"), "w")
    py = sys.executable
    t0 = time.time()
    stats = {}
    scripts = {"ring_escape": ("sim2.py", "audio2.py", "render2.py"),
               "barrier_drop": ("sim3.py", "audio3.py", "render3.py"),
               "galton_board": ("sim4.py", "audio4.py", "render4.py")}[concept]
    txt = run([py, os.path.join(cdir, scripts[0])], work, env, log)
    run([py, os.path.join(cdir, scripts[1])], work, env, log)
    renderer = os.path.join(cdir, scripts[2])
    nf = int(run([py, renderer, "n"], work, env, log).split()[-1])
    for line in txt.splitlines():
        if line.startswith("t_esc"):
            stats["t_esc"] = round(float(line.split()[1]), 2)
        if line.startswith("balls"):
            stats["n"] = int(line.split()[1])
    if concept == "ring_escape":
        stats["n"] = prm["n_rings"]
    elif concept == "barrier_drop":
        stats["n"] = prm["n_barriers"]
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
