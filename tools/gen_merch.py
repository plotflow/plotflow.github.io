import json, math, os, re
from PIL import Image, ImageDraw, ImageFont

src = open('data/editions.js').read()
src = src[src.index('{'):src.rindex('}')+1]
DATA = json.loads(src)
SUITS = DATA['suits']
ORDER = DATA.get('plotterOrder', list(SUITS.keys()))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'mockups', 'merch')
os.makedirs(OUT, exist_ok=True)

INK   = (21, 22, 15)
RED   = (232, 53, 31)
PAPER = (246, 243, 236)
MUTE  = (195, 197, 184)
DIM   = (143, 145, 132)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

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


def plot_minutes(sp, total_draw, mm):
    """Plot time = draw + pen-up travel + lift cycles (tuned to PlotGrid actuals),
    not just ink-length / feed."""
    travel = 0.0
    for a, b in zip(sp, sp[1:]):
        travel += math.hypot(b[0][0]-a[-1][0], b[0][1]-a[-1][1])
    lifts = max(0, len(sp)-1)
    return (total_draw*mm)/1100 + (travel*mm)/6600 + lifts*0.10/60

def bbox(sp):
    xs = [p[0] for s in sp for p in s]
    ys = [p[1] for s in sp for p in s]
    return min(xs), min(ys), max(xs), max(ys)

def draw_suit(d, subpaths, bb, region, color, width):
    minx, miny, maxx, maxy = bb
    pad = max(maxx-minx, maxy-miny) * 0.06
    vbx, vby = minx-pad, miny-pad
    vbw, vbh = (maxx-minx)+2*pad, (maxy-miny)+2*pad
    rx, ry, rw, rh = region
    sc = min(rw/vbw, rh/vbh)
    ox = rx + (rw - vbw*sc)/2
    oy = ry + (rh - vbh*sc)/2
    for sp in subpaths:
        for i in range(len(sp)-1):
            x0,y0 = sp[i]; x1,y1 = sp[i+1]
            d.line([(ox+(x0-vbx)*sc, oy+(y0-vby)*sc),
                    (ox+(x1-vbx)*sc, oy+(y1-vby)*sc)], fill=color, width=width)

def draw_asterisk(d, cx, cy, r, color, width):
    for angle in [0, 45, 90, 135]:
        rad = math.radians(angle)
        dx, dy = r * math.cos(rad), r * math.sin(rad)
        d.line([cx-dx, cy-dy, cx+dx, cy+dy], fill=color, width=width)


# ============================================================
# TEE 1: BACK PRINT: full suit, centered, code below
# Output: 4500×5400 (print-ready ~15×18″ @ 300dpi)
# ============================================================
def tee_back(key, variant='black'):
    s = SUITS[key]
    sp = parse_path(s['d']); bb = bbox(sp)
    SS = 3
    W, H = 4500, 5400
    is_dark = variant == 'black'
    bg = BLACK if is_dark else WHITE
    line_color = RED if is_dark else RED
    text_color = WHITE if is_dark else BLACK

    img = Image.new('RGB', (W, H), bg)
    d = ImageDraw.Draw(img, 'RGBA')

    # suit centered, large
    margin = 200
    suit_h = int(H * 0.72)
    draw_suit(d, sp, bb, (margin, 100, W - 2*margin, suit_h), line_color, 6)

    # code + name below suit
    f_code = ImageFont.truetype(BOLD, 72)
    f_name = ImageFont.truetype(BOLD, 48)
    f_jp = ImageFont.truetype(JP, 40)
    f_brand = ImageFont.truetype(BOLD, 36)

    text_y = suit_h + 200
    code_text = s['code']
    cw = d.textlength(code_text, font=f_code)
    d.text((W/2 - cw/2, text_y), code_text, font=f_code, fill=text_color)

    text_y += 90
    name_text = s['name'].upper()
    nw = d.textlength(name_text, font=f_name)
    d.text((W/2 - nw/2, text_y), name_text, font=f_name, fill=text_color + (180,))

    text_y += 70
    jp_text = s.get('jp', '')
    jw = d.textlength(jp_text, font=f_jp)
    d.text((W/2 - jw/2, text_y), jp_text, font=f_jp, fill=text_color + (100,))

    # PLOTFLOW* at bottom
    text_y += 100
    brand = 'PLOTFLOW*'
    bw = d.textlength(brand, font=f_brand)
    d.text((W/2 - bw/2, text_y), brand, font=f_brand, fill=RED + (160,))

    path = f'{OUT}/merch-{key}-tee-back-{variant}.png'
    img.save(path, 'PNG'); print(f'  {path}'); return path


