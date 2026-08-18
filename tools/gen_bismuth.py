#!/usr/bin/env python3
"""
gen_bismuth.py — randomized 3D bismuth hopper crystals for the plotter.

Real bismuth grows skeletal "hopper" crystals: the rim of each face
grows faster than the centre, so the face develops as a square spiral
staircase descending into the crystal. Here each crystal is modelled in
3D — a block prism whose top face carries an inverted ziggurat of
terraces (closed rings stepping down and inward, with corner risers) —
then the whole cluster is axonometrically projected to the sheet.
Wireframe only: what the pen can draw.

Seeded RNG throughout: every seed is a different specimen cluster.
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
TILT = 1.02          # camera tilt (rad): ~30° above the horizon


def ring_corners(s, aspect, twist_th):
    hw, hh = s / 2, s * aspect / 2
    c = np.array([[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]], float)
    ct, st = math.cos(twist_th), math.sin(twist_th)
    R = np.array([[ct, -st], [st, ct]])
    return c @ R.T


def hopper3d(rng, s0):
    """One crystal in local 3D coords (z up; hopper descends below z=0).
    Returns a list of 3D polylines (Nx3 arrays)."""
    aspect = rng.uniform(0.9, 1.1)
    shrink = rng.uniform(0.78, 0.88)
    dz = rng.uniform(0.016, 0.030) * s0          # step depth per terrace — shallow:
    # a hopper pit is much wider than deep, or it projects as a spike
    twist = rng.uniform(-0.03, 0.03)
    sink = rng.uniform(0, 2 * math.pi)           # drift direction of the funnel
    drift_k = rng.uniform(0.25, 0.7)
    body_h = rng.uniform(0.22, 0.34) * s0         # visible prism height

    polys = []
    s, th, k = s0, 0.0, 0
    cx = cy = 0.0
    prev = None
    while s > s0 * 0.12:
        c2 = ring_corners(s, aspect, th) + [cx, cy]
        z = -k * dz
        ring = np.column_stack([c2, np.full(4, z)])
        polys.append(np.vstack([ring, ring[:1]]))          # closed terrace
        if prev is not None:
            for i in range(4):                             # corner risers
                polys.append(np.array([prev[i], ring[i]]))
        prev = ring
        room = s * (1 - shrink) / 2
        cx += math.cos(sink) * room * drift_k
        cy += math.sin(sink) * room * drift_k
        s *= shrink
        th += twist
        k += 1

    # crystal body: outer rim extruded downward + base outline
    top = np.column_stack([ring_corners(s0, aspect, 0.0), np.zeros(4)])
    base = top.copy()
    base[:, 2] = -body_h
    for i in range(4):
        polys.append(np.array([top[i], base[i]]))
    polys.append(np.vstack([base, base[:1]]))
    return polys


def project(polys3d, yaw, scale, ox, oy):
    """Yaw about z, tilt toward camera, orthographic drop of depth."""
    cy_, sy_ = math.cos(yaw), math.sin(yaw)
    Rz = np.array([[cy_, -sy_, 0], [sy_, cy_, 0], [0, 0, 1]])
    ct, st = math.cos(TILT), math.sin(TILT)
    out = []
    for p in polys3d:
        q = p @ Rz.T
        x = q[:, 0]
        y = q[:, 1] * st - q[:, 2] * ct          # tilt: depth lifts, z drops
        out.append(np.column_stack([ox + x * scale, oy - y * scale]))
    return out


def cluster(seed=3, n=11):
    rng = np.random.default_rng(seed)
    placed = []
    polys = []
    sizes = sorted(rng.uniform(120, 300, n))[::-1]
    sizes[0] = rng.uniform(320, 380)
    for s in sizes:
        r_screen = s * 0.72                       # projected footprint radius
        for _ in range(500):
            x = rng.uniform(MARGIN + r_screen, W - MARGIN - r_screen)
            y = rng.uniform(MARGIN + r_screen, H - MARGIN - r_screen)
            if all(math.hypot(x - px, y - py) > 0.74 * (r_screen + pr)
                   for px, py, pr in placed):
                placed.append((x, y, r_screen))
                p3 = hopper3d(rng, s)
                polys += project(p3, rng.uniform(0, math.pi / 2), 1.0, x, y)
                break
    return polys


def to_svg(polys, path):
    sub = []
    for p in polys:
        pieces = ["M %.2f,%.2f" % (p[0][0], p[0][1])]
        pieces += ["L %.2f,%.2f" % (q[0], q[1]) for q in p[1:]]
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
        dr.line([(q[0] * k, q[1] * k) for q in p], fill=(21, 22, 15), width=ss)
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
    print("bismuth3d seed=%d polylines=%d ink=%.1fm -> %s.{svg,png}" % (seed, len(polys), ink, base))
