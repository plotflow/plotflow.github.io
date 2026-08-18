#!/usr/bin/env python3
"""
gen_fish.py — procedural fish via LingDong Huang's fishdraw (MIT).

Runs the vendored fishdraw.js (tools/vendor/fishdraw/, MIT © 2021
Lingdong Huang) under node, takes its polylines, and fits the fish onto
the studio sheet in the pipeline's M/L-only SVG dialect, with a PNG
preview. The seed string names the fish — same seed, same fish.

Usage:  python tools/gen_fish.py               # seed "plotflow"
        python tools/gen_fish.py "koi dream"   # chosen seed
"""
import os, sys, json, math, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets", "generative")
FISHJS = os.path.join(HERE, "vendor", "fishdraw", "fishdraw.js")

W, H = 1400, 1100          # landscape sheet (14x11), fish are wide
MARGIN = 120


def run_fishdraw(seed):
    out = subprocess.run(
        ["node", FISHJS, "--seed", str(seed), "--format", "json"],
        capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def fit(polys):
    xs = [p[0] for pl in polys for p in pl]
    ys = [p[1] for pl in polys for p in pl]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    s = min((W - 2 * MARGIN) / (x1 - x0), (H - 2 * MARGIN) / (y1 - y0))
    ox = (W - (x1 - x0) * s) / 2 - x0 * s
    oy = (H - (y1 - y0) * s) / 2 - y0 * s
    return [[(x * s + ox, y * s + oy) for x, y in pl] for pl in polys]


def to_svg(polys, path):
    sub = []
    for p in polys:
        pieces = ["M %.2f,%.2f" % p[0]]
        pieces += ["L %.2f,%.2f" % q for q in p[1:]]
        sub.append(" ".join(pieces))
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d">\n'
           '<path d="%s" fill="none" stroke="#15160f" stroke-width="0.8"/>\n'
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
    seed = sys.argv[1] if len(sys.argv) > 1 else "plotflow"
    polys = fit(run_fishdraw(seed))
    slug = "".join(c if c.isalnum() else "-" for c in str(seed)).strip("-")
    base = os.path.join(OUT, "fish-%s" % slug)
    to_svg(polys, base + ".svg")
    to_png(polys, base + ".png")
    ink = sum(sum(math.hypot(p[i+1][0]-p[i][0], p[i+1][1]-p[i][1])
                  for i in range(len(p)-1)) for p in polys) * (420/1400) / 1000
    print("fish seed=%r strokes=%d ink=%.1fm -> %s.{svg,png}" % (seed, len(polys), ink, base))