# ============================================================
# TEE 2: FRONT: small chest logo (asterisk + PLOTFLOW*)
# ============================================================
def tee_front(variant='black'):
    SS = 3
    W, H = 4500, 5400
    is_dark = variant == 'black'
    bg = BLACK if is_dark else WHITE
    text_color = WHITE if is_dark else BLACK

    img = Image.new('RGB', (W, H), bg)
    d = ImageDraw.Draw(img, 'RGBA')

    # chest placement: upper-left area
    cx, cy = 1400, 1200

    # asterisk
    draw_asterisk(d, cx, cy, 80, RED, 14)

    # PLOTFLOW* text below asterisk
    f_brand = ImageFont.truetype(BOLD, 42)
    bw = d.textlength('PLOTFLOW*', font=f_brand)
    d.text((cx - bw/2, cy + 110), 'PLOTFLOW*', font=f_brand, fill=text_color)

    # マシンドロー small below
    f_jp = ImageFont.truetype(JP, 28)
    jt = 'マシンドロー'
    jw = d.textlength(jt, font=f_jp)
    d.text((cx - jw/2, cy + 168), jt, font=f_jp, fill=text_color + (80,))

    path = f'{OUT}/merch-tee-front-{variant}.png'
    img.save(path, 'PNG'); print(f'  {path}'); return path


# ============================================================
# TEE 3: LINEUP: all 6 suits in a grid (2×3), back print
# ============================================================
def tee_lineup(variant='black'):
    W, H = 4500, 5400
    is_dark = variant == 'black'
    bg = BLACK if is_dark else WHITE
    line_color = RED
    text_color = WHITE if is_dark else BLACK

    img = Image.new('RGB', (W, H), bg)
    d = ImageDraw.Draw(img, 'RGBA')

    # header
    f_brand = ImageFont.truetype(BOLD, 48)
    f_sub = ImageFont.truetype(REG, 28)
    bw = d.textlength('PLOTFLOW*', font=f_brand)
    d.text((W/2 - bw/2, 120), 'PLOTFLOW*', font=f_brand, fill=RED)
    sub = 'SEASON 01 · UNIVERSAL CENTURY'
    sw = d.textlength(sub, font=f_sub)
    d.text((W/2 - sw/2, 190), sub, font=f_sub, fill=text_color + (120,))

    # 2 columns × 3 rows
    cols, rows = 2, 3
    cell_w = (W - 400) // cols
    cell_h = (H - 800) // rows
    start_x, start_y = 200, 340
    f_code = ImageFont.truetype(BOLD, 24)

    for idx, key in enumerate(ORDER[:6]):
        s = SUITS[key]
        sp = parse_path(s['d']); bb = bbox(sp)
        col = idx % cols
        row = idx // cols
        cx = start_x + col * cell_w
        cy = start_y + row * cell_h
        draw_suit(d, sp, bb, (cx + 40, cy + 20, cell_w - 80, cell_h - 80), line_color + (200,), 4)
        # code label centered under each
        ct = s['code']
        ctw = d.textlength(ct, font=f_code)
        d.text((cx + cell_w/2 - ctw/2, cy + cell_h - 50), ct, font=f_code, fill=text_color + (140,))

    # footer: JP in the JP font (Latin fonts render it as tofu), Latin below
    f_foot = ImageFont.truetype(REG, 24)
    f_foot_jp = ImageFont.truetype(JP, 24)
    jt = 'マシンドロー'
    jw = d.textlength(jt, font=f_foot_jp)
    d.text((W/2 - jw/2, H - 180), jt, font=f_foot_jp, fill=text_color + (80,))
    foot = 'DRAWN BY MACHINE · EST. 2026'
    fw = d.textlength(foot, font=f_foot)
    d.text((W/2 - fw/2, H - 130), foot, font=f_foot, fill=text_color + (80,))

    path = f'{OUT}/merch-tee-lineup-{variant}.png'
    img.save(path, 'PNG'); print(f'  {path}'); return path


