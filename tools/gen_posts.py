import json, math, os, re, textwrap
from PIL import Image, ImageDraw, ImageFont

src = open('data/editions.js').read()
src = src[src.index('{'):src.rindex('}')+1]
DATA = json.loads(src)
SUITS = DATA['suits']
ORDER = DATA.get('plotterOrder', list(SUITS.keys()))

S = 1080; SS = 3; C = S * SS
INK  = (21, 22, 15)
RED  = (232, 53, 31)
PAPER = (246, 243, 236)
MUTE = (195, 197, 184)
DIM  = (143, 145, 132)
CON2 = (67, 70, 62)
WHITE = (255, 255, 255)

BOLD = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
REG  = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
JP   = '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf'

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

def seg_lengths(subpaths):
    segs = []; total = 0.0
    for sp in subpaths:
        for i in range(len(sp)-1):
            x0,y0 = sp[i]; x1,y1 = sp[i+1]
            L = math.hypot(x1-x0, y1-y0)
            segs.append((x0,y0,x1,y1,total,L))
            total += L
    return segs, total

def bbox(sp):
    xs = [p[0] for s in sp for p in s]
    ys = [p[1] for s in sp for p in s]
    return min(xs), min(ys), max(xs), max(ys)

def draw_suit_partial(d, subpaths, bb, region, color, width, frac=1.0):
    """Draw suit up to frac (0-1) of total length. Returns last point drawn."""
    minx, miny, maxx, maxy = bb
    pad = max(maxx-minx, maxy-miny) * 0.06
    vbx, vby = minx-pad, miny-pad
    vbw, vbh = (maxx-minx)+2*pad, (maxy-miny)+2*pad
    rx, ry, rw, rh = region
    sc = min(rw/vbw, rh/vbh)
    ox = rx + (rw - vbw*sc)/2
    oy = ry + (rh - vbh*sc)/2
    segs, total = seg_lengths(subpaths)
    target = total * frac
    pen = None
    for (x0,y0,x1,y1,cs,L) in segs:
        if cs >= target: break
        if cs+L <= target:
            d.line([(ox+(x0-vbx)*sc, oy+(y0-vby)*sc),
                    (ox+(x1-vbx)*sc, oy+(y1-vby)*sc)], fill=color, width=width)
            pen = (ox+(x1-vbx)*sc, oy+(y1-vby)*sc)
        else:
            f = (target-cs)/L
            xe = x0+(x1-x0)*f; ye = y0+(y1-y0)*f
            d.line([(ox+(x0-vbx)*sc, oy+(y0-vby)*sc),
                    (ox+(xe-vbx)*sc, oy+(ye-vby)*sc)], fill=color, width=width)
            pen = (ox+(xe-vbx)*sc, oy+(ye-vby)*sc)
            break
    return pen, total

def draw_suit(d, subpaths, bb, region, color, width):
    draw_suit_partial(d, subpaths, bb, region, color, width, 1.0)

def reg_marks(d, m, sz, color):
    w = 2*SS
    for cx,cy in [(m,m),(C-m,m),(m,C-m),(C-m,C-m)]:
        d.line([cx-sz,cy,cx+sz,cy], fill=color, width=w)
        d.line([cx,cy-sz,cx,cy+sz], fill=color, width=w)

def wrap(d, text, font, max_w):
    words = text.split(); lines = []; line = ''
    for w in words:
        test = line + (' ' if line else '') + w
        if d.textlength(test, font=font) > max_w:
            if line: lines.append(line)
            line = w
        else: line = test
    if line: lines.append(line)
    return lines

