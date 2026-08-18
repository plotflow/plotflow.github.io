#!/usr/bin/env python3
"""
gen_diffline.py: differential line growth for the plotter.

An original implementation of the classic differential-growth technique
(a closed loop of nodes: each node springs toward its two chain
neighbours, is repelled by every node within a radius, and edges that
stretch past a limit are split). Recording the loop every few steps and
drawing all snapshots on one sheet produces the layered, sheet-like
forms this family of algorithms is known for.

Output is plotter-honest SVG: M/L polylines only, one subpath per
recorded generation: so a piece can drop straight into the site
pipeline (tools/build_data.py) or PlotGrid.

Usage:  python tools/gen_diffline.py            # all presets
        python tools/gen_diffline.py bloom 7    # one preset, seed 7
"""
import os, sys, math
import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets", "generative")

# sheet in working units (11x14 aspect); margins keep growth off the edge
W, H = 1100, 1400
MARGIN = 90


def grow(seed=1, steps=950, snap_grow=1.10,
         n0=42, r0=36.0,
         d_split=5.0,          # split an edge longer than this
         r_rep=24.0,           # repulsion radius
         k_att=0.5, k_rep=0.9, k_noise=0.35,
         step_max=2.2, n_max=12000, ins_rate=85,
         center=(W / 2, H / 2), stretch=(1.0, 1.0), rot=0.0):
    """Run the growth and return a list of snapshot loops (Nx2 arrays)."""
    rng = np.random.default_rng(seed)
    th = np.linspace(0, 2 * math.pi, n0, endpoint=False)
    pts = np.stack([np.cos(th) * r0, np.sin(th) * r0], axis=1)
    # anisotropic seed: stretching + rotating the starting loop biases the
    # whole growth into bands / diagonals instead of a round bloom
    S = np.array([[stretch[0], 0], [0, stretch[1]]])
    R = np.array([[math.cos(rot), -math.sin(rot)], [math.sin(rot), math.cos(rot)]])
    pts = pts @ S.T @ R.T + np.array(center)

    snaps = []
    last_len = 0.0
    for it in range(steps):
        n = len(pts)
        prv = np.roll(pts, 1, axis=0)
        nxt = np.roll(pts, -1, axis=0)
        # spring toward chain neighbours
        force = k_att * ((prv - pts) + (nxt - pts))

        # repulsion from every node within r_rep (excluding immediate chain)
        tree = cKDTree(pts)
        pairs = tree.query_pairs(r_rep, output_type="ndarray")
        if len(pairs):
            i, j = pairs[:, 0], pairs[:, 1]
            ring = np.minimum((i - j) % n, (j - i) % n)
            keep = ring > 1
            i, j = i[keep], j[keep]
            d = pts[i] - pts[j]
            dist = np.linalg.norm(d, axis=1) + 1e-9
            w = (r_rep - dist) / r_rep
            push = d / dist[:, None] * (k_rep * w)[:, None]
            np.add.at(force, i, push)
            np.add.at(force, j, -push)

        force += rng.normal(0, k_noise, size=pts.shape)

        # soft boundary: past the margin, push back proportionally :
        # a hard clamp stacks nodes on the wall and blows up the pair count
        over = np.zeros_like(pts)
        over[:, 0] += np.maximum(0, MARGIN - pts[:, 0]) - np.maximum(0, pts[:, 0] - (W - MARGIN))
        over[:, 1] += np.maximum(0, MARGIN - pts[:, 1]) - np.maximum(0, pts[:, 1] - (H - MARGIN))
        force += 0.22 * over

        # clamp step length
        mag = np.linalg.norm(force, axis=1, keepdims=True) + 1e-9
        force = force * np.minimum(1.0, step_max / mag)
        pts = pts + force

        # split long edges (midpoint + a whisper of noise)
        e = np.linalg.norm(np.roll(pts, -1, axis=0) - pts, axis=1)
        long_idx = np.nonzero(e > d_split)[0]
        if len(pts) >= n_max:
            long_idx = long_idx[:0]
        if len(long_idx):
            mids = (pts[long_idx] + pts[(long_idx + 1) % len(pts)]) / 2
            mids += rng.normal(0, 0.08, size=mids.shape)
            pts = np.insert(pts, long_idx + 1, mids, axis=0)

        # continuous growth: also insert midpoints on random edges: this is
        # what drives the buckling. Without it the loop settles and stops.
        if len(pts) < n_max:
            n_ins = max(1, len(pts) // ins_rate)
            ins = rng.choice(len(pts), size=n_ins, replace=False)
            ins = np.sort(ins)
            mids = (pts[ins] + pts[(ins + 1) % len(pts)]) / 2
            mids += rng.normal(0, 0.08, size=mids.shape)
            pts = np.insert(pts, ins + 1, mids, axis=0)

        # record a generation each time the loop has grown ~10% in length :
        # geometric spacing keeps the drawn sheets separated instead of
        # burying the plot under hundreds of coincident loops
        total = float(np.sum(np.linalg.norm(np.roll(pts, -1, axis=0) - pts, axis=1)))
        if total >= last_len * snap_grow or it == steps - 1:
            snaps.append(pts.copy())
            last_len = max(total, 1.0)
    return snaps


def to_svg(snaps, path):
    sub = []
    for s in snaps:
        pieces = ["M %.2f,%.2f" % (s[0, 0], s[0, 1])]
        pieces += ["L %.2f,%.2f" % (x, y) for x, y in s[1:]]
        pieces.append("L %.2f,%.2f" % (s[0, 0], s[0, 1]))   # close the loop
        sub.append(" ".join(pieces))
    d = " ".join(sub)
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d">\n'
           '<path d="%s" fill="none" stroke="#15160f" stroke-width="0.45"/>\n'
           '</svg>\n') % (W, H, d)
    with open(path, "w") as f:
        f.write(svg)
    return sum(len(s) for s in snaps)