# ============================================================
# POSTER: 18×24″ @ 300dpi (5400×7200), dark technical readout
# ============================================================
def poster(key):
    s = SUITS[key]
    sp = parse_path(s['d']); bb = bbox(sp)
    segs, total = seg_lengths(sp)
    npts = sum(len(x) for x in sp)   # vertices along the continuous path
    mm = 420 / max(bb[2]-bb[0], bb[3]-bb[1])
    ink_m = (total*mm)/1000
    plot_min = int(plot_minutes(sp, total, mm))

    W, H = 5400, 7200
    img = Image.new('RGB', (W, H), INK)
    d = ImageDraw.Draw(img, 'RGBA')

    # thin border
    d.rectangle([60, 60, W-60, H-60], outline=RED + (40,), width=3)

    # header
    f_brand = ImageFont.truetype(BOLD, 48)
    f_tiny = ImageFont.truetype(REG, 28)
    d.text((140, 120), 'PLOTFLOW*', font=f_brand, fill=RED)
    d.text((560, 132), 'TECHNICAL READOUT', font=f_tiny, fill=DIM)
    f_jp_sm = ImageFont.truetype(JP, 32)
    jt = 'マシンドロー'
    jw = d.textlength(jt, font=f_jp_sm)
    d.text((W - 140 - jw, 126), jt, font=f_jp_sm, fill=DIM)

    # red line
    d.rectangle([140, 190, W-140, 194], fill=RED + (80,))

    # suit: hero, centered
    suit_margin = 300
    suit_top = 280
    suit_h = int(H * 0.62)
    draw_suit(d, sp, bb, (suit_margin, suit_top, W - 2*suit_margin, suit_h), RED, 8)

    # ghosted model code behind suit
    f_ghost = ImageFont.truetype(BOLD, 500)
    gc = s['code'].split('-')[-1] if '-' in s['code'] else s['code']
    gw = d.textlength(gc, font=f_ghost)
    d.text((W/2 - gw/2, 600), gc, font=f_ghost, fill=PAPER + (12,))

    # ---- data panel below suit ----
    panel_y = suit_top + suit_h + 100
    d.rectangle([140, panel_y, W-140, panel_y + 4], fill=PAPER + (30,))
    panel_y += 40

    f_name_lg = ImageFont.truetype(BOLD, 80)
    f_jp_lg = ImageFont.truetype(JP, 56)
    f_code = ImageFont.truetype(REG, 32)
    f_label = ImageFont.truetype(REG, 24)
    f_val = ImageFont.truetype(BOLD, 40)
    f_lore = ImageFont.truetype(REG, 28)

    # name
    d.text((160, panel_y), s['name'].upper(), font=f_name_lg, fill=PAPER)
    nw = d.textlength(s['name'].upper(), font=f_name_lg)
    d.text((160 + nw + 30, panel_y + 20), s.get('jp', ''), font=f_jp_lg, fill=DIM)
    panel_y += 100
    d.text((160, panel_y), s['code'], font=f_code, fill=MUTE)
    panel_y += 60

    # data row
    col_w = (W - 320) // 4
    data_items = [
        ('EDITION', s.get('edition','').split('·')[0].strip()),
        ('INK', f'{ink_m:.1f}m total'),
        ('PLOT TIME', f'{plot_min} min'),
        ('VERTICES', f'{npts:,}'),
    ]
    for i, (label, val) in enumerate(data_items):
        x = 160 + i * col_w
        d.text((x, panel_y), label, font=f_label, fill=DIM)
        d.text((x, panel_y + 36), val, font=f_val, fill=PAPER)
    panel_y += 110

    d.rectangle([160, panel_y, W-160, panel_y + 2], fill=PAPER + (20,))
    panel_y += 30

    # lore
    lore = s.get('lore', '')
    words = lore.split(); lines = []; line = ''
    for w in words:
        test = line + (' ' if line else '') + w
        if d.textlength(test, font=f_lore) > W - 360:
            if line: lines.append(line)
            line = w
        else: line = test
    if line: lines.append(line)
    for ln in lines[:4]:
        d.text((160, panel_y), ln, font=f_lore, fill=MUTE)
        panel_y += 42

    panel_y += 20
    specs_text = 'Staedtler 0.3mm pigment ink  ·  Strathmore Bristol 11×14″  ·  AxiDraw V3  ·  Signed & numbered'
    d.text((160, panel_y), specs_text, font=f_label, fill=DIM)

    # bottom red strip
    d.rectangle([0, H-60, W, H], fill=RED)
    f_strip = ImageFont.truetype(BOLD, 24)
    strip = 'PLOTFLOW*  ·  DRAWN BY MACHINE  ·  EST. 2026  ·  PLOTTED IN THE U.S.A.'
    sw = d.textlength(strip, font=f_strip)
    d.text((W/2 - sw/2, H - 48), strip, font=f_strip, fill=WHITE)

    path = f'{OUT}/merch-{key}-poster.png'
    img.save(path, 'PNG'); print(f'  {path}'); return path


