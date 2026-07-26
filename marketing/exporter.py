#!/usr/bin/env python3
"""
PlotFlow Post Exporter
Turns the scheduled queue into ready-to-post packs you can publish by hand —
no Meta API, no app approval, no account dependency. For each scheduled post it
writes a folder with the media file + caption.txt, and builds a single review
board (index.html) with per-post media preview, the scheduled time, and a
one-click "Copy caption" button.

This is the manual-assist posting path: open the review page, and for each slot
copy the caption and save/upload the media via the Instagram app in seconds.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

SCRIPT_DIR = Path(__file__).parent
GENERATED = SCRIPT_DIR / 'media' / 'generated'
SOCIAL_FALLBACK = SCRIPT_DIR.parent / 'assets' / 'social'
QUEUE_FILE = SCRIPT_DIR / 'content' / 'post_queue.json'
EXPORTS = SCRIPT_DIR / 'exports'


def _load_queue() -> List[Dict[str, Any]]:
    if QUEUE_FILE.exists():
        return json.loads(QUEUE_FILE.read_text())
    return []


def _load_manifest() -> Dict[str, Any]:
    mf = GENERATED / 'manifest.json'
    return json.loads(mf.read_text()) if mf.exists() else {}


def _find_media(filename: str) -> Optional[Path]:
    """Locate a media file locally (generated dir first, then committed assets)."""
    for base in (GENERATED, SOCIAL_FALLBACK):
        p = base / filename
        if p.exists():
            return p
    return None


def _media_filename(post: Dict[str, Any], manifest: Dict[str, Any]) -> Optional[str]:
    key = post.get('edition_key', '')
    entry = manifest.get(key, {})
    if post.get('media_needed') == 'video':
        return entry.get('video')
    return entry.get('still')


def export_queue(only_queued: bool = True) -> Path:
    """Export scheduled posts into a dated folder of ready-to-post packs."""
    queue = _load_queue()
    if only_queued:
        queue = [p for p in queue if p.get('status', 'queued') == 'queued']

    if not queue:
        raise SystemExit(
            "Nothing to export. Run: python automate.py schedule --days 7"
        )

    manifest = _load_manifest()
    queue.sort(key=lambda p: p.get('scheduled_at', ''))

    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_dir = EXPORTS / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    cards: List[Dict[str, Any]] = []
    missing = 0

    for i, post in enumerate(queue, 1):
        caption = post['captions'][0] if post.get('captions') else ''
        media_name = _media_filename(post, manifest)
        media_src = _find_media(media_name) if media_name else None

        slug = f"{i:02d}_{post.get('edition_key','post')}_{post.get('post_type','')}"
        pack = out_dir / slug
        pack.mkdir(exist_ok=True)

        # caption.txt
        (pack / 'caption.txt').write_text(caption, encoding='utf-8')

        media_rel = None
        if media_src:
            shutil.copy2(media_src, pack / media_src.name)
            media_rel = f"{slug}/{media_src.name}"
        else:
            missing += 1

        cards.append({
            "n": i,
            "edition": post.get('edition', ''),
            "post_type": post.get('post_type', ''),
            "media_type": post.get('media_needed', ''),
            "scheduled_at": post.get('scheduled_at', ''),
            "caption": caption,
            "media_rel": media_rel,
            "media_name": media_name or "(no media — run media_generator build)",
        })

    (out_dir / 'index.html').write_text(_render_board(cards, stamp), encoding='utf-8')
    (out_dir / 'posts.json').write_text(json.dumps(cards, indent=2, ensure_ascii=False), encoding='utf-8')

    print(f"✓ Exported {len(cards)} posts → {out_dir}")
    if missing:
        print(f"⚠️  {missing} posts have no media. Run: python media_generator.py build")
    print(f"\n📋 Open the review board:\n   {out_dir / 'index.html'}")
    return out_dir


def _render_board(cards: List[Dict[str, Any]], stamp: str) -> str:
    """Render a self-contained review page with copy-caption buttons."""
    def esc(s: str) -> str:
        return (s.replace('&', '&amp;').replace('<', '&lt;')
                 .replace('>', '&gt;').replace('"', '&quot;'))

    def fmt_when(iso: str) -> str:
        try:
            return datetime.fromisoformat(iso).strftime('%a %b %d · %H:%M')
        except Exception:
            return iso or '—'

    items = []
    for c in cards:
        if c['media_rel'] and c['media_rel'].endswith('.mp4'):
            preview = f'<video src="{c["media_rel"]}" controls loop muted playsinline></video>'
        elif c['media_rel']:
            preview = f'<img src="{c["media_rel"]}" alt="">'
        else:
            preview = '<div class="nomedia">no media</div>'

        items.append(f"""
      <article class="card">
        <div class="media">{preview}</div>
        <div class="body">
          <div class="meta">
            <span class="badge">{esc(c['post_type'])} · {esc(c['media_type'])}</span>
            <span class="when">{esc(fmt_when(c['scheduled_at']))}</span>
          </div>
          <h3>#{c['n']} · {esc(c['edition'])}</h3>
          <textarea readonly rows="9">{esc(c['caption'])}</textarea>
          <div class="actions">
            <button onclick="copyCap(this)">Copy caption</button>
            <span class="file">{esc(c['media_name'])}</span>
          </div>
        </div>
      </article>""")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PLOTFLOW · Post board {stamp}</title>
<style>
  :root {{ --bristol:#f6f3ec; --ink:#15160f; --red:#e8351f; --dim:#43463e; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bristol); color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; }}
  header {{ padding:24px 20px; border-bottom:1px solid #ddd; position:sticky; top:0;
    background:var(--bristol); z-index:2; }}
  header h1 {{ margin:0; font-size:20px; letter-spacing:.02em; }}
  header p {{ margin:4px 0 0; color:var(--dim); font-size:13px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(360px,1fr));
    gap:20px; padding:20px; max-width:1400px; margin:0 auto; }}
  .card {{ background:#fff; border:1px solid #e4e0d6; border-radius:10px; overflow:hidden;
    display:flex; flex-direction:column; }}
  .media {{ background:var(--bristol); aspect-ratio:1/1; display:flex; align-items:center; justify-content:center; }}
  .media img, .media video {{ width:100%; height:100%; object-fit:contain; }}
  .nomedia {{ color:var(--dim); font-size:13px; }}
  .body {{ padding:14px; display:flex; flex-direction:column; gap:8px; }}
  .meta {{ display:flex; justify-content:space-between; align-items:center; }}
  .badge {{ background:var(--dim); color:#fff; font-size:11px; padding:3px 8px; border-radius:20px;
    text-transform:uppercase; letter-spacing:.04em; }}
  .when {{ color:var(--dim); font-size:12px; }}
  h3 {{ margin:0; font-size:15px; }}
  textarea {{ width:100%; border:1px solid #e4e0d6; border-radius:6px; padding:10px;
    font-size:12px; line-height:1.5; resize:vertical; font-family:inherit; background:#fbfaf6; }}
  .actions {{ display:flex; align-items:center; gap:10px; }}
  button {{ background:var(--red); color:#fff; border:0; border-radius:6px; padding:9px 14px;
    font-weight:600; cursor:pointer; font-size:13px; }}
  button.ok {{ background:#2e7d32; }}
  .file {{ font-size:11px; color:var(--dim); word-break:break-all; }}
</style></head>
<body>
  <header>
    <h1>PLOTFLOW* · Post board</h1>
    <p>{len(cards)} posts ready. Copy the caption, save the media, post via the Instagram app. Batch {stamp}.</p>
  </header>
  <div class="grid">{''.join(items)}</div>
  <script>
    function copyCap(btn) {{
      const ta = btn.closest('.card').querySelector('textarea');
      navigator.clipboard.writeText(ta.value).then(() => {{
        const t = btn.textContent; btn.textContent = 'Copied ✓'; btn.classList.add('ok');
        setTimeout(() => {{ btn.textContent = t; btn.classList.remove('ok'); }}, 1500);
      }});
    }}
  </script>
</body></html>"""


