#!/usr/bin/env python3
"""
PlotFlow Media Generator
Renders each edition's continuous-line path into Instagram-ready media:

  • process video (.mp4): the suit drawn line-by-line, the way the site's
    Live Plot animates it, on Strathmore Bristol paper in red ink.
  • showcase still (.png): the finished plot, composed as a feed image.

Self-contained: parses the M/L path data straight out of data/editions.js,
draws with Pillow, and encodes with the ffmpeg binary bundled by
imageio-ffmpeg (no system ffmpeg required). Cron-friendly, no browser.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import imageio.v2 as imageio
import imageio_ffmpeg

SCRIPT_DIR = Path(__file__).parent
EDITIONS_PATH = SCRIPT_DIR.parent / 'data/editions.js'

with open(SCRIPT_DIR / 'config/settings.json') as f:
    SETTINGS = json.load(f)

# Authentic PlotFlow palette (from styles/tokens.css)
BRISTOL = (246, 243, 236)   # --bristol : the live-plot paper
RED = (232, 53, 31)         # --red     : the ink
DIM = (67, 70, 62)          # --con2    : frame + labels
INK_DARK = (21, 22, 15)     # --ink

# Fonts (Latin + CJK) discovered on the host
FONT_LATIN = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_JP = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"

Point = Tuple[float, float]
Segment = Tuple[float, float, float, float, float, float]  # x0,y0,x1,y1,len,cum_start


class PlotRenderer:
    """Renders continuous-line paths to video + still media."""

    def __init__(self):
        self.suits = self._load_suits()
        self.export_dir = SCRIPT_DIR / 'media' / 'generated'
        self.export_dir.mkdir(parents=True, exist_ok=True)

    # ---- data ---------------------------------------------------------------

    def _load_suits(self) -> Dict[str, Any]:
        """Parse window.PLOTFLOW from editions.js (valid JSON once unwrapped)."""
        with open(EDITIONS_PATH) as f:
            content = f.read()
        m = re.search(r'window\.PLOTFLOW\s*=\s*', content)
        if not m:
            raise ValueError("Could not find window.PLOTFLOW in editions.js")
        payload = content[m.end():].strip().rstrip(';').strip()
        data = json.loads(payload)
        return data.get('suits', {})

    def order(self) -> List[str]:
        return list(self.suits.keys())

    # ---- geometry -----------------------------------------------------------

    @staticmethod
    def _parse_path(d: str) -> List[List[Point]]:
        """Parse an M/L-only path string into a list of polylines.

        In this data 'M' is a pen lift (start of a new stroke) and 'L' draws
        to the next point: exactly how the AxiDraw walks the geometry.
        """
        tokens = d.replace(',', ' ').split()
        polylines: List[List[Point]] = []
        cur: Optional[List[Point]] = None
        i, n = 0, len(tokens)
        while i < n:
            t = tokens[i]
            if t in ('M', 'L'):
                x = float(tokens[i + 1]); y = float(tokens[i + 2]); i += 3
                if t == 'M':
                    cur = [(x, y)]
                    polylines.append(cur)
                else:
                    if cur is None:
                        cur = [(x, y)]; polylines.append(cur)
                    else:
                        cur.append((x, y))
            else:
                i += 1
        return polylines

    @staticmethod
    def _flatten(polylines: List[List[Point]]) -> Tuple[List[Segment], float, Tuple[float, float, float, float]]:
        """Turn polylines into a flat, arc-length-indexed segment list."""
        segs: List[Segment] = []
        cum = 0.0
        minx = miny = float('inf')
        maxx = maxy = float('-inf')

        def note(px, py):
            nonlocal minx, miny, maxx, maxy
            minx = min(minx, px); miny = min(miny, py)
            maxx = max(maxx, px); maxy = max(maxy, py)

        for poly in polylines:
            for (x, y) in poly:
                note(x, y)
            for (x0, y0), (x1, y1) in zip(poly, poly[1:]):
                length = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
                if length <= 0:
                    continue
                segs.append((x0, y0, x1, y1, length, cum))
                cum += length

        if minx == float('inf'):
            minx = miny = 0.0; maxx = maxy = 1.0
        return segs, cum, (minx, miny, maxx, maxy)

    @staticmethod
    def _make_transform(bbox, cw, ch, ox, oy):
        """Fit bbox into a cw×ch content box at offset (ox,oy), preserve aspect."""
        minx, miny, maxx, maxy = bbox
        bw = max(1e-6, maxx - minx)
        bh = max(1e-6, maxy - miny)
        pad = max(bw, bh) * 0.06
        minx -= pad; miny -= pad; bw += 2 * pad; bh += 2 * pad
        s = min(cw / bw, ch / bh)
        # center within the content box
        tx = ox + (cw - bw * s) / 2 - minx * s
        ty = oy + (ch - bh * s) / 2 - miny * s

        def tf(x, y):
            return (x * s + tx, y * s + ty)
        return tf, s

    # ---- drawing helpers ----------------------------------------------------

    def _base_paper(self, w: int, h: int) -> Image.Image:
        """Bristol sheet with a subtle inset frame, echoing the plot bed."""
        img = Image.new('RGB', (w, h), BRISTOL)
        d = ImageDraw.Draw(img)
        m = int(min(w, h) * 0.035)
        d.rectangle([m, m, w - m, h - m], outline=DIM + (0,) if False else DIM, width=max(1, w // 900))
        return img

    def _font(self, path: str, size: int) -> ImageFont.FreeTypeFont:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            return ImageFont.load_default()

    def _draw_labels(self, img: Image.Image, suit: Dict[str, Any], ss: int):
        """Corner bed label + name/JP, plotter-HUD style."""
        d = ImageDraw.Draw(img)
        w, h = img.size
        pad = int(w * 0.06)
        f_small = self._font(FONT_LATIN, int(w * 0.022))
        f_name = self._font(FONT_LATIN, int(w * 0.040))
        f_jp = self._font(FONT_JP, int(w * 0.030))

        # top-left: BED 01 · CODE
        d.text((pad, pad), f"BED 01 · {suit.get('code', '')}", font=f_small, fill=DIM)
        # top-right: マシンドロー (drawn by machine)
        machine = "マシンドロー"
        bbox = d.textbbox((0, 0), machine, font=f_jp)
        d.text((w - pad - (bbox[2] - bbox[0]), pad), machine, font=f_jp, fill=DIM)

        # bottom-left: name + JP
        name = suit.get('name', '')
        jp = suit.get('jp', '')
        d.text((pad, h - pad - int(w * 0.075)), name, font=f_name, fill=INK_DARK)
        d.text((pad, h - pad - int(w * 0.032)), jp, font=f_jp, fill=DIM)

    # ---- public: video ------------------------------------------------------

    def render_video(self, key: str, size: int = 1080, fps: int = 30,
                     duration: float = 14.0, supersample: int = 2,
                     out_path: Optional[Path] = None) -> Path:
        """Render the line-by-line plotting animation to an MP4."""
        suit = self.suits[key]
        segs, total_len, bbox = self._flatten(self._parse_path(suit['d']))
        if total_len <= 0:
            raise ValueError(f"{key}: path has zero length")

        ss = supersample
        W = size * ss
        m = int(W * 0.035)
        content = (W - 2 * m, W - 2 * m)
        tf, scale = self._make_transform(bbox, content[0], content[1], m, m)
        line_w = max(1, int(W * 0.0022))
        pen_r = max(2, int(W * 0.010))

        paper = self._base_paper(W, W)
        ink = Image.new('RGBA', (W, W), (0, 0, 0, 0))
        idraw = ImageDraw.Draw(ink)

        frames = max(2, int(fps * duration))
        out_path = out_path or (self.export_dir / f"{key}_process.mp4")
        tmp_video = out_path.with_suffix('.noaudio.mp4')

        # ease-in-out so the pen starts/settles gently
        def ease(t): return t * t * (3 - 2 * t)

        writer = imageio.get_writer(
            str(tmp_video), fps=fps, codec='libx264', quality=8,
            macro_block_size=None,
            ffmpeg_params=['-pix_fmt', 'yuv420p', '-movflags', '+faststart'],
        )

        drawn_len = 0.0
        cursor = 0  # index into segs; advances monotonically
        head = None
        try:
            for i in range(frames + 1):
                target = ease(i / frames) * total_len
                # extend ink from drawn_len -> target
                j = cursor
                while j < len(segs):
                    x0, y0, x1, y1, slen, cstart = segs[j]
                    cend = cstart + slen
                    if cend <= drawn_len:
                        j += 1; continue
                    if cstart >= target:
                        break
                    a = max(drawn_len, cstart); b = min(target, cend)
                    ta = (a - cstart) / slen
                    tb = (b - cstart) / slen
                    ax, ay = x0 + (x1 - x0) * ta, y0 + (y1 - y0) * ta
                    bx, by = x0 + (x1 - x0) * tb, y0 + (y1 - y0) * tb
                    idraw.line([tf(ax, ay), tf(bx, by)], fill=RED + (255,),
                               width=line_w, joint='curve')
                    head = tf(bx, by)
                    if cend <= target:
                        j += 1
                    else:
                        break
                cursor = j
                drawn_len = target

                # composite paper + ink + pen head
                frame = paper.copy()
                frame.paste(ink, (0, 0), ink)
                if head is not None and i < frames:
                    fd = ImageDraw.Draw(frame)
                    hx, hy = head
                    fd.ellipse([hx - pen_r, hy - pen_r, hx + pen_r, hy + pen_r],
                               outline=INK_DARK, width=max(1, line_w))
                    fd.line([hx - pen_r * 1.7, hy, hx + pen_r * 1.7, hy], fill=INK_DARK, width=1)
                    fd.line([hx, hy - pen_r * 1.7, hx, hy + pen_r * 1.7], fill=INK_DARK, width=1)

                self._draw_labels(frame, suit, ss)
                out = frame.resize((size, size), Image.LANCZOS) if ss > 1 else frame
                writer.append_data(np.asarray(out))

            # hold the finished frame for ~1s
            for _ in range(fps):
                writer.append_data(np.asarray(out))
        finally:
            writer.close()

        self._add_silent_audio(tmp_video, out_path)
        tmp_video.unlink(missing_ok=True)
        return out_path

    # ---- public: still ------------------------------------------------------

    def render_still(self, key: str, width: int = 1080, height: int = 1350,
                     supersample: int = 2, out_path: Optional[Path] = None) -> Path:
        """Render the finished plot as a feed still (4:5 portrait by default)."""
        suit = self.suits[key]
        segs, total_len, bbox = self._flatten(self._parse_path(suit['d']))

        ss = supersample
        W, H = width * ss, height * ss
        m = int(W * 0.05)
        # leave headroom at the bottom for the label block
        content = (W - 2 * m, H - 2 * m - int(H * 0.10))
        tf, scale = self._make_transform(bbox, content[0], content[1], m, m)
        line_w = max(1, int(W * 0.0024))

        img = Image.new('RGB', (W, H), BRISTOL)
        d = ImageDraw.Draw(img)
        d.rectangle([m, m, W - m, H - m], outline=DIM, width=max(1, W // 900))

        for (x0, y0, x1, y1, slen, cstart) in segs:
            d.line([tf(x0, y0), tf(x1, y1)], fill=RED, width=line_w, joint='curve')

        # label block
        pad = m
        f_code = self._font(FONT_LATIN, int(W * 0.020))
        f_name = self._font(FONT_LATIN, int(W * 0.045))
        f_jp = self._font(FONT_JP, int(W * 0.032))
        by = H - m - int(H * 0.085)
        d.text((pad, by), f"{suit.get('code', '')} · {suit.get('edition', '')}", font=f_code, fill=DIM)
        d.text((pad, by + int(W * 0.028)), suit.get('name', ''), font=f_name, fill=INK_DARK)
        jp = suit.get('jp', '')
        bbox_jp = d.textbbox((0, 0), jp, font=f_jp)
        d.text((W - pad - (bbox_jp[2] - bbox_jp[0]), by + int(W * 0.030)), jp, font=f_jp, fill=DIM)
        # drawn-by-machine signature (no price: gallery, not storefront)
        d.text((W - pad - int(W * 0.22), by), 'マシンドロー', font=self._font(FONT_JP, int(W * 0.024)), fill=RED)

        out_path = out_path or (self.export_dir / f"{key}_showcase.png")
        final = img.resize((width, height), Image.LANCZOS) if ss > 1 else img
        final.save(out_path, 'PNG')
        return out_path

    # ---- encoding -----------------------------------------------------------

    def _add_silent_audio(self, video_in: Path, video_out: Path):
        """Mux a silent AAC track (some IG endpoints require an audio stream)."""
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ffmpeg, '-y', '-i', str(video_in),
            '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
            '-shortest', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k',
            '-movflags', '+faststart', str(video_out),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # ---- batch build + manifest --------------------------------------------

    def build_all(self, keys: Optional[List[str]] = None, video_duration: float = 14.0,
                  publish_dir: Optional[Path] = None) -> Dict[str, Any]:
        """Render video + still for each edition and write a manifest.

        The manifest maps each edition key to its media filenames and (if a
        site URL is configured) the public URLs the Instagram API will fetch.
        When publish_dir is given, media is also copied there: point it at a
        folder served by GitHub Pages (e.g. ../assets/social) so the files are
        publicly reachable at your domain.
        """
        keys = keys or self.order()
        site = SETTINGS.get('site', {})
        site_url = (site.get('url') or '').rstrip('/')
        social_path = (site.get('social_path') or 'assets/social').strip('/')

        manifest: Dict[str, Any] = {}
        for key in keys:
            print(f"🎬 {key}: video …")
            video = self.render_video(key, duration=video_duration)
            print(f"🖼  {key}: still …")
            still = self.render_still(key)

            entry: Dict[str, str] = {"video": video.name, "still": still.name}

            if publish_dir:
                publish_dir = Path(publish_dir)
                publish_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(video, publish_dir / video.name)
                shutil.copy2(still, publish_dir / still.name)

            if site_url:
                base = f"{site_url}/{social_path}"
                entry["video_url"] = f"{base}/{video.name}"
                entry["still_url"] = f"{base}/{still.name}"

            manifest[key] = entry

        manifest_path = self.export_dir / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest, indent=2))
        print(f"\n✓ Manifest → {manifest_path}")
        return manifest


class MediaLibrary:
    """Reads the media manifest so the poster can resolve edition → media URL."""

    def __init__(self, manifest_path: Optional[Path] = None):
        self.manifest_path = manifest_path or (SCRIPT_DIR / 'media' / 'generated' / 'manifest.json')
        self.manifest = {}
        if self.manifest_path.exists():
            self.manifest = json.loads(self.manifest_path.read_text())

    def url_for(self, key: str, media_type: str) -> Optional[str]:
        """Return the public URL for an edition's video or image, if known."""
        entry = self.manifest.get(key)
        if not entry:
            return None
        field = 'video_url' if media_type == 'video' else 'still_url'
        return entry.get(field)

    def has(self, key: str) -> bool:
        return key in self.manifest


