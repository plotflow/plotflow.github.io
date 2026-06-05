# PLOTFLOW

**Independent pen-plotter studio.** Universal-Century mobile suits, rebuilt as a single unbroken line and drawn in ink by machine.

一筆書き — *hitofudegaki*, "one continuous line."

🌐 **[plotflow.io](https://plotflow.io)**

---

## What it is

PlotFlow reimagines each mobile suit as one continuous vector path — no pen lifts, no breaks — and traces it in technical pen on archival paper with an AxiDraw plotter. Nothing is printed. Every impression is *drawn*, so each carries the minor variation of the medium; editions are limited, made to order, signed, and numbered.

This repository is the PlotFlow homepage — a no-build static site (plain HTML/CSS/JS, no framework, no bundler) hosted on GitHub Pages. Its centerpiece is an interactive **Live Plot** that animates a suit being drawn line-by-line by a virtual plotter, alongside the shop of current editions.

## The work

- **Drawn, not printed** — technical pen on 300gsm archival stock, never a print
- **One continuous line** — each suit is a single unbroken path
- **Limited editions** — made to order, signed and numbered
- Variation in line and ink is a feature of the medium, not a flaw

## Process

1. **Vectorize** (ベクター化) — the suit is rebuilt as one continuous vector path
2. **Plot** (作画) — an AxiDraw traces it in ink; a single A1 can run for hours
3. **Finish** (仕上げ) — inspected, signed, and numbered

---

## Run locally

No build step or dependencies — the edition data is inlined as a script.

```bash
python3 -m http.server 8000
# visit http://localhost:8000
```

## Deploy

Hosted on GitHub Pages ("deploy from a branch", root). Pushing to `main` deploys automatically.

```bash
git add -A && git commit -m "update site" && git push
```

## Structure

```
├─ index.html           # homepage + Live Plot hero
├─ styles/              # tokens.css (design tokens) + styles.css
├─ scripts/             # plotter.js (Live Plot) + shop.js (edition grid)
├─ data/editions.js     # SVG path data for every edition (auto-generated)
├─ assets/plots/        # source SVG art
├─ tools/               # Python scripts to regenerate data from the SVGs
├─ CNAME                # custom domain (plotflow.io)
└─ .nojekyll            # disables Jekyll processing
```

**To add or change an edition:** drop a clean SVG into `assets/plots/`, register it in `tools/build_data.py`, then run that script to regenerate `data/editions.js`. The shop grid and Live Plot pick it up automatically.

---

<sub>© 2026 PLOTFLOW* — plotted in the U.S.A. · 一筆書き · one continuous line</sub>