# ============================================================
# CARD LIBRARY EXPORT — the 5 editorial card styles (assets/posts)
# ============================================================

CARDS_DIR = SCRIPT_DIR.parent / 'assets' / 'posts'
CAPTIONS_FILE = SCRIPT_DIR.parent / 'tools' / 'captions.json'
EDITIONS_FILE = SCRIPT_DIR.parent / 'data' / 'editions.js'

# Card types in the order we'd post a suit's set, most attention-grabbing first.
CARD_TYPES = ['process', 'lore', 'spec', 'drop']

BRAND_CAPTION = (
    "PLOTFLOW* — 一筆書き, one continuous line.\n\n"
    "Universal-Century mobile suits, rebuilt as continuous vector paths and "
    "traced in pigment ink on archival paper by an AxiDraw plotter. "
    "Nothing is printed. Every impression is drawn.\n\n"
    "Made to order · signed & numbered · plotflow.io"
)


def _load_captions():
    data = json.loads(CAPTIONS_FILE.read_text())
    return data.get('captions', {}), data.get('_footer', '')


def _load_order_names():
    c = EDITIONS_FILE.read_text()
    d = json.loads(c[c.index('{'):c.rindex('}') + 1])
    order = d.get('shopOrder') or list(d['suits'].keys())
    names = {k: d['suits'][k].get('name', k) for k in d['suits']}
    return order, names