# ============================================================
# TYPE 1: PROCESS — mid-plot freeze frame with pen crosshair
# ============================================================
def post_process(key, frac=0.55):
    s = SUITS[key]
    sp = parse_path(s['d']); bb = bbox(sp)

    img = Image.new('RGB', (C,C), PAPER)
    d = ImageDraw.Draw(img, 'RGBA')

    region = (80*SS, 80*SS, 920*SS, 750*SS)
    pen, total = draw_suit_partial(d, sp, bb, region, RED, max(2,2*SS), frac)

    # pen crosshair
    if pen:
        px, py = pen; r = 20*SS
        d.ellipse([px-r,py-r,px+r,py+r], outline=RED+(100,), width=max(2,2*SS))
        d.line([px-r*2,py,px+r*2,py], fill=RED+(80,), width=max(1,SS))
        d.line([px,py-r*2,px,py+r*2], fill=RED+(80,), width=max(1,SS))

    # progress readout — bottom
    mm = 420 / max(bb[2]-bb[0], bb[3]-bb[1])
    ink_m = (total*frac*mm)/1000; ink_total = (total*mm)/1000
    pct = round(frac*100)

    f_big = ImageFont.truetype(BOLD, 72*SS)
    f_label = ImageFont.truetype(REG, 12*SS)
    f_val = ImageFont.truetype(BOLD, 16*SS)
    f_brand = ImageFont.truetype(BOLD, 12*SS)

    # big percentage
    d.text((80*SS, C-280*SS), f'{pct}%', font=f_big, fill=INK+(40,))

    # stats row
    by = C - 130*SS
    cols = [
        ('PLOTTING', f'{s["code"]} {s["name"]}'),
        ('INK', f'{ink_m:.1f} / {ink_total:.1f}m'),
        ('STATUS', 'IN PROGRESS'),
    ]
    x = 80*SS
    for label, val in cols:
        d.text((x, by), label, font=f_label, fill=DIM)
        d.text((x, by+18*SS), val, font=f_val, fill=INK+(200,))
        x += 280*SS

    # brand
    bw = d.textlength('PLOTFLOW*', font=f_brand)
    d.text((C-80*SS-bw, C-80*SS), 'PLOTFLOW*', font=f_brand, fill=INK+(80,))

    out = img.resize((S,S), Image.LANCZOS)
    path = f'/tmp/post-{key}-process.png'
    out.save(path, 'PNG'); print(f'  {path}'); return path

# ============================================================
# TYPE 2: DROP ANNOUNCEMENT — bold type, edition number hero
# ============================================================
def post_drop(key):
    s = SUITS[key]
    sp = parse_path(s['d']); bb = bbox(sp)

    img = Image.new('RGB', (C,C), INK)
    d = ImageDraw.Draw(img, 'RGBA')

    # suit ghosted large
    draw_suit(d, sp, bb, (100*SS, 100*SS, 880*SS, 700*SS), RED+(60,), max(2,2*SS))

    # "NOW AVAILABLE" top
    f_tag = ImageFont.truetype(BOLD, 14*SS)
    d.text((80*SS, 60*SS), 'NOW AVAILABLE', font=f_tag, fill=RED)
    # red line under tag
    tw = d.textlength('NOW AVAILABLE', font=f_tag)
    d.rectangle([80*SS, 86*SS, 80*SS+tw, 88*SS], fill=RED)

    # edition number — MASSIVE
    ed_raw = s.get('edition','ED. 01/25').split('·')[0].strip()
    f_ed = ImageFont.truetype(BOLD, 140*SS)
    d.text((80*SS, C-520*SS), ed_raw, font=f_ed, fill=WHITE+(30,))

    # suit name large
    f_name = ImageFont.truetype(BOLD, 48*SS)
    f_jp = ImageFont.truetype(JP, 32*SS)
    d.text((80*SS, C-320*SS), s['name'], font=f_name, fill=PAPER)
    nw = d.textlength(s['name'], font=f_name)
    d.text((80*SS+nw+20*SS, C-310*SS), s.get('jp',''), font=f_jp, fill=DIM)

    # code
    f_code = ImageFont.truetype(REG, 18*SS)
    d.text((80*SS, C-260*SS), s['code'], font=f_code, fill=MUTE)

    # specs line
    f_spec = ImageFont.truetype(REG, 13*SS)
    d.text((80*SS, C-220*SS), 'Staedtler 0.3mm on Strathmore Bristol · 11×14″ · Signed & numbered', font=f_spec, fill=DIM)

    # price + CTA
    f_price = ImageFont.truetype(BOLD, 36*SS)
    d.text((80*SS, C-160*SS), s.get('price','$45'), font=f_price, fill=RED)
    f_cta = ImageFont.truetype(BOLD, 16*SS)
    d.text((80*SS, C-108*SS), 'plotflow.io', font=f_cta, fill=MUTE)

    # brand top-right
    f_brand = ImageFont.truetype(BOLD, 14*SS)
    bw = d.textlength('PLOTFLOW*', font=f_brand)
    d.text((C-80*SS-bw, 60*SS), 'PLOTFLOW*', font=f_brand, fill=MUTE+(140,))

    out = img.resize((S,S), Image.LANCZOS)
    path = f'/tmp/post-{key}-drop.png'
    out.save(path, 'PNG'); print(f'  {path}'); return path

