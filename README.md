# PLOTFLOW · design system + homepage

Avant-garde pen-plotter art house. Muted ground, bold white grotesque, Japanese, halftone + asterisk, with an interactive **Live Plot** hero that draws each mobile-suit plot as one continuous line.

## Quick start

No build step or dependencies — it's static HTML/CSS/JS with the data inlined in a script.

```bash
# just open it…
open index.html                      # works from file://

# …or serve it (recommended)
python3 -m http.server 8000          # then visit http://localhost:8000
```

`preview.html` is a single-file, fully-inlined version of the same page (handy for a quick look or to drop into a CMS).

## Structure

```
plotflow-design-system/
├─ index.html            # the homepage (links the css + scripts below)
├─ preview.html          # single-file build of the same page
├─ tokens.json           # machine-readable design tokens
├─ styles/
│  ├─ tokens.css         # ← colors, fonts, spacing. EDIT BRAND HERE.
│  └─ styles.css         # base + all component styles
├─ scripts/
│  ├─ plotter.js         # Live Plot component (window.PlotflowPlotter)
│  └─ shop.js            # builds the editions grid
├─ data/
│  └─ editions.js        # window.PLOTFLOW = { suits, orders }  (AUTO-GENERATED)
├─ assets/plots/         # the 8 recolorable plot SVGs (source art)
├─ tools/
│  ├─ prep_plots.py      # normalize raw plotter.vision exports → assets/plots
│  └─ build_data.py      # regenerate data/editions.js from assets/plots
└─ docs/
   └─ DESIGN_SYSTEM.md   # tokens, components, rules — start here
```

## Common edits

**Change the palette / type** → edit `styles/tokens.css` (and mirror in `tokens.json`). Everything reads those variables.

**Add or change an edition**
1. Drop the new clean SVG in `assets/plots/` (run `python tools/prep_plots.py raw/` if it's a fresh plotter.vision export).
2. Add a row to `META` (and the order arrays) in `tools/build_data.py`.
3. `python tools/build_data.py` → regenerates `data/editions.js`. Done; the shop + plotter pick it up.

**Plot legibility** — keep the cardinal rule: show plots large with a thin stroke; don't scale a plot up to fill a small card (it fuses the lines). Stroke widths are set in CSS (`.hero #ppath`, `.card .cover .art path`).

See `docs/DESIGN_SYSTEM.md` for the full spec and `CLAUDE.md` for working in this repo with Claude Code.