def export_cards() -> Path:
    """Export the editorial card library (assets/posts) as ready-to-post packs.

    Groups by suit (each card style paired with the suit's canon caption),
    plus the brand cards. Produces per-card packs + a grouped review board.
    """
    if not CARDS_DIR.exists() or not any(CARDS_DIR.glob('post-*.png')):
        raise SystemExit("No cards found. Run: python tools/gen_posts.py")

    captions, footer = _load_captions()
    order, names = _load_order_names()

    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_dir = EXPORTS / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    groups = []
    n = 0

    for key in order:
        cards = []
        caption = (captions.get(key, '') + footer).strip()
        for t in CARD_TYPES:
            src = CARDS_DIR / f'post-{key}-{t}.png'
            if not src.exists():
                continue
            n += 1
            slug = f'{n:02d}_{key}_{t}'
            pack = out_dir / slug
            pack.mkdir(exist_ok=True)
            shutil.copy2(src, pack / src.name)
            (pack / 'caption.txt').write_text(caption, encoding='utf-8')
            cards.append({'type': t, 'img_rel': f'{slug}/{src.name}',
                          'caption': caption, 'file': src.name})
        if cards:
            groups.append({'key': key, 'name': names.get(key, key), 'cards': cards})

    # brand cards
    brand_cards = []
    brand_caption = (BRAND_CAPTION + footer).strip()
    for variant in ('dark', 'light'):
        src = CARDS_DIR / f'post-brand-{variant}.png'
        if not src.exists():
            continue
        n += 1
        slug = f'{n:02d}_brand_{variant}'
        pack = out_dir / slug
        pack.mkdir(exist_ok=True)
        shutil.copy2(src, pack / src.name)
        (pack / 'caption.txt').write_text(brand_caption, encoding='utf-8')
        brand_cards.append({'type': f'brand · {variant}', 'img_rel': f'{slug}/{src.name}',
                            'caption': brand_caption, 'file': src.name})
    if brand_cards:
        groups.append({'key': 'brand', 'name': 'Brand / Studio', 'cards': brand_cards})

    (out_dir / 'index.html').write_text(_render_card_board(groups, stamp, n), encoding='utf-8')
    print(f"✓ Exported {n} cards across {len(groups)} groups → {out_dir}")
    print(f"\n📋 Open the review board:\n   {out_dir / 'index.html'}")
    return out_dir