def main():
    import argparse
    p = argparse.ArgumentParser(description='PlotFlow media generator')
    p.add_argument('command', choices=['video', 'still', 'all', 'build', 'list'])
    p.add_argument('--key', help='edition key (e.g. zaku). Omit for all editions.')
    p.add_argument('--duration', type=float, default=14.0, help='video seconds (default 14)')
    p.add_argument('--size', type=int, default=1080)
    p.add_argument('--publish-dir', help='also copy media here (e.g. ../assets/social) for public hosting')
    args = p.parse_args()

    r = PlotRenderer()

    if args.command == 'list':
        print("Available editions:")
        for k in r.order():
            s = r.suits[k]
            print(f"  {k:12s} {s.get('code',''):10s} {s.get('name','')}")
        return

    if args.command == 'build':
        # Render everything + write the manifest the poster consumes.
        keys = [args.key] if args.key else None
        r.build_all(keys=keys, video_duration=args.duration,
                    publish_dir=args.publish_dir)
        print("\n✨ Media build complete!")
        return

    keys = [args.key] if args.key else r.order()
    for key in keys:
        if args.command in ('video', 'all'):
            print(f"🎬 Rendering video: {key} ...")
            out = r.render_video(key, size=args.size, duration=args.duration)
            print(f"   ✓ {out} ({out.stat().st_size // 1024} KB)")
        if args.command in ('still', 'all'):
            print(f"🖼  Rendering still: {key} ...")
            out = r.render_still(key, width=args.size)
            print(f"   ✓ {out} ({out.stat().st_size // 1024} KB)")

    print("\n✨ Media generation complete!")


if __name__ == '__main__':
    main()
