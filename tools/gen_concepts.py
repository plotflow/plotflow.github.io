#!/usr/bin/env python3
"""
gen_concepts.py — mock up NEW post/reel design directions for review.

Renders to  mockups/  so you can thumbs-up/down before any of these graduate
into tools/gen_posts.py. Run from the repo root:  python tools/gen_concepts.py

Concepts:
  A  gradient   — the path colored start→end to show the draw order
  B  blueprint  — dark technical schematic, cyan on navy, grid + reg marks
  C  macro      — extreme abstract crop of the linework, gallery-object energy
  D  roster     — all six suits as a contact-sheet collection poster
  E  statement  — bold typographic philosophy card
"""
import json, math, os, re
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = json.loads(open(os.path.join(ROOT, 'data/editions.js')).read().split('=', 1)[1].rsplit(';', 1)[0])
SUITS = DATA['suits']
ORDER = DATA.get('shopOrder', list(SUITS.keys()))

OUT = os.path.join(ROOT, 'mockups')
os.makedirs(OUT, exist_ok=True)

S = 1080; SS = 3; C = S * SS
INK   = (21, 22, 15)
RED   = (232, 53, 31)
PAPER = (246, 243, 236)
DIM   = (143, 145, 132)
MUTE  = (195, 197, 184)
NAVY  = (13, 22, 38)
CYAN  = (76, 201, 240)
GOLD  = (242, 183, 5)
INDIGO= (43, 45, 90)
WHITE = (255, 255, 255)

BOLD = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
REG  = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
JP   = '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf'
def F(f, px): return ImageFont.truetype(f, int(px))

def parse_path(d):
    subpaths, cur = [], []
    for cmd, xs, ys in re.findall(r'([ML])\s*(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)', d):
        x, y = float(xs), float(ys)
        if cmd == 'M':
            if len(cur) > 1: subpaths.append(cur)
            cur = [(x, y)]
        else: cur.append((x, y))
    if len(cur) > 1: subpaths.append(cur)
    return subpaths

def bbox(sp):
    xs = [p[0] for s in sp for p in s]; ys = [p[1] for s in sp for p in s]
    return min(xs), min(ys), max(xs), max(ys)

def fit(bb, region, pad_frac=0.06):
    minx, miny, maxx, maxy = bb
    pad = max(maxx-minx, maxy-miny) * pad_frac
    minx -= pad; miny -= pad; vbw = (maxx-minx)+pad; vbh = (maxy-miny)+pad
    rx, ry, rw, rh = region
    sc = min(rw/vbw, rh/vbh)
    ox = rx + (rw - vbw*sc)/2; oy = ry + (rh - vbh*sc)/2
    return (lambda x, y: (ox+(x-minx)*sc, oy+(y-miny)*sc)), sc

def total_len(sp):
    t = 0.0
    for s in sp:
        for i in range(len(s)-1):
            t += math.hypot(s[i+1][0]-s[i][0], s[i+1][1]-s[i][1])
    return t

def lerp(a, b, t): return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))
def grad(stops, t):
    for i in range(len(stops)-1):
        p0, c0 = stops[i]; p1, c1 = stops[i+1]
        if p0 <= t <= p1:
            return lerp(c0, c1, (t-p0)/(p1-p0 or 1))
    return stops[-1][1]

def draw_plain(d, sp, tf, color, w):
    for s in sp:
        d.line([tf(x, y) for (x, y) in s], fill=color, width=w, joint='curve')

def brand(d, xy, color, px=14):
    d.text(xy, 'PLOTFLOW*', font=F(BOLD, px*SS), fill=color)