# ============================================================
# STICKER: die-cut style, suit on transparent (saved as white bg for preview)
# 1500×1500 (5″ @ 300dpi)
# ============================================================
def sticker(key):
    s = SUITS[key]
    sp = parse_path(s['d']); bb = bbox(sp)

    SZ = 1500
    img = Image.new('RGBA', (SZ, SZ), (255, 255, 255, 0))
    d = ImageDraw.Draw(img, 'RGBA')

    # circle background
    pad = 60
    d.ellipse([pad, pad, SZ-pad, SZ-pad], fill=INK + (255,))

    # suit inside circle
    draw_suit(d, sp, bb, (pad + 80, pad + 60, SZ - 2*(pad+80), SZ - 2*(pad+80) - 120), RED + (230,), 3)

    # PLOTFLOW* at bottom of circle
    f_brand = ImageFont.truetype(BOLD, 32)
    bw = d.textlength('PLOTFLOW*', font=f_brand)
    d.text((SZ/2 - bw/2, SZ - pad - 120), 'PLOTFLOW*', font=f_brand, fill=RED + (200,))

    # code
    f_code = ImageFont.truetype(BOLD, 22)
    ct = s['code']
    cw = d.textlength(ct, font=f_code)
    d.text((SZ/2 - cw/2, SZ - pad - 80), ct, font=f_code, fill=MUTE + (180,))

    path = f'{OUT}/merch-{key}-sticker.png'
    img.save(path, 'PNG'); print(f'  {path}'); return path


# ============================================================
# TOTE BAG: minimal, vertical format (3000×3600)
# ============================================================
def tote(key, variant='natural'):
    s = SUITS[key]
    sp = parse_path(s['d']); bb = bbox(sp)

    W, H = 3000, 3600
    is_dark = variant == 'black'
    bg = BLACK if is_dark else (240, 235, 220)  # natural canvas color
    line_color = RED if is_dark else INK
    text_color = WHITE if is_dark else INK

    img = Image.new('RGB', (W, H), bg)
    d = ImageDraw.Draw(img, 'RGBA')

    # suit centered
    draw_suit(d, sp, bb, (200, 100, W - 400, H - 700), line_color, 5)

    # name + brand at bottom
    f_name = ImageFont.truetype(BOLD, 56)
    f_brand = ImageFont.truetype(BOLD, 36)
    f_jp = ImageFont.truetype(JP, 40)

    name_text = s['name'].upper()
    nw = d.textlength(name_text, font=f_name)
    bottom_y = H - 400
    d.text((W/2 - nw/2, bottom_y), name_text, font=f_name, fill=text_color)

    jp_text = s.get('jp', '')
    jw = d.textlength(jp_text, font=f_jp)
    d.text((W/2 - jw/2, bottom_y + 80), jp_text, font=f_jp, fill=text_color + (100,))

    brand = 'PLOTFLOW*'
    bw = d.textlength(brand, font=f_brand)
    d.text((W/2 - bw/2, bottom_y + 160), brand, font=f_brand, fill=RED + (180,))

    path = f'{OUT}/merch-{key}-tote-{variant}.png'
    img.save(path, 'PNG'); print(f'  {path}'); return path


