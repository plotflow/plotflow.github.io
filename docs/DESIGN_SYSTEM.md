# PLOTFLOW — Design System

A small studio selling **pen-plotter (AxiDraw) line drawings of Universal-Century mobile suits** — each rebuilt as a single continuous line and drawn in red ink on archival paper, signed + numbered. *Plotted, not printed.* est. 2026.

Aesthetic: **washed/muted ground · bold white grotesque · Japanese · halftone + asterisk**, with an interactive **Live Plot** hero that draws the suit in front of you. This document is the source of truth for tokens, components, and rules. (`tokens.json` is the machine-readable mirror; `tokens.css` is what the site consumes.)

---

## 1. Brand

| | |
|---|---|
| **Name / wordmark** | `PLOTFLOW*` — always all-caps, **one color** (the `*` is the only red). Katakana: プロットフロー |
| **Tagline** | *Drawn, not printed.* |
| **Motto (JP)** | 一筆書き (*ichi-fude-gaki*, "single-stroke drawing") · "One continuous line" |
| **Marks** | est. 2026 · plotted in the U.S.A. · signed + numbered |
| **Voice** | Confident, technical, a little cryptic. Machine-precise meets hand-made-scarce. Never corporate, never cute. |

## 2. Color tokens

Mostly **white-on-muted monochrome**, one warm red accent, paper for the sheet.

| Token | Hex | Use |
|---|---|---|
| `--white` | `#f5f4ef` | primary type / foreground |
| `--mute`  | `#c3c5b8` | secondary text on dark |
| `--dim`   | `#8f9184` | captions / tertiary |
| `--ink`   | `#15160f` | near-black ground (manifesto, footer), pen reticle |
| `--paper` | `#efe7d3` | the plotted sheet (bed) |
| `--red`   | `#e8351f` | **single accent** — pen ink + asterisk bug only |
| `--con1`  | `#5b5e54` | muted ground, light |
| `--con2`  | `#43463e` | muted ground, dark / page base |
| `--line`  | `rgba(245,244,239,.22)` | hairline borders |

**Rule:** red is an accent, not a fill. ~90% white/muted/ink, ~10% red.

## 3. Typography

- **One family for everything: Archivo** (grotesque). Display = 900, labels = 700, body = 500. Uppercase + tight tracking for display.
- **Noto Sans JP** for Japanese only.
- No serif, no condensed display. "Simple."

Scale: `display clamp(3rem,11vw,8rem)` · `h2 clamp(2rem,6vw,3.4rem)` · `lead 1rem` · `body 13px` · `label 10px/.14em` · `micro 8.5px/.16em`.

## 4. Motifs (the texture vocabulary)

- **Asterisk `*`** — 4-line SVG cross, usually red. The brand bug; trails the wordmark and section titles, floats as decoration.
- **Halftone** — white radial-dot pattern (`7px` grid) masked to a soft circle; ambient white "clouds."
- **Grain** — `feTurbulence` SVG, overlay/multiply, ~0.4 opacity, over muted grounds.
- **Scanlines** — 1px repeating horizontal lines, very low opacity.
- **Japanese** — short authentic phrases as accents (作品 works, 工程 process, vertical katakana suit nicknames). Never decorative gibberish.

## 5. The plots (artwork)

- Source: single-path line drawings (`assets/plots/*.svg`), `stroke="currentColor"`, `vector-effect:non-scaling-stroke`.
- **Recolor** by setting `color` on a parent. **Line weight** via CSS `stroke-width` (hero `1.1px`, covers `0.7px`).
- **Cardinal rule:** never scale a plot *up* to cram a small box — that fuses the lines. Show it **large with a thin stroke**. The hero is where detail reads; covers are small silhouettes.

## 6. Components

All markup lives in `index.html`; shop cards + plotter are populated by `scripts/`.

### Nav  `nav > .nav-in`
Sticky, translucent dark bar. `.brand` (wordmark, red `*`), `.nav-links`, `.cart`.

### Hero / Live Plot  `.hero#feature`
The centerpiece. Muted ground (`linear-gradient` + `radial-gradient`) + `.grain` + `.scan` + a `.halftone`.
- `.hero-head` — `h1` display wordmark + `//`-style `.sub`.
- `.stage-area > .bed` — the **paper sheet**; holds `#stage` (the SVG: `#ppath` + `#pen`) and the `.replay` overlay. **The bed must have a definite width** (`width:min(62%,640px)`) or it collapses.
- `.hud` — live readouts (progress, ink-m, plot-time, position), top-right.
- `.hero-jp` / `.hero-collab` / `.ast-bug` — the lower-left 一筆書き lockup, `[ LIVE PLOT* ]`, floating asterisk.
- `.pbar` + `.dock` — progress bar + controls (suit `select`, play/pause, restart, skip, speed segmented control).

### Manifesto  `.mani`
Ink ground, "Drawn, not printed." + a JP line + a short paragraph.

### Shop  `.shop#shop`
`.shop-head` ("THE WORK* / 作品") + `#grid` (filled by `shop.js`).
**Cover anatomy** (`.card .cover`): muted ground, `.art` (the plot, white), `.grain`, `.ht` (halftone), `.top` (PLOTFLOW* + №), `.name` (suit), vertical `.jp` nickname, red `.ast`, `.foot`, and a `.plotbtn` ("▶ Plot") that loads the suit into the hero. Below: `.buy` (edition, title, price, Acquire).

### Process  `.proc` — 3 steps (Vectorize / Plot / Finish) with JP labels.
### Footer  `footer` — huge wordmark, link columns, marks.

## 7. Data + behavior

- `data/editions.js` sets `window.PLOTFLOW = { suits, plotterOrder, shopOrder }`. Each suit: `{ name, code, jp, edition, price, file, w, h, d }` (`d` = the path).
- `scripts/plotter.js` → animates `#ppath` via `stroke-dashoffset`, moves `#pen` with `getPointAtLength`. Exposes `window.PlotflowPlotter.load(key)`. **Plot is hidden until drawing starts** (offset = full length on load/switch).
- `scripts/shop.js` → builds cards from `shopOrder`; `.plotbtn` calls the plotter + scrolls to `#feature`.

## 8. Responsive

- `--maxw: 1240px`. Grid 3→2→1 col. Nav links hide < 720px. Hero HUD hides < 820px.
- Hero bed is width-capped with `max-height` so it fits without overflow. Plots are SVG, so they scale cleanly.

## 9. Do / Don't

**Do:** keep the wordmark one color · red as a small accent · plots large + thin-lined · pair white grotesque with real Japanese · pile on micro-labels, asterisks, halftone, grain.

**Don't:** scale plots up inside small boxes (lines merge) · use serif/condensed display · add a second accent color · use gradients-as-decoration or rounded corners · use photography (the line plots are the only imagery).
