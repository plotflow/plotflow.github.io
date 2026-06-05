#!/usr/bin/env python3
"""
prep_plots.py — normalize raw plotter.vision SVG exports.

Raw exports come as a single <path> with width/height in px and a hard-coded
red stroke. This makes them recolorable + responsive:
  - adds a viewBox so they scale
  - sets stroke to `currentColor` (recolor via CSS `color`)
  - constant 1.4px non-scaling stroke (override per-context in CSS)
  - rounds coordinates to ints to slim the file

Usage:
  python tools/prep_plots.py path/to/raw_exports/   # writes into assets/plots/
"""
import os, re, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(HERE, "..", "assets", "plots")

def prep(src_path, out_path):
    s = open(src_path).read()
    W = int(re.search(r"width='(\d+)px'", s).group(1))
    H = int(re.search(r"height='(\d+)px'", s).group(1))
    m = re.search(r"d='([^']*)'", s); d = m.group(1)
    d = re.sub(r"-?\d+\.\d+", lambda x: str(round(float(x.group(0)))), d)
    d = re.sub(r"\s+", " ", d).strip()
    s = s.replace(m.group(0), "d='" + d + "'")
    s = s.replace("style='stroke:#ff0000;stroke-width:1;fill:none'",
                  "fill='none' stroke='currentColor' stroke-width='1.4' "
                  "stroke-linejoin='round' stroke-linecap='round' vector-effect='non-scaling-stroke'")
    s = s.replace("width='%dpx' height='%dpx'" % (W, H),
                  "viewBox='0 0 %d %d' width='100%%' height='100%%' preserveAspectRatio='xMidYMid meet'" % (W, H))
    s = re.sub(r"<\?xml[^>]*\?>", "", s)
    s = re.sub(r"<desc>.*?</desc>", "", s).strip()
    open(out_path, "w").write(s)

if __name__ == "__main__":
    src_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(OUT, exist_ok=True)
    files = sorted(glob.glob(os.path.join(src_dir, "*.svg")))
    if not files:
        print("No .svg files found in", src_dir); sys.exit(1)
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        prep(f, os.path.join(OUT, name + ".svg"))
        print("prepped", name)
    print("Now run: python tools/build_data.py")