# ============================================================
# MUG WRAP: panoramic band (3600×1200)
# ============================================================
def mug_wrap():
    W, H = 3600, 1200
    img = Image.new('RGB', (W, H), INK)
    d = ImageDraw.Draw(img, 'RGBA')

    # place all 6 suits side by side
    suit_w = W // 6
    for idx, key in enumerate(ORDER[:6]):
        s = SUITS[key]
        sp = parse_path(s['d']); bb = bbox(sp)
        x = idx * suit_w
        draw_suit(d, sp, bb, (x + 30, 40, suit_w - 60, H - 160), RED + (180,), 3)
        # code below each
        f_code = ImageFont.truetype(BOLD, 18)
        ct = s['code']
        cw = d.textlength(ct, font=f_code)
        d.text((x + suit_w/2 - cw/2, H - 100), ct, font=f_code, fill=DIM)

    # brand centered at very bottom: JP part in the JP font (avoids tofu)
    f_brand = ImageFont.truetype(BOLD, 22)
    f_brand_jp = ImageFont.truetype(JP, 22)
    latin, jt = 'PLOTFLOW*  ·  ', 'マシンドロー'
    lw = d.textlength(latin, font=f_brand)
    jw = d.textlength(jt, font=f_brand_jp)
    x0 = W/2 - (lw + jw)/2
    d.text((x0, H - 50), latin, font=f_brand, fill=RED + (140,))
    d.text((x0 + lw, H - 50), jt, font=f_brand_jp, fill=RED + (140,))

    path = f'{OUT}/merch-mug-wrap.png'
    img.save(path, 'PNG'); print(f'  {path}'); return path


# ============================================================
# ENAMEL PIN DESIGN: individual suit badge (800×800)
# ============================================================
def pin_design(key):
    s = SUITS[key]
    sp = parse_path(s['d']); bb = bbox(sp)

    SZ = 800
    img = Image.new('RGB', (SZ, SZ), INK)
    d = ImageDraw.Draw(img, 'RGBA')

    # hexagonal-ish border (approximated as rounded rect)
    d.rounded_rectangle([30, 30, SZ-30, SZ-30], radius=60, outline=RED, width=6)

    # suit
    draw_suit(d, sp, bb, (80, 50, SZ - 160, SZ - 200), RED, 3)

    # code at bottom
    f_code = ImageFont.truetype(BOLD, 28)
    ct = s['code']
    cw = d.textlength(ct, font=f_code)
    d.text((SZ/2 - cw/2, SZ - 100), ct, font=f_code, fill=MUTE)

    # asterisk mark
    draw_asterisk(d, SZ - 80, 80, 20, RED, 4)

    path = f'{OUT}/merch-{key}-pin.png'
    img.save(path, 'PNG'); print(f'  {path}'); return path


# ============================================================
# PRESENTATION MOCKUPS: the print composited onto a flat garment
# silhouette (brand-consistent flat style, honest: a mockup, not a photo)
# ============================================================

def _tee_polygon(cx, ty, w):
    """Classic tee outline (back view), width w = body width unit."""
    return [
        (cx-0.18*w, ty),              # left neck
        (cx-0.55*w, ty+0.05*w),       # left shoulder tip
        (cx-0.75*w, ty+0.40*w),       # left sleeve end (outer)
        (cx-0.53*w, ty+0.52*w),       # left sleeve cuff (inner)
        (cx-0.47*w, ty+0.40*w),       # left underarm
        (cx-0.47*w, ty+1.32*w),       # left hem
        (cx+0.47*w, ty+1.32*w),       # right hem
        (cx+0.47*w, ty+0.40*w),
        (cx+0.53*w, ty+0.52*w),
        (cx+0.75*w, ty+0.40*w),
        (cx+0.55*w, ty+0.05*w),
        (cx+0.18*w, ty),              # right neck
    ]