# ============================================================
# A · GRADIENT — color the path start→end (proves one line)
# ============================================================
def concept_gradient(key, dark=False):
    s = SUITS[key]; sp = parse_path(s['d']); bb = bbox(sp)
    bg = INK if dark else PAPER
    img = Image.new('RGB', (C, C), bg); d = ImageDraw.Draw(img, 'RGBA')
    tf, _ = fit(bb, (90*SS, 150*SS, 900*SS, 700*SS))
    stops = [(0.0, INDIGO), (0.5, RED), (1.0, GOLD)]
    tot = total_len(sp); done = 0.0; w = max(2, 2*SS)
    for s2 in sp:
        for i in range(len(s2)-1):
            seg = math.hypot(s2[i+1][0]-s2[i][0], s2[i+1][1]-s2[i][1])
            t = done/tot if tot else 0
            d.line([tf(*s2[i]), tf(*s2[i+1])], fill=grad(stops, t)+(255,), width=w, joint='curve')
            done += seg
    fg = PAPER if dark else INK
    d.text((90*SS, 70*SS), s['code'], font=F(BOLD, 40*SS), fill=fg)
    d.text((90*SS, 118*SS), f"{s['name']}  {s.get('jp','')}", font=F(JP, 20*SS), fill=DIM)
    # gradient legend
    lx, ly, lw = 90*SS, C-120*SS, 380*SS
    for i in range(int(lw)):
        d.line([(lx+i, ly), (lx+i, ly+10*SS)], fill=grad(stops, i/lw), width=1)
    d.text((lx, ly-26*SS), 'COLORED IN DRAW ORDER', font=F(BOLD, 13*SS), fill=fg)
    d.text((lx, ly+18*SS), 'START', font=F(REG, 10*SS), fill=DIM)
    ew = d.textlength('END', font=F(REG, 10*SS))
    d.text((lx+lw-ew, ly+18*SS), 'END', font=F(REG, 10*SS), fill=DIM)
    brand(d, (C-90*SS-d.textlength('PLOTFLOW*', font=F(BOLD, 14*SS)), 70*SS), fg+(120,))
    img.resize((S, S), Image.LANCZOS).save(f'{OUT}/concept-{key}-gradient{"-dark" if dark else ""}.png')
    print(f'  gradient {key}{" dark" if dark else ""}')

# ============================================================
# B · BLUEPRINT — cyan schematic on navy, grid + reg marks
# ============================================================
def concept_blueprint(key):
    s = SUITS[key]; sp = parse_path(s['d']); bb = bbox(sp)
    img = Image.new('RGB', (C, C), NAVY); d = ImageDraw.Draw(img, 'RGBA')
    # grid
    step = 60*SS
    for x in range(0, C, step): d.line([(x, 0), (x, C)], fill=CYAN+(18,), width=1)
    for y in range(0, C, step): d.line([(0, y), (C, y)], fill=CYAN+(18,), width=1)
    # reg marks
    m, sz = 46*SS, 18*SS
    for cx, cy in [(m, m), (C-m, m), (m, C-m), (C-m, C-m)]:
        d.line([cx-sz, cy, cx+sz, cy], fill=CYAN+(160,), width=2*SS)
        d.line([cx, cy-sz, cx, cy+sz], fill=CYAN+(160,), width=2*SS)
    tf, _ = fit(bb, (110*SS, 150*SS, 860*SS, 680*SS))
    draw_plain(d, sp, tf, CYAN+(230,), max(2, 2*SS))
    # header
    d.text((60*SS, 46*SS), 'TECHNICAL BLUEPRINT', font=F(BOLD, 15*SS), fill=CYAN)
    d.text((60*SS, 74*SS), f"{s['code']} · {s['name']}", font=F(REG, 13*SS), fill=CYAN+(180,))
    jw = d.textlength('マシンドロー', font=F(JP, 13*SS))
    d.text((C-60*SS-jw, 50*SS), 'マシンドロー', font=F(JP, 13*SS), fill=CYAN+(150,))
    # bottom data line
    d.text((60*SS, C-70*SS), f"DRAWN BY MACHINE · {sum(len(x) for x in sp):,} VERTICES · 11×14″", font=F(REG, 12*SS), fill=CYAN+(160,))
    brand(d, (C-60*SS-d.textlength('PLOTFLOW*', font=F(BOLD, 14*SS)), C-72*SS), CYAN)
    img.resize((S, S), Image.LANCZOS).save(f'{OUT}/concept-{key}-blueprint.png')
    print(f'  blueprint {key}')

# ============================================================
# C · MACRO — extreme abstract crop of the linework
# ============================================================
def concept_macro(key):
    s = SUITS[key]; sp = parse_path(s['d']); bb = bbox(sp)
    minx, miny, maxx, maxy = bb
    # crop to the upper-center third — dense, abstract
    cw, ch = (maxx-minx), (maxy-miny)
    crop = (minx+cw*0.18, miny+ch*0.02, minx+cw*0.82, miny+ch*0.40)
    img = Image.new('RGB', (C, C), PAPER); d = ImageDraw.Draw(img, 'RGBA')
    tf, _ = fit(crop, (-60*SS, -60*SS, C+120*SS, C+120*SS), pad_frac=0.0)  # overscan/bleed
    draw_plain(d, sp, tf, RED, max(3, 3*SS))
    # minimal label chip
    d.rectangle([0, C-92*SS, C, C], fill=PAPER)
    label = f"{s['code']} · {s['name']}   "
    d.text((60*SS, C-74*SS), label, font=F(BOLD, 18*SS), fill=INK)
    lw = d.textlength(label, font=F(BOLD, 18*SS))
    d.text((60*SS+lw, C-73*SS), s.get('jp', ''), font=F(JP, 16*SS), fill=INK)  # JP font ⇒ no tofu
    d.text((60*SS, C-44*SS), 'DETAIL · DRAWN BY MACHINE', font=F(REG, 11*SS), fill=DIM)
    brand(d, (C-60*SS-d.textlength('PLOTFLOW*', font=F(BOLD, 14*SS)), C-70*SS), INK+(120,))
    img.resize((S, S), Image.LANCZOS).save(f'{OUT}/concept-{key}-macro.png')
    print(f'  macro {key}')

