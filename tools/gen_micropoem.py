#!/usr/bin/env python3
"""
gen_micropoem.py — micro-lettering poem sheets for the plotter.

Sets a poem in single-stroke Hershey lettering at ~2.4 mm cap height and
repeats it to fill the sheet — from viewing distance the page reads as a
grey field; up close it is language. Output is M/L-only SVG (same
dialect as the rest of the pipeline) plus a full-sheet PNG preview and a
4x detail crop.

The demo text is public-domain (Emily Dickinson). Swap POEM for any
text you have the rights to.

Usage:  python tools/gen_micropoem.py
"""
import os, re
from HersheyFonts import HersheyFonts

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets", "generative")

W, H = 1100, 1400          # sheet in working units (0.3 mm/unit at 420 mm)
MARGIN = 100
CAP = 8.0                  # cap height in units  (~2.4 mm on paper)
LEAD = 13.0                # line advance
GAP_WORD = 4.0             # extra advance between words
STANZA_MARK = " * "

POEM = (
    '"Hope" is the thing with feathers - That perches in the soul - '
    "And sings the tune without the words - And never stops - at all - "
    + STANZA_MARK +
    "And sweetest - in the Gale - is heard - And sore must be the storm - "
    "That could abash the little Bird That kept so many warm - "
    + STANZA_MARK +
    "I've heard it in the chillest land - And on the strangest Sea - "
    "Yet - never - in Extremity, It asked a crumb - of me. "
    + STANZA_MARK
)

font = HersheyFonts()
font.load_default_font("futural")


def word_strokes(word):
    """Strokes for one word in font units, plus its advance width."""
    strokes = [list(s) for s in font.strokes_for_text(word)]
    xs = [x for s in strokes for x, _ in s]
    width = (max(xs) - min(xs)) if xs else 0
    return strokes, width


# measure the font's cap height once to derive the scale factor
_caps, _ = word_strokes("H")
_ys = [y for s in _caps for _, y in s]
SCALE = CAP / (max(_ys) - min(_ys))

# advance width of a space in scaled units (measured via a probe pair)
_, w_i = word_strokes("nn")
_, w_2 = word_strokes("n n")
SPACE = max(4.0, (w_2 - w_i) * SCALE)


def layout(text):
    """Greedy line-wrap into the sheet; returns list of polylines."""
    words = re.sub(r"\s+", " ", text).strip().split(" ")
    polys = []
    x, y = MARGIN, MARGIN + CAP
    max_x = W - MARGIN
    wi = 0
    while y < H - MARGIN:
        word = words[wi % len(words)]
        strokes, width = word_strokes(word)
        w_scaled = width * SCALE
        if x + w_scaled > max_x:
            x = MARGIN
            y += LEAD
            if y >= H - MARGIN:
                break
        all_x = [p[0] for st in strokes for p in st]
        base = min(all_x) if all_x else 0
        for st in strokes:
            poly = [(x + (px - base) * SCALE, y + py * SCALE) for px, py in st]
            if len(poly) > 1:
                polys.append(poly)
        x += w_scaled + SPACE
        wi += 1
    return polys


def to_svg(polys, path):
    sub = []
    for p in polys:
        pieces = ["M %.2f,%.2f" % p[0]]
        pieces += ["L %.2f,%.2f" % q for q in p[1:]]
        sub.append(" ".join(pieces))
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d">\n'
           '<path d="%s" fill="none" stroke="#15160f" stroke-width="0.5"/>\n'
           '</svg>\n') % (W, H, " ".join(sub))
    with open(path, "w") as f:
        f.write(svg)


def to_png(polys, path, scale=1.0, ss=2, crop=None):
    from PIL import Image, ImageDraw
    w, h = int(W * scale) * ss, int(H * scale) * ss
    im = Image.new("RGB", (w, h), (246, 243, 236))
    dr = ImageDraw.Draw(im)
    k = scale * ss
    for p in polys:
        dr.line([(x * k, y * k) for x, y in p], fill=(21, 22, 15), width=1)
    im = im.resize((w // ss, h // ss), Image.LANCZOS)
    if crop:
        cx, cy, cw, ch, zoom = crop
        im = im.crop((int(cx * scale), int(cy * scale),
                      int((cx + cw) * scale), int((cy + ch) * scale)))
        im = im.resize((int(cw * scale * zoom), int(ch * scale * zoom)), Image.LANCZOS)
    im.save(path)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    polys = layout(POEM)
    base = os.path.join(OUT, "micropoem-hope")
    to_svg(polys, base + ".svg")
    to_png(polys, base + ".png")
    to_png(polys, base + "-detail.png", crop=(MARGIN, MARGIN, 340, 220, 3))
    verts = sum(len(p) for p in polys)
    ink = sum(sum(((p[i+1][0]-p[i][0])**2 + (p[i+1][1]-p[i][1])**2) ** .5
                  for i in range(len(p)-1)) for p in polys) * (420/1400) / 1000
    print("micropoem strokes=%d verts=%d ink=%.1fm -> %s.{svg,png}" % (len(polys), verts, ink, base))
