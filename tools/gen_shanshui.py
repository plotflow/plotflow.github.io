#!/usr/bin/env python3
"""
gen_shanshui.py — a sheet of {Shan, Shui}* via LingDong Huang's
shan-shui-inf (MIT, vendored in tools/vendor/shan-shui/), reinterpreted
for the pen.

The original paints an infinite scroll with brush strokes as filled
polygons, grey washes for tone, and white shapes for occlusion. A pen
has exactly one mark, so the conversion keeps the dark ink marks
(drawn as line work), and drops washes and masks — a plotter's reading
of the painting, not a reproduction of it.

Runs the generator headless (Chromium via Playwright), captures a
sheet-sized window of the scroll, and emits the pipeline's M/L-only SVG
+ a PNG preview. Seed string → same landscape forever.

Usage:  python tools/gen_shanshui.py                 # seed "plotflow"
        python tools/gen_shanshui.py mountain-04     # chosen seed
        python tools/gen_shanshui.py mountain-04 600 # window start x
"""
import os, re, sys, math

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
OUT = os.path.join(ROOT, "assets", "generative")

W, H = 1400, 1100        # landscape sheet
SCENE_H = 800            # shan-shui scroll height
Y_OFF = (H - SCENE_H) / 2


def capture(seed, timeout_ms=12000):
    from playwright.sync_api import sync_playwright
    url_path = os.path.join("tools", "vendor", "shan-shui", "index.html")
    with sync_playwright() as p:
        b = p.chromium.launch(
            executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
            args=["--no-sandbox"])
        pg = b.new_page(viewport={"width": 1600, "height": 900})
        pg.goto("http://localhost:8811/%s?%s" % (url_path.replace(os.sep, "/"), seed),
                wait_until="domcontentloaded")
        pg.wait_for_timeout(timeout_ms)
        canv = pg.evaluate("() => MEM.canv")
        b.close()
    return canv


def parse(canv, x0, x1, min_alpha=0.0):
    """Dark ink marks inside the window → list of (closed, polyline).
    min_alpha drops the palest shading strokes — the painting stacks
    low-opacity marks for tone, but a pen lays every line at full dark,
    so alpha becomes the plot-density dial."""
    out = []
    for m in re.finditer(r"<polyline points='([^']*)'[^>]*style='([^']*)'", canv):
        style = m.group(2)
        if "100,100,100" not in style:
            continue                       # washes, mist, white masks: tone, not line
        am = re.search(r"rgba\(100,100,100,([0-9.]+)\)", style)
        if am and float(am.group(1)) < min_alpha:
            continue
        pts = m.group(1).split()
        poly = []
        for t in pts:
            x, y = t.split(",")
            poly.append((float(x), float(y)))
        if len(poly) < 2:
            continue
        xs = [p[0] for p in poly]
        if max(xs) < x0 or min(xs) > x1:
            continue
        closed = "fill:rgba" in style       # filled brush-mark polygons close
        poly = [(x - x0, y + Y_OFF) for x, y in poly]
        out.append((closed, poly))
    return out


def to_svg(marks, path):
    sub = []
    for closed, p in marks:
        pieces = ["M %.2f,%.2f" % p[0]]
        pieces += ["L %.2f,%.2f" % q for q in p[1:]]
        if closed:
            pieces.append("L %.2f,%.2f" % p[0])
        sub.append(" ".join(pieces))
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d">\n'
           '<path d="%s" fill="none" stroke="#15160f" stroke-width="0.55"/>\n'
           '</svg>\n') % (W, H, " ".join(sub))
    with open(path, "w") as f:
        f.write(svg)


def to_png(marks, path, scale=1.0, ss=2):
    from PIL import Image, ImageDraw
    w, h = int(W * scale) * ss, int(H * scale) * ss
    im = Image.new("RGB", (w, h), (246, 243, 236))
    dr = ImageDraw.Draw(im)
    k = scale * ss
    for closed, p in marks:
        xy = [(x * k, y * k) for x, y in p]
        if closed:
            xy.append(xy[0])
        dr.line(xy, fill=(21, 22, 15), width=1)
    im = im.resize((w // ss, h // ss), Image.LANCZOS)
    im.save(path)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    seed = sys.argv[1] if len(sys.argv) > 1 else "plotflow"
    x0 = float(sys.argv[2]) if len(sys.argv) > 2 else 100.0
    min_alpha = float(sys.argv[3]) if len(sys.argv) > 3 else 0.3
    canv = capture(seed)
    marks = parse(canv, x0, x0 + W, min_alpha)
    slug = "".join(c if c.isalnum() else "-" for c in str(seed)).strip("-")
    base = os.path.join(OUT, "shanshui-%s" % slug)
    to_svg(marks, base + ".svg")
    to_png(marks, base + ".png")
    ink = sum(sum(math.hypot(p[i+1][0]-p[i][0], p[i+1][1]-p[i][1])
                  for i in range(len(p)-1)) for _, p in marks) * (420/1400) / 1000
    print("shanshui seed=%r marks=%d ink=%.1fm -> %s.{svg,png}" % (seed, len(marks), ink, base))