# ============================================================
# TYPE 3: LORE CARD — text-forward, suit ghosted
# ============================================================
def post_lore(key):
    s = SUITS[key]
    sp = parse_path(s['d']); bb = bbox(sp)

    img = Image.new('RGB', (C,C), PAPER)
    d = ImageDraw.Draw(img, 'RGBA')

    # suit ghosted behind text
    draw_suit(d, sp, bb, (250*SS, 50*SS, 750*SS, 750*SS), INK+(22,), max(2,2*SS))

    # red accent bar left
    d.rectangle([60*SS, 60*SS, 66*SS, C-60*SS], fill=RED)

    # model code top
    f_code = ImageFont.truetype(BOLD, 54*SS)
    d.text((90*SS, 60*SS), s['code'], font=f_code, fill=INK)

    # name + jp
    f_name = ImageFont.truetype(BOLD, 28*SS)
    f_jp = ImageFont.truetype(JP, 24*SS)
    d.text((90*SS, 130*SS), s['name'], font=f_name, fill=INK+(200,))
    nw = d.textlength(s['name'], font=f_name)
    d.text((90*SS+nw+16*SS, 134*SS), s.get('jp',''), font=f_jp, fill=DIM)

    # lore text — large, readable
    f_lore = ImageFont.truetype(REG, 18*SS)
    lore = s.get('lore', '')
    lines = wrap(d, lore, f_lore, 620*SS)
    y = 200*SS
    for ln in lines[:7]:
        d.text((90*SS, y), ln, font=f_lore, fill=INK+(180,))
        y += 32*SS

    # divider
    y += 16*SS
    d.rectangle([90*SS, y, 400*SS, y+2*SS], fill=INK+(40,))
    y += 20*SS

    # specs compact
    f_spec = ImageFont.truetype(BOLD, 13*SS)
    f_label = ImageFont.truetype(REG, 10*SS)
    for label, val in [('EDITION', s.get('edition','')), ('MEDIUM', 'Pigment ink on Bristol, 11×14″'), ('MADE BY', 'AxiDraw pen plotter')]:
        d.text((90*SS, y), label, font=f_label, fill=DIM)
        d.text((200*SS, y), val, font=f_spec, fill=INK+(160,))
        y += 22*SS

    # price
    f_price = ImageFont.truetype(BOLD, 28*SS)
    d.text((90*SS, C-110*SS), s.get('price','$45'), font=f_price, fill=RED)

    # brand bottom-right
    f_brand = ImageFont.truetype(BOLD, 16*SS)
    bw = d.textlength('PLOTFLOW*', font=f_brand)
    d.text((C-80*SS-bw, C-100*SS), 'PLOTFLOW*', font=f_brand, fill=INK+(70,))

    out = img.resize((S,S), Image.LANCZOS)
    path = f'/tmp/post-{key}-lore.png'
    out.save(path, 'PNG'); print(f'  {path}'); return path

