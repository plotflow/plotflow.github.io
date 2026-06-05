# PLOTFLOW — plotflow.io

Static website for PlotFlow, an avant-garde pen-plotter art house. No build step, no framework — plain HTML/CSS/JS served via GitHub Pages.

## Run locally

```bash
python3 -m http.server 8000
# visit http://localhost:8000
```

## Deploy

Push to `main`. GitHub Pages serves from the repo root automatically.

```bash
git add -A && git commit -m "update site" && git push
```

## Structure

```
├─ index.html           # homepage
├─ styles/              # tokens.css (design tokens) + styles.css
├─ scripts/             # plotter.js (live plot) + shop.js (edition grid)
├─ data/editions.js     # SVG path data for all editions (auto-generated)
├─ assets/plots/        # source SVG files
├─ tools/               # Python scripts to regenerate data from SVGs
├─ CNAME                # custom domain config (plotflow.io)
└─ .nojekyll            # disables Jekyll processing
```