# ============================================================
# D · ROSTER — contact sheet of all six editions
# ============================================================
def concept_roster():
    img = Image.new('RGB', (C, C), PAPER); d = ImageDraw.Draw(img, 'RGBA')
    d.text((60*SS, 56*SS), 'THE ROSTER', font=F(BOLD, 40*SS), fill=INK)
    d.text((60*SS, 108*SS), '出撃 · current editions', font=F(JP, 18*SS), fill=DIM)
    cols, rows = 3, 2
    gx, gy = 60*SS, 190*SS
    cw = (C - 2*gx) / cols; chh = (C - gy - 90*SS) / rows
    for i, key in enumerate(ORDER):
        s = SUITS[key]; sp = parse_path(s['d']); bb = bbox(sp)
        cx = gx + (i % cols)*cw; cy = gy + (i//cols)*chh
        tf, _ = fit(bb, (cx+14*SS, cy+14*SS, cw-28*SS, chh-56*SS))
        draw_plain(d, sp, tf, RED, max(1, 1*SS)+SS)
        d.text((cx+14*SS, cy+chh-40*SS), s['code'], font=F(BOLD, 15*SS), fill=INK)
        d.text((cx+14*SS, cy+chh-18*SS), s['name'], font=F(REG, 11*SS), fill=DIM)
    d.rectangle([0, C-54*SS, C, C], fill=RED)
    d.text((60*SS, C-40*SS), 'PLOTFLOW*  ·  DRAWN BY MACHINE  ·  plotflow.io', font=F(BOLD, 12*SS), fill=WHITE)
    img.resize((S, S), Image.LANCZOS).save(f'{OUT}/concept-roster.png')
    print('  roster')

# ============================================================
# E · STATEMENT — typographic philosophy card
# ============================================================
def concept_statement(key='zaku'):
    s = SUITS[key]; sp = parse_path(s['d']); bb = bbox(sp)
    img = Image.new('RGB', (C, C), INK); d = ImageDraw.Draw(img, 'RGBA')
    tf, _ = fit(bb, (380*SS, 120*SS, 660*SS, 820*SS))
    draw_plain(d, sp, tf, RED+(45,), max(2, 2*SS))
    d.text((70*SS, 250*SS), 'NOTHING', font=F(BOLD, 92*SS), fill=PAPER)
    d.text((70*SS, 345*SS), 'IS PRINTED.', font=F(BOLD, 92*SS), fill=PAPER)
    d.text((70*SS, 470*SS), 'EVERY IMPRESSION', font=F(BOLD, 40*SS), fill=RED)
    d.text((70*SS, 522*SS), 'IS DRAWN.', font=F(BOLD, 40*SS), fill=RED)
    d.text((70*SS, 640*SS), 'マシンドロー', font=F(JP, 30*SS), fill=DIM)
    d.text((70*SS, 700*SS), 'Pigment ink on Strathmore Bristol · AxiDraw pen plotter', font=F(REG, 14*SS), fill=MUTE)
    brand(d, (70*SS, C-90*SS), PAPER)
    img.resize((S, S), Image.LANCZOS).save(f'{OUT}/concept-statement.png')
    print('  statement')


# ============================================================
# F · SPECTRUM EDITION — plotter-HONEST banded gradient
#     The path split into N arc-length bands, each a solid pen color.
#     This is what a real multi-pen swap plot would produce (stepped, not
#     smooth) — and export_spectrum_layers() writes the actual per-pen SVGs.
# ============================================================
RAMP = [(0.0, INDIGO), (0.5, RED), (1.0, GOLD)]
def band_color(b, bands): return grad(RAMP, (b + 0.5) / max(1, bands))

def _ordered_segments(sp):
    """Every segment in draw order, with cumulative arc length."""
    segs = []; cum = 0.0
    for pi, poly in enumerate(sp):
        for i in range(len(poly) - 1):
            (x0, y0), (x1, y1) = poly[i], poly[i + 1]
            L = math.hypot(x1 - x0, y1 - y0)
            if L <= 0: continue
            segs.append((pi, x0, y0, x1, y1, cum, L)); cum += L
    return segs, cum

def concept_spectrum(key, bands=8):
    s = SUITS[key]; sp = parse_path(s['d']); bb = bbox(sp)
    segs, tot = _ordered_segments(sp)
    img = Image.new('RGB', (C, C), PAPER); d = ImageDraw.Draw(img, 'RGBA')
    tf, _ = fit(bb, (90*SS, 165*SS, 900*SS, 640*SS))
    w = max(2, 2*SS)
    for (pi, x0, y0, x1, y1, cs, L) in segs:
        b = min(bands - 1, int(cs / tot * bands)) if tot else 0
        d.line([tf(x0, y0), tf(x1, y1)], fill=band_color(b, bands) + (255,), width=w, joint='curve')
    d.text((90*SS, 60*SS), s['code'], font=F(BOLD, 40*SS), fill=INK)
    d.text((90*SS, 110*SS), f'SPECTRUM EDITION · {bands}-PEN', font=F(BOLD, 16*SS), fill=RED)
    d.text((90*SS, 138*SS), f"{s['name']}  {s.get('jp','')}", font=F(JP, 18*SS), fill=DIM)
    # swatch legend = the pen set, in plot order
    lx, ly = 90*SS, C - 150*SS
    sw = (760*SS) / bands
    for b in range(bands):
        d.rectangle([lx + b*sw, ly, lx + b*sw + sw - 6*SS, ly + 40*SS], fill=band_color(b, bands))
    d.text((lx, ly - 28*SS), f'PLOT ORDER · PEN 01 → {bands:02d}', font=F(BOLD, 13*SS), fill=INK)
    d.text((lx, ly + 52*SS), 'Each band a solid pen · swapped mid-plot · exact registration', font=F(REG, 11*SS), fill=DIM)
    brand(d, (C-90*SS - d.textlength('PLOTFLOW*', font=F(BOLD, 14*SS)), 66*SS), INK+(120,))
    img.resize((S, S), Image.LANCZOS).save(f'{OUT}/concept-{key}-spectrum.png')
    print(f'  spectrum {key} ({bands}-pen)')

def export_spectrum_layers(key, bands=8):
    """Write plot-ready per-pen SVG layers (one color band each)."""
    s = SUITS[key]; sp = parse_path(s['d'])
    segs, tot = _ordered_segments(sp)
    runs = {b: [] for b in range(bands)}
    cur = {'band': None, 'poly': None, 'pts': None}
    for (pi, x0, y0, x1, y1, cs, L) in segs:
        b = min(bands - 1, int(cs / tot * bands)) if tot else 0
        start, end = (x0, y0), (x1, y1)
        if cur['band'] != b or cur['poly'] != pi or cur['pts'] is None or cur['pts'][-1] != start:
            cur = {'band': b, 'poly': pi, 'pts': [start, end]}
            runs[b].append(cur['pts'])
        else:
            cur['pts'].append(end)
    outdir = os.path.join(OUT, f'spectrum-{key}')
    os.makedirs(outdir, exist_ok=True)
    plan = []
    for b in range(bands):
        col = band_color(b, bands); hh = '%02x%02x%02x' % col
        dparts = ['M ' + ' L '.join(f'{x:.1f},{y:.1f}' for (x, y) in pts) for pts in runs[b]]
        svg = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {s['w']} {s['h']}'>"
               f"<path d=\"{' '.join(dparts)}\" fill='none' stroke='#{hh}' "
               f"stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/></svg>")
        open(os.path.join(outdir, f'pen-{b+1:02d}_{hh}.svg'), 'w').write(svg)
        plan.append(f'PEN {b+1:02d}  #{hh}  ({len(runs[b])} strokes)')
    open(os.path.join(outdir, 'PLOT_PLAN.txt'), 'w').write(
        f"SPECTRUM EDITION — {s['code']} {s['name']}\n"
        f"{bands}-pen layered plot · all layers share the suit's coordinate space.\n\n"
        f"Plot each layer in order, swapping to the matching pen between layers:\n\n"
        + '\n'.join(plan) +
        "\n\nLoad pen-NN.svg files into the AxiDraw app (or vpype/saxi) and plot in\n"
        "sequence. Registration is exact, so the bands align into one flowing path.\n"
        "Note: this is a stepped (banded) gradient — the honest limit of a pen.\n")
    print(f'  spectrum layers → {outdir}/ ({bands} pens + PLOT_PLAN.txt)')


if __name__ == '__main__':
    print('Mocking up new concepts → mockups/')
    concept_gradient('zaku')
    concept_gradient('zaku', dark=True)
    concept_blueprint('zaku')
    concept_macro('zaku')
    concept_roster()
    concept_statement('zaku')
    concept_spectrum('zaku', bands=8)
    export_spectrum_layers('zaku', bands=8)
    print('Done. Review in mockups/ and tell me which to keep.')
