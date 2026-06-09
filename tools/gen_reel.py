#!/usr/bin/env python3
"""
PLOTFLOW · Server-side Reel generator
Renders the live-plot engine into vertical 1080x1920 H.264 MP4s for Instagram,
mirroring reel.html but headless (no browser). Reads paths from data/editions.js.

Usage:
  python3 tools/gen_reel.py                      # all editions, red, 15s, 30fps
  python3 tools/gen_reel.py zaku red 15          # one edition
  python3 tools/gen_reel.py --all black 20       # all editions, black ink, 20s
Output: <key>-<color>-reel.mp4 in the current directory.

Deps: pillow, numpy, imageio-ffmpeg (bundles ffmpeg w/ libx264).
Fonts: uses Liberation Sans + IPA Gothic (JP). Swap BOLD/REG to Archivo locally
for the exact site typeface.
"""
import json, re, sys, math, subprocess, os
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import imageio_ffmpeg

# ---------- load editions data ----------
src = open('/home/user/plotflow.github.io/data/editions.js').read()
# strip the JS wrapper -> JSON
src = src[src.index('{'):]
src = src[:src.rindex('}')+1]
DATA = json.loads(src)
SUITS = DATA['suits']
ORDER = DATA.get('plotterOrder', list(SUITS.keys()))

# ---------- config ----------
W, H = 1080, 1920
PAPER = (246, 243, 236)
INK_HEX = {'black': (23, 21, 15), 'red': (216, 52, 42), 'blue': (31, 74, 160)}
HUD = (21, 22, 15)
FEED = 1100
ART = (60, 280, 960, 1300)  # x,y,w,h

BOLD = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
REG  = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
JP   = '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf'

# ---------- parse path 'd' into polyline subpaths ----------
def parse_path(d):
    # tokens like "M 744,398" or "L 736,382"
    subpaths, cur = [], []
    for cmd, xs, ys in re.findall(r'([ML])\s*(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)', d):
        x, y = float(xs), float(ys)
        if cmd == 'M':
            if len(cur) > 1: subpaths.append(cur)
            cur = [(x, y)]
        else:
            cur.append((x, y))
    if len(cur) > 1: subpaths.append(cur)
    return subpaths

def seg_lengths(subpaths):
    segs = []  # (x0,y0,x1,y1, cumlen_start)
    total = 0.0
    for sp in subpaths:
        for i in range(len(sp)-1):
            x0,y0 = sp[i]; x1,y1 = sp[i+1]
            L = math.hypot(x1-x0, y1-y0)
            segs.append((x0,y0,x1,y1,total,L))
            total += L
    return segs, total

def bbox(subpaths):
    xs = [p[0] for sp in subpaths for p in sp]
    ys = [p[1] for sp in subpaths for p in sp]
    return min(xs), min(ys), max(xs), max(ys)

# ---------- easing ----------
def ease_out_cubic(t): return 1 - (1-t)**3
def smoothstep(t): return t*t*(3-2*t)

def fmt(sec):
    s = max(0, round(sec))
    return f"{s//60:02d}:{s%60:02d}"

