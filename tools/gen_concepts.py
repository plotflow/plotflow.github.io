#!/usr/bin/env python3
"""
gen_concepts.py — mock up NEW post/reel design directions for review.

Renders to  mockups/  so you can thumbs-up/down before any of these graduate
into tools/gen_posts.py. Run from the repo root:  python tools/gen_concepts.py

Concepts:
  A  gradient   — the path colored start→end to *prove* it's one continuous line
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
    d.text((lx, ly-26*SS), 'ONE CONTINUOUS LINE', font=F(BOLD, 13*SS), fill=fg)
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
    d.text((60*SS, C-70*SS), f"CONTINUOUS PATH · {sum(len(x) for x in sp):,} VERTICES · 11×14″", font=F(REG, 12*SS), fill=CYAN+(160,))
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
    d.text((60*SS, C-44*SS), 'DETAIL · ONE CONTINUOUS LINE', font=F(REG, 11*SS), fill=DIM)
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


if __name__ == '__main__':
    print('Mocking up new concepts → mockups/')
    concept_gradient('zaku')
    concept_gradient('zaku', dark=True)
    concept_blueprint('zaku')
    concept_macro('zaku')
    concept_roster()
    concept_statement('zaku')
    print('Done. Review in mockups/ and tell me which to keep.')