def to_png(snaps, path, scale=1.0, ss=2):
    from PIL import Image, ImageDraw
    w, h = int(W * scale) * ss, int(H * scale) * ss
    im = Image.new("RGB", (w, h), (246, 243, 236))
    dr = ImageDraw.Draw(im)
    k = scale * ss
    for s in snaps:
        xy = [(x * k, y * k) for x, y in s] + [(s[0, 0] * k, s[0, 1] * k)]
        dr.line(xy, fill=(21, 22, 15), width=1)
    im = im.resize((w // ss, h // ss), Image.LANCZOS)
    im.save(path)


PRESETS = {
    # round bloom growing from centre: the classic
    "bloom":  dict(steps=950, n0=48, r0=40),
    # long diagonal band, like sheeted fabric
    "band":   dict(steps=950, n0=72, r0=30, stretch=(6.5, 0.55),
                   rot=-0.62, r_rep=21.0),
    # tall column, tighter repulsion → denser folds
    "column": dict(steps=950, n0=56, r0=26, stretch=(0.6, 4.6),
                   r_rep=19.0),
    # organic labyrinth (after Pedersen & Singh): confined growth tuned for
    # even corridor spacing; only the FINAL curve is drawn, one closed line
    "labyrinth": dict(steps=1600, n0=60, r0=40, r_rep=14.0, d_split=4.2,
                      ins_rate=70, n_max=30000, k_noise=0.3, step_max=1.8,
                      final_only=True),
}

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    which = sys.argv[1] if len(sys.argv) > 1 else None
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 11
    for name, kw in PRESETS.items():
        if which and name != which:
            continue
        kw = dict(kw)
        final_only = kw.pop("final_only", False)
        snaps = grow(seed=seed, **kw)
        if final_only:
            snaps = snaps[-1:]
        base = os.path.join(OUT, "diffline-%s-s%d" % (name, seed))
        verts = to_svg(snaps, base + ".svg")
        to_png(snaps, base + ".png")
        print("%-8s gens=%d verts=%d -> %s.{svg,png}" % (name, len(snaps), verts, base))
