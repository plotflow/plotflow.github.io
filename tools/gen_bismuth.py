#!/usr/bin/env python3
"""
gen_bismuth.py — hopper-crystal clusters for the plotter.

Bismuth grows skeletal "hopper" crystals: the edges of each face grow
faster than the centre, leaving stepped, funnel-like terraces. Drawn
flat, a hopper is a staircase of concentric rectangles whose centres
drift toward one corner as they shrink — that drift is what reads as
depth. A cluster of them at mixed sizes and rotations is the classic
bismuth specimen.

Direct construction, seeded RNG: every seed is a different specimen.
Output is M/L-only SVG in the pipeline dialect + PNG preview.

Usage:  python tools/gen_bismuth.py           # seed 3
        python tools/gen_bismuth.py 42        # chosen seed
"""
import os, sys, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets", "generative")

W, H = 1100, 1400
MARGIN = 110


def hopper(rng, cx, cy, size, rot):
    """One hopper crystal: a staircase of drifting concentric rectangles."""
    polys = []
    aspect = rng.uniform(0.88, 1.12)
    shrink = rng.uniform(0.86, 0.91)
    twist = rng.uniform(-0.02, 0.02)
    # the funnel sinks toward one corner — pick it once per crystal
    sink = rng.uniform(0, 2 * math.pi)
    drift_k = rng.uniform(0.55, 0.92)
    jit = size * 0.006

    s, th = size, rot
    x, y = cx, cy
    while s > size * 0.06:
        hw, hh = s / 2, s * aspect / 2
        corners = np.array([[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]])
        c, snt = math.cos(th), math.sin(th)
        R = np.array([[c, -snt], [snt, c]])
        pts = corners @ R.T + [x, y]
        pts = pts + rng.normal(0, jit, size=pts.shape)
        polys.append([tuple(p) for p in pts] + [tuple(pts[0])])
        # next terrace: smaller, twisted, drifted toward the sink corner —
        # drift is capped at the shrink amount so every ring stays nested
        # inside the previous one (unbounded drift telescopes into trails)
        room = s * (1 - shrink) / 2
        x += math.cos(sink) * room * drift_k
        y += math.sin(sink) * room * drift_k
        s *= shrink
        th += twist
    return polys


def cluster(seed=3, n=14):
    rng = np.random.default_rng(seed)
    placed = []          # (x, y, r)
    polys = []
    # one anchor crystal, then satellites by rejection sampling
    sizes = sorted(rng.uniform(90, 340, n))[::-1]
    sizes[0] = rng.uniform(330, 400)
    for s in sizes:
        for _ in range(400):
            x = rng.uniform(MARGIN + s / 2, W - MARGIN - s / 2)
            y = rng.uniform(MARGIN + s / 2, H - MARGIN - s / 2)
            # allow only shallow intergrowth — deep overlap between two large
            # crystals interleaves their terraces into a noisy ladder
            ok = all(math.hypot(x - px, y - py) > 0.78 * (s / 2 + pr)
                     for px, py, pr in placed)
            if ok:
                placed.append((x, y, s / 2))
                polys += hopper(rng, x, y, s, rng.uniform(0, math.pi / 2))
                break
    return polys


def to_svg(polys, path):
    sub = []
    for p in polys:
        pieces = ["M %.2f,%.2f" % p[0]]
        pieces += ["L %.2f,%.2f" % q for q in p[1:]]
        sub.append(" ".join(pieces))
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d">\n'
           '<path d="%s" fill="none" stroke="#15160f" stroke-width="0.7"/>\n'
           '</svg>\n') % (W, H, " ".join(sub))
    with open(path, "w") as f:
        f.write(svg)


def to_png(polys, path, scale=1.0, ss=2):
    from PIL import Image, ImageDraw
    w, h = int(W * scale) * ss, int(H * scale) * ss
    im = Image.new("RGB", (w, h), (246, 243, 236))
    dr = ImageDraw.Draw(im)
    k = scale * ss
    for p in polys:
        dr.line([(x * k, y * k) for x, y in p], fill=(21, 22, 15), width=ss)
    im = im.resize((w // ss, h // ss), Image.LANCZOS)
    im.save(path)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    polys = cluster(seed=seed)
    base = os.path.join(OUT, "bismuth-s%d" % seed)
    to_svg(polys, base + ".svg")
    to_png(polys, base + ".png")
    ink = sum(sum(math.hypot(p[i+1][0]-p[i][0], p[i+1][1]-p[i][1])
                  for i in range(len(p)-1)) for p in polys) * (420/1400) / 1000
    print("bismuth seed=%d rings=%d ink=%.1fm -> %s.{svg,png}" % (seed, len(polys), ink, base))