# ============================================================
# TYPE 4: SPEC SHEET — dense technical readout, editorial energy
# ============================================================
def post_spec(key):
    s = SUITS[key]
    sp = parse_path(s['d']); bb = bbox(sp)
    segs, total = seg_lengths(sp)
    mm = 420 / max(bb[2]-bb[0], bb[3]-bb[1])
    ink_m = (total*mm)/1000
    plot_min = (total*mm)/1100

    img = Image.new('RGB', (C,C), INK)
    d = ImageDraw.Draw(img, 'RGBA')

    reg_marks(d, 50*SS, 20*SS, PAPER+(30,))

    # suit — right/center
    draw_suit(d, sp, bb, (280*SS, 100*SS, 700*SS, 620*SS), RED+(200,), max(2,2*SS))

    # big ghosted code
    f_ghost = ImageFont.truetype(BOLD, 160*SS)
    d.text((40*SS, 20*SS), s['code'].split('-')[-1] if '-' in s['code'] else s['code'], font=f_ghost, fill=PAPER+(18,))

    # header bar
    d.rectangle([50*SS, 58*SS, C-50*SS, 60*SS], fill=RED+(80,))

    # PLOTFLOW* + type line
    f_brand = ImageFont.truetype(BOLD, 16*SS)
    f_tiny = ImageFont.truetype(REG, 10*SS)
    d.text((50*SS, 36*SS), 'PLOTFLOW*', font=f_brand, fill=RED)
    d.text((210*SS, 42*SS), 'TECHNICAL READOUT', font=f_tiny, fill=DIM)

    # right side: マシンドロー
    f_jp_sm = ImageFont.truetype(JP, 12*SS)
    jw = d.textlength('マシンドロー', font=f_jp_sm)
    d.text((C-50*SS-jw, 40*SS), 'マシンドロー', font=f_jp_sm, fill=DIM)

    # ---- bottom data panel ----
    panel_y = C - 380*SS
    d.rectangle([50*SS, panel_y, C-50*SS, panel_y+2*SS], fill=PAPER+(30,))
    panel_y += 20*SS

    f_label = ImageFont.truetype(REG, 10*SS)
    f_val = ImageFont.truetype(BOLD, 16*SS)
    f_val_lg = ImageFont.truetype(BOLD, 36*SS)
    f_name = ImageFont.truetype(BOLD, 28*SS)
    f_jp = ImageFont.truetype(JP, 20*SS)
    f_lore_sm = ImageFont.truetype(REG, 12*SS)

    # suit name row
    d.text((60*SS, panel_y), s['name'].upper(), font=f_name, fill=PAPER)
    nw = d.textlength(s['name'].upper(), font=f_name)
    d.text((60*SS+nw+16*SS, panel_y+6*SS), s.get('jp',''), font=f_jp, fill=DIM)
    d.text((60*SS, panel_y+40*SS), s['code'], font=f_label, fill=MUTE)
    panel_y += 70*SS

    # data grid — 4 columns
    col_w = (C - 120*SS) // 4
    data = [
        ('EDITION', s.get('edition','').split('·')[0].strip()),
        ('INK', f'{ink_m:.1f}m'),
        ('PLOT TIME', f'{int(plot_min)}min'),
        ('PRICE', s.get('price','$45')),
    ]
    for i, (label, val) in enumerate(data):
        x = 60*SS + i*col_w
        d.text((x, panel_y), label, font=f_label, fill=DIM)
        d.text((x, panel_y+18*SS), val, font=f_val, fill=PAPER)
    panel_y += 60*SS

    # divider
    d.rectangle([60*SS, panel_y, C-60*SS, panel_y+SS], fill=PAPER+(20,))
    panel_y += 16*SS

    # material specs
    specs = [
        ('PAPER', 'Strathmore 300 Series Bristol, smooth'),
        ('PEN', 'Staedtler Triplus 0.3mm, pigment-based'),
        ('PLOTTER', 'AxiDraw V3, continuous line path'),
        ('FINISH', 'Inspected, signed, numbered by hand'),
    ]
    for label, val in specs:
        d.text((60*SS, panel_y), label, font=f_label, fill=DIM)
        d.text((160*SS, panel_y), val, font=f_lore_sm, fill=MUTE)
        panel_y += 20*SS

    # bottom strip
    d.rectangle([0, C-36*SS, C, C], fill=RED)
    f_strip = ImageFont.truetype(BOLD, 10*SS)
    strip = 'PLOTFLOW*  ·  マシンドロー  ·  DRAWN BY MACHINE  ·  EST. 2026  ·  PLOTTED IN THE U.S.A.'
    sw = d.textlength(strip, font=f_strip)
    d.text((C/2-sw/2, C-28*SS), strip, font=f_strip, fill=WHITE)

    out = img.resize((S,S), Image.LANCZOS)
    path = f'/tmp/post-{key}-spec.png'
    out.save(path, 'PNG'); print(f'  {path}'); return path