# ---------- render one reel ----------
def render(key, color, dur=15, fps=30, out=None):
    suit = SUITS[key]
    ink = INK_HEX[color]
    subpaths = parse_path(suit['d'])
    minx, miny, maxx, maxy = bbox(subpaths)
    pad = max(maxx-minx, maxy-miny) * 0.06
    vbx, vby = minx-pad, miny-pad
    vbw, vbh = (maxx-minx)+2*pad, (maxy-miny)+2*pad
    segs, total_len = seg_lengths(subpaths)

    ax, ay, aw, ah = ART
    sc = min(aw/vbw, ah/vbh)
    ox = ax + (aw - vbw*sc)/2
    oy = ay + (ah - vbh*sc)/2
    def mx(x): return ox + (x-vbx)*sc
    def my(y): return oy + (y-vby)*sc

    mm_per_unit = 420 / max(vbw, vbh)
    ink_total_m = (total_len * mm_per_unit) / 1000
    total_sec = (total_len * mm_per_unit) / FEED * 60

    total_frames = dur * fps
    plot_end = int(total_frames * 0.80)
    hold_end = int(total_frames * 0.92)

    # fonts
    f_logo = ImageFont.truetype(BOLD, 56)
    f_bed  = ImageFont.truetype(BOLD, 26)
    f_name = ImageFont.truetype(REG, 22)
    f_jp   = ImageFont.truetype(JP, 26)
    f_stat = ImageFont.truetype(BOLD, 22)
    f_small= ImageFont.truetype(REG, 17)
    f_end_logo = ImageFont.truetype(BOLD, 88)
    f_end_name = ImageFont.truetype(BOLD, 32)
    f_end_jp   = ImageFont.truetype(JP, 30)
    f_end_tag  = ImageFont.truetype(REG, 20)

    out = out or f'/tmp/{key}-{color}-reel.mp4'
    ff = imageio_ffmpeg.write_frames(
        out, (W, H), fps=fps, codec='libx264', quality=None,
        bitrate='10M', pix_fmt_in='rgb24', pix_fmt_out='yuv420p',
        macro_block_size=1,
        output_params=['-preset','medium','-profile:v','high','-movflags','+faststart']
    )
    ff.send(None)

    def hud_rgba(a=0.30): return HUD + (int(255*a),)

    for f in range(total_frames):
        if f < plot_end:
            prog = smoothstep(f/plot_end); phase='draw'; alpha=0
        elif f < hold_end:
            prog = 1.0; phase='hold'; alpha=0
        else:
            prog = 1.0; phase='end'
            alpha = (f-hold_end)/(total_frames-hold_end)

        img = Image.new('RGB', (W,H), PAPER)
        d = ImageDraw.Draw(img, 'RGBA')

        # ---- strokes up to prog ----
        target = prog * total_len
        pen = None
        for (x0,y0,x1,y1,cs,L) in segs:
            if cs >= target: break
            if cs+L <= target:
                d.line([(mx(x0),my(y0)),(mx(x1),my(y1))], fill=ink, width=2)
                pen = (x1,y1)
            else:
                frac = (target-cs)/L
                xe = x0+(x1-x0)*frac; ye=y0+(y1-y0)*frac
                d.line([(mx(x0),my(y0)),(mx(xe),my(ye))], fill=ink, width=2)
                pen = (xe,ye)
                break

        # ---- HUD ----
        hc = hud_rgba(0.30)
        d.text((60,60), f'BED 01 · {suit["code"]}', font=f_bed, fill=hc)
        lw = d.textlength('PLOTFLOW*', font=f_bed)
        d.text((W-60-lw,60), 'PLOTFLOW*', font=f_bed, fill=hc)
        d.text((60,96), suit['name'], font=f_name, fill=hc)
        d.text((60,122), suit.get('jp',''), font=f_jp, fill=hc)
        fr = f'F{FEED} mm/min'
        d.text((W-60-d.textlength(fr,font=f_small),98), fr, font=f_small, fill=hc)

        bar_y = H-160
        d.rectangle([60,bar_y,W-60,bar_y+3], fill=HUD+(26,))
        d.rectangle([60,bar_y,60+(W-120)*prog,bar_y+3], fill=ink)
        ink_drawn = (target*mm_per_unit)/1000
        elapsed = total_sec*prog
        d.text((60,bar_y+16), f'{fmt(elapsed)} / {fmt(total_sec)}', font=f_stat, fill=hc)
        pct = f'{round(prog*100)}%'
        d.text((W/2-d.textlength(pct,font=f_stat)/2,bar_y+16), pct, font=f_stat, fill=hc)
        inkstr = f'{ink_drawn:.1f}m / {ink_total_m:.1f}m ink'
        d.text((W-60-d.textlength(inkstr,font=f_stat),bar_y+16), inkstr, font=f_stat, fill=hc)

        if pen and 0 < prog < 1:
            px,py = mx(pen[0]),my(pen[1]); r=14
            d.ellipse([px-r,py-r,px+r,py+r], outline=(232,53,31,160), width=2)
            d.line([px-r*1.8,py,px+r*1.8,py], fill=(232,53,31,160), width=2)
            d.line([px,py-r*1.8,px,py+r*1.8], fill=(232,53,31,160), width=2)
            d.text((60,bar_y+44), f'X {round(pen[0]*mm_per_unit)}  Y {round(pen[1]*mm_per_unit)}', font=f_small, fill=hc)

        # ---- end card crossfade ----
        if phase=='end':
            ov = Image.new('RGBA',(W,H),(246,243,236,int(255*min(1,alpha))))
            img = Image.alpha_composite(img.convert('RGBA'), ov).convert('RGB')
            if alpha>0.15:
                a2 = min(1,(alpha-0.15)/0.6)
                d2 = ImageDraw.Draw(img,'RGBA')
                def ctext(y,txt,fnt,col):
                    w=d2.textlength(txt,font=fnt); d2.text((W/2-w/2,y),txt,font=fnt,fill=col+(int(255*a2),))
                ctext(H/2-90,'PLOTFLOW*',f_end_logo,(21,22,15))
                ctext(H/2+10,f'{suit["code"]}  {suit["name"]}',f_end_name,(21,22,15))
                ctext(H/2+60,suit.get('jp',''),f_end_jp,(91,94,84))
                ctext(H-110,'DRAWN BY MACHINE · マシンドロー',f_end_tag,(143,145,132))

        ff.send(np.asarray(img))

    ff.close()
    sz = os.path.getsize(out)/1024/1024
    print(f'{key}-{color}: {out}  {sz:.1f} MB  ({total_frames} frames @ {fps}fps, {dur}s)')
    return out

if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0] in ('--all','-a','all'):
        color = a[1] if len(a)>1 else 'red'
        dur   = int(a[2]) if len(a)>2 else 15
        for k in ORDER:
            render(k, color, dur=dur)
    else:
        key   = a[0]
        color = a[1] if len(a)>1 else 'red'
        dur   = int(a[2]) if len(a)>2 else 15
        render(key, color, dur=dur)