def _render_card_board(groups, stamp, total):
    def esc(s):
        return (s.replace('&', '&amp;').replace('<', '&lt;')
                 .replace('>', '&gt;').replace('"', '&quot;'))

    sections = []
    for g in groups:
        cards_html = []
        for c in g['cards']:
            cards_html.append(f"""
        <article class="card">
          <div class="media"><img src="{c['img_rel']}" alt=""></div>
          <div class="body">
            <span class="badge">{esc(c['type'])}</span>
            <textarea readonly rows="10">{esc(c['caption'])}</textarea>
            <div class="actions">
              <button onclick="copyCap(this)">Copy caption</button>
              <span class="file">{esc(c['file'])}</span>
            </div>
          </div>
        </article>""")
        sections.append(f"""
      <section class="group">
        <h2>{esc(g['name'])} <span class="ct">{len(g['cards'])} cards</span></h2>
        <div class="grid">{''.join(cards_html)}</div>
      </section>""")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PLOTFLOW · Card board {stamp}</title>
<style>
  :root {{ --bristol:#f6f3ec; --ink:#15160f; --red:#e8351f; --dim:#43463e; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bristol); color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; }}
  header {{ padding:24px 20px; border-bottom:1px solid #ddd; position:sticky; top:0;
    background:var(--bristol); z-index:2; }}
  header h1 {{ margin:0; font-size:20px; }}
  header p {{ margin:4px 0 0; color:var(--dim); font-size:13px; }}
  .group {{ padding:8px 20px 28px; max-width:1500px; margin:0 auto; }}
  .group h2 {{ font-size:16px; text-transform:uppercase; letter-spacing:.06em;
    border-bottom:2px solid var(--red); padding-bottom:6px; }}
  .group h2 .ct {{ color:var(--dim); font-weight:400; font-size:12px; letter-spacing:0; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); gap:18px; margin-top:16px; }}
  .card {{ background:#fff; border:1px solid #e4e0d6; border-radius:10px; overflow:hidden;
    display:flex; flex-direction:column; }}
  .media {{ background:var(--bristol); }}
  .media img {{ width:100%; display:block; }}
  .body {{ padding:12px; display:flex; flex-direction:column; gap:8px; }}
  .badge {{ align-self:flex-start; background:var(--dim); color:#fff; font-size:11px;
    padding:3px 9px; border-radius:20px; text-transform:uppercase; letter-spacing:.04em; }}
  textarea {{ width:100%; border:1px solid #e4e0d6; border-radius:6px; padding:10px;
    font-size:12px; line-height:1.5; resize:vertical; font-family:inherit; background:#fbfaf6; }}
  .actions {{ display:flex; align-items:center; gap:10px; }}
  button {{ background:var(--red); color:#fff; border:0; border-radius:6px; padding:9px 14px;
    font-weight:600; cursor:pointer; font-size:13px; }}
  button.ok {{ background:#2e7d32; }}
  .file {{ font-size:11px; color:var(--dim); word-break:break-all; }}
</style></head>
<body>
  <header>
    <h1>PLOTFLOW* · Card board</h1>
    <p>{total} cards across {len(groups)} groups. Copy the caption, save the card, post via the Instagram app. Batch {stamp}.</p>
  </header>
  {''.join(sections)}
  <script>
    function copyCap(btn) {{
      const ta = btn.closest('.card').querySelector('textarea');
      navigator.clipboard.writeText(ta.value).then(() => {{
        const t = btn.textContent; btn.textContent = 'Copied ✓'; btn.classList.add('ok');
        setTimeout(() => {{ btn.textContent = t; btn.classList.remove('ok'); }}, 1500);
      }});
    }}
  </script>
</body></html>"""


def main():
    import argparse
    p = argparse.ArgumentParser(description='Export ready-to-post packs')
    p.add_argument('--queue', action='store_true',
                   help='export the old scheduler queue (still+video) instead of the card library')
    p.add_argument('--all', action='store_true', help='(queue mode) include posted/failed too')
    args = p.parse_args()
    if args.queue:
        export_queue(only_queued=not args.all)
    else:
        export_cards()


if __name__ == '__main__':
    main()