def present_tee(print_path, out_name, variant, label):
    """Composite a flat print file onto a tee silhouette, masked to the garment."""
    CV = 2160
    canvas = Image.new('RGB', (CV, CV), PAPER)
    d = ImageDraw.Draw(canvas, 'RGBA')

    cx, ty, w = CV/2, CV*0.16, CV*0.42
    poly = _tee_polygon(cx, ty, w)

    # exact match to the print file's bg so the panel is seamless on the garment
    tee_col = BLACK if variant == 'black' else WHITE
    edge_col = (0, 0, 0, 60) if variant != 'black' else (255, 255, 255, 36)

    # garment layer: tee color + the print placed on the body, then masked
    mask = Image.new('L', (CV, CV), 0)
    ImageDraw.Draw(mask).polygon(poly, fill=255)
    layer = Image.new('RGB', (CV, CV), tee_col)
    pr = Image.open(print_path)
    pw = int(w * 0.66); ph = int(pr.height * pw / pr.width)
    pr = pr.resize((pw, ph), Image.LANCZOS)
    layer.paste(pr, (int(cx - pw/2), int(ty + 0.30*w)))
    canvas.paste(layer, (0, 0), mask)

    # outline + back-collar hint
    d.line(poly + [poly[0]], fill=edge_col, width=3)
    d.arc([cx-0.18*w, ty-0.05*w, cx+0.18*w, ty+0.09*w], 0, 180, fill=edge_col, width=4)

    # caption strip
    f = ImageFont.truetype(BOLD, 34); f2 = ImageFont.truetype(REG, 24)
    d.text((90, CV-150), label, font=f, fill=INK)
    d.text((90, CV-100), f'{variant.upper()} TEE · SCREEN PRINT · MOCKUP', font=f2, fill=DIM)
    bw2 = d.textlength('PLOTFLOW*', font=f)
    d.text((CV-90-bw2, CV-150), 'PLOTFLOW*', font=f, fill=RED)

    path = f'{OUT}/mock-tee-{out_name}-{variant}.png'
    canvas.save(path, 'PNG'); print(f'  {path}'); return path

def present_tote(print_path, out_name, label):
    """Composite a tote print onto a flat tote-bag silhouette."""
    CV = 2160
    canvas = Image.new('RGB', (CV, CV), PAPER)
    d = ImageDraw.Draw(canvas, 'RGBA')

    bw_, bh = CV*0.46, CV*0.56
    bx, by = CV/2 - bw_/2, CV*0.26
    bag_col = (240, 235, 220)          # natural canvas: matches the tote print bg
    edge = (0, 0, 0, 70)

    # handles
    for hx in (bx + bw_*0.22, bx + bw_*0.78):
        d.line([(hx, by), (hx - (bw_*0.06 if hx < CV/2 else -bw_*0.06), by - bh*0.22)],
               fill=(60, 55, 45), width=26)
    # bag face + print masked to it
    mask = Image.new('L', (CV, CV), 0)
    ImageDraw.Draw(mask).rounded_rectangle([bx, by, bx+bw_, by+bh], radius=18, fill=255)
    layer = Image.new('RGB', (CV, CV), bag_col)
    pr = Image.open(print_path)
    pw = int(bw_ * 0.80); ph = int(pr.height * pw / pr.width)
    pr = pr.resize((pw, ph), Image.LANCZOS)
    layer.paste(pr, (int(CV/2 - pw/2), int(by + bh*0.10)))
    canvas.paste(layer, (0, 0), mask)
    d.rounded_rectangle([bx, by, bx+bw_, by+bh], radius=18, outline=edge, width=3)

    f = ImageFont.truetype(BOLD, 34); f2 = ImageFont.truetype(REG, 24)
    d.text((90, CV-150), label, font=f, fill=INK)
    d.text((90, CV-100), 'NATURAL CANVAS TOTE · MOCKUP', font=f2, fill=DIM)
    bw2 = d.textlength('PLOTFLOW*', font=f)
    d.text((CV-90-bw2, CV-150), 'PLOTFLOW*', font=f, fill=RED)

    path = f'{OUT}/mock-tote-{out_name}.png'
    canvas.save(path, 'PNG'); print(f'  {path}'); return path