# ============================================================
# TYPE 5: BRAND/PHILOSOPHY — no suit, pure typography
# ============================================================
def post_brand(variant='dark'):
    bg = INK if variant=='dark' else PAPER
    fg = PAPER if variant=='dark' else INK
    accent = RED

    img = Image.new('RGB', (C,C), bg)
    d = ImageDraw.Draw(img, 'RGBA')

    reg_marks(d, 50*SS, 20*SS, fg+(25,))

    f_huge = ImageFont.truetype(BOLD, 80*SS)
    f_sub = ImageFont.truetype(REG, 18*SS)
    f_jp_big = ImageFont.truetype(JP, 48*SS)
    f_body = ImageFont.truetype(REG, 16*SS)
    f_tiny = ImageFont.truetype(REG, 11*SS)
    f_brand = ImageFont.truetype(BOLD, 14*SS)

    # PLOTFLOW*
    d.text((80*SS, 120*SS), 'PLOT', font=f_huge, fill=fg)
    d.text((80*SS, 210*SS), 'FLOW*', font=f_huge, fill=accent)

    # tagline
    d.text((80*SS, 320*SS), 'independent pen-plotter studio', font=f_sub, fill=fg+(140,) if variant=='dark' else fg+(120,))

    # jp
    d.text((80*SS, 430*SS), 'マシンドロー', font=f_jp_big, fill=fg+(80,) if variant=='dark' else fg+(60,))

    # body text
    body = "Universal-Century mobile suits, rebuilt as continuous vector paths and traced in pigment ink on archival paper by an AxiDraw plotter. Nothing is printed. Every impression is drawn."
    lines = wrap(d, body, f_body, 700*SS)
    y = 560*SS
    for ln in lines:
        d.text((80*SS, y), ln, font=f_body, fill=fg+(160,) if variant=='dark' else fg+(140,))
        y += 30*SS

    # bottom details
    by = C - 160*SS
    d.rectangle([80*SS, by, 400*SS, by+2*SS], fill=accent+(80,))
    by += 20*SS
    details = [
        'Limited editions of 25 · Signed and numbered',
        'Staedtler pigment ink on Strathmore Bristol',
        'Made to order · Plotted in the U.S.A.',
    ]
    for line in details:
        d.text((80*SS, by), line, font=f_tiny, fill=fg+(120,) if variant=='dark' else fg+(100,))
        by += 20*SS

    # asterisk decorative
    f_ast = ImageFont.truetype(BOLD, 200*SS)
    d.text((C-320*SS, C-420*SS), '*', font=f_ast, fill=accent+(30,))

    # est
    d.text((80*SS, C-60*SS), 'est. 2026', font=f_tiny, fill=fg+(60,))
    bw = d.textlength('plotflow.io', font=f_brand)
    d.text((C-80*SS-bw, C-60*SS), 'plotflow.io', font=f_brand, fill=accent+(160,))

    out = img.resize((S,S), Image.LANCZOS)
    path = f'/tmp/post-brand-{variant}.png'
    out.save(path, 'PNG'); print(f'  {path}'); return path


# ============================================================
# GENERATE ALL
# ============================================================
print('=== Process (mid-plot) ===')
for k in ORDER: post_process(k, frac=0.55)

print('\n=== Drop Announcements ===')
for k in ORDER: post_drop(k)

print('\n=== Lore Cards ===')
for k in ORDER: post_lore(k)

print('\n=== Spec Sheets ===')
for k in ORDER: post_spec(k)

print('\n=== Brand Cards ===')
post_brand('dark')
post_brand('light')

print('\nDone!')