def present_mug(wrap_path):
    """Composite the panoramic wrap onto a flat mug silhouette."""
    CV = 2160
    canvas = Image.new('RGB', (CV, CV), PAPER)
    d = ImageDraw.Draw(canvas, 'RGBA')

    mw, mh = CV*0.44, CV*0.46
    mx, my = CV/2 - mw/2 - CV*0.03, CV*0.24
    edge = (0, 0, 0, 70)

    # handle behind body
    hr = mh*0.30
    d.ellipse([mx+mw-hr*0.35, my+mh*0.22, mx+mw+hr*1.15, my+mh*0.22+hr*1.6],
              outline=(230, 228, 222), width=int(hr*0.30))
    d.ellipse([mx+mw-hr*0.35, my+mh*0.22, mx+mw+hr*1.15, my+mh*0.22+hr*1.6],
              outline=edge, width=3)

    # body + wrap band masked in (wrap shows ~40% of the full 360° art)
    mask = Image.new('L', (CV, CV), 0)
    ImageDraw.Draw(mask).rounded_rectangle([mx, my, mx+mw, my+mh], radius=40, fill=255)
    layer = Image.new('RGB', (CV, CV), (235, 233, 228))
    wr = Image.open(wrap_path)
    crop_w = int(wr.width * 0.42)
    # crop stops short of the centered brand line, and trims the brand row at
    # the bottom, so no half-cut text shows on the visible face
    wr = wr.crop((int(wr.width*0.03), 0, int(wr.width*0.03)+crop_w, wr.height - 70))
    ph = int(mh * 0.66); pw = int(wr.width * ph / wr.height)
    wr = wr.resize((pw, ph), Image.LANCZOS)
    layer.paste(wr, (int(mx + mw/2 - pw/2), int(my + mh*0.17)))
    canvas.paste(layer, (0, 0), mask)
    d.rounded_rectangle([mx, my, mx+mw, my+mh], radius=40, outline=edge, width=3)

    f = ImageFont.truetype(BOLD, 34); f2 = ImageFont.truetype(REG, 24)
    d.text((90, CV-150), 'FULL LINEUP · 11oz MUG', font=f, fill=INK)
    d.text((90, CV-100), 'PANORAMIC WRAP · MOCKUP', font=f2, fill=DIM)
    bw2 = d.textlength('PLOTFLOW*', font=f)
    d.text((CV-90-bw2, CV-150), 'PLOTFLOW*', font=f, fill=RED)

    path = f'{OUT}/mock-mug.png'
    canvas.save(path, 'PNG'); print(f'  {path}'); return path


# ============================================================
# GENERATE ALL
# ============================================================
os.chdir(ROOT)

print('=== T-SHIRT BACK PRINTS (black tee) ===')
for k in ORDER: tee_back(k, 'black')

print('\n=== T-SHIRT BACK PRINTS (white tee) ===')
for k in ORDER: tee_back(k, 'white')

print('\n=== T-SHIRT FRONT (chest logo) ===')
tee_front('black')
tee_front('white')

print('\n=== T-SHIRT LINEUP (all suits) ===')
tee_lineup('black')
tee_lineup('white')

print('\n=== POSTERS (18×24″) ===')
for k in ORDER: poster(k)

print('\n=== STICKERS (die-cut) ===')
for k in ORDER: sticker(k)

print('\n=== TOTE BAGS ===')
for k in ORDER[:3]: tote(k, 'natural')
for k in ORDER[:3]: tote(k, 'black')

print('\n=== MUG WRAP ===')
mug_wrap()

print('\n=== PIN DESIGNS ===')
for k in ORDER: pin_design(k)

print('\n=== PRESENTATION MOCKUPS (design on garment) ===')
zk = SUITS['zaku']
present_tee(f'{OUT}/merch-zaku-tee-back-black.png', 'zaku-back', 'black',
            f"{zk['code']} · {zk['name'].upper()} · BACK PRINT")
present_tee(f'{OUT}/merch-zaku-tee-back-white.png', 'zaku-back', 'white',
            f"{zk['code']} · {zk['name'].upper()} · BACK PRINT")
present_tee(f'{OUT}/merch-tee-lineup-black.png', 'lineup', 'black',
            'SEASON 01 LINEUP · BACK PRINT')
present_tee(f'{OUT}/merch-tee-front-black.png', 'front-logo', 'black',
            'CHEST LOGO · FRONT')
present_tote(f'{OUT}/merch-zaku-tote-natural.png', 'zaku',
             f"{zk['code']} · {zk['name'].upper()}")
present_mug(f'{OUT}/merch-mug-wrap.png')

print('\nDone! All merch designs generated → mockups/merch/')
