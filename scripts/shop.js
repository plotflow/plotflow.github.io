/* ============================================================
   PLOTFLOW · Edition queue (shop)
   Builds the console's job list from window.PLOTFLOW
   (data/editions.js): one row per edition with stats computed
   from its stroke program, an availability meter fed by
   scripts/stock.js, and Acquire / Open record / ▶ Plot actions.
   ============================================================ */
(function () {
  var P = window.PLOTFLOW || {};
  var SUITS = P.suits || {};
  var ORDER = P.shopOrder || Object.keys(SUITS);
  var grid = document.getElementById('grid');
  if (!grid) return;

  // Same physical model as the Live Plot (plotter.js): pen-down feed,
  // pen-up travel feed, and a fixed cost per pen lift.
  var FEED = 1100, TRAVEL_FEED = 6600, LIFT_S = 0.10;

  function stats(d) {
    var re = /([ML])\s*(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)/g, m;
    var px = null, py = null, draw = 0, travel = 0, lifts = 0;
    var minx = 1e9, miny = 1e9, maxx = -1e9, maxy = -1e9;
    while ((m = re.exec(d)) !== null) {
      var x = +m[2], y = +m[3];
      if (x < minx) minx = x; if (x > maxx) maxx = x;
      if (y < miny) miny = y; if (y > maxy) maxy = y;
      if (m[1] === 'M') { if (px !== null) { travel += Math.hypot(x - px, y - py); lifts++; } }
      else if (px !== null) { draw += Math.hypot(x - px, y - py); }
      px = x; py = y;
    }
    var mm = 420 / Math.max(maxx - minx, maxy - miny);   // longest side ≈ 420mm on sheet
    return {
      ink: draw * mm / 1000,
      min: (draw * mm) / FEED + (travel * mm) / TRAVEL_FEED + (lifts * LIFT_S) / 60,
      strokes: lifts + 1,
      bb: [minx, miny, maxx - minx, maxy - miny]
    };
  }

  function fmt(min) {
    var s = Math.round(min * 60);
    return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
  }

  ORDER.forEach(function (key) {
    var s = SUITS[key]; if (!s) return;
    var t = stats(s.d), p = Math.max(t.bb[2], t.bb[3]) * 0.05;
    var href = 'product.html?id=' + encodeURIComponent(key);
    var row = document.createElement('article');
    row.className = 'qrow';
    row.dataset.key = key;
    row.innerHTML =
      '<a class="thumb" href="' + href + '" aria-label="' + s.name + ' record">' +
        '<svg viewBox="' + (t.bb[0] - p) + ' ' + (t.bb[1] - p) + ' ' +
          (t.bb[2] + 2 * p) + ' ' + (t.bb[3] + 2 * p) + '" preserveAspectRatio="xMidYMid meet">' +
          '<path d="' + s.d + '"/></svg>' +
        '<button class="qplot" data-plot="' + key + '" aria-label="Plot ' + s.name + '">▶︎ Plot</button>' +
      '</a>' +
      '<div class="des"><span class="code">№ ' + s.code + '</span>' +
        '<a class="nm" href="' + href + '">' + s.name + '</a>' +
        '<span class="jp">' + s.jp + '</span></div>' +
      '<div class="qstat"><label>Ink</label>' + t.ink.toFixed(1) + ' m</div>' +
      '<div class="qstat"><label>Strokes</label>' + t.strokes.toLocaleString() + '</div>' +
      '<div class="qstat"><label>Plot time</label>' + fmt(t.min) + '</div>' +
      '<div class="avail"><span class="n" data-stock-n>EDITION OF 25</span>' +
        '<div class="m" hidden data-stock-m><b></b></div></div>' +
      '<div class="act"><div class="l1"><span class="pr">' + s.price + '</span>' +
        '<button class="acq" data-acq="' + key + '" data-color="black">Acquire</button></div>' +
        '<a class="rec" href="' + href + '">Open record →</a></div>';
    grid.appendChild(row);
  });

  // Availability meters — filled once live stock loads (fails silent:
  // without the endpoint the rows keep the static "EDITION OF 25" label).
  if (window.PlotflowStock) {
    window.PlotflowStock.ready(function (counts) {
      if (!counts) return;
      var SIZE = window.PlotflowStock.size;
      ORDER.forEach(function (key) {
        var row = grid.querySelector('.qrow[data-key="' + key + '"]');
        if (!row || typeof counts[key] !== 'number') return;
        var left = counts[key];
        var n = row.querySelector('[data-stock-n]');
        var m = row.querySelector('[data-stock-m]');
        var acq = row.querySelector('.acq');
        if (left <= 0) {
          row.classList.add('sold-out');
          if (n) { n.textContent = 'SOLD OUT'; n.classList.add('low'); }
          if (acq) { acq.textContent = 'Sold out'; acq.disabled = true; }
        } else {
          if (n) {
            n.textContent = left + ' / ' + SIZE + ' AVAILABLE';
            if (left <= 5) n.classList.add('low');
          }
          if (m) { m.hidden = false; m.querySelector('b').style.width = (left / SIZE * 100) + '%'; }
        }
      });
    });
  }

  // "▶ Plot" hands the suit to the hero plotter (button sits inside the record link).
  grid.addEventListener('click', function (e) {
    var b = e.target.closest('[data-plot]');
    if (!b) return;
    e.preventDefault();
    if (window.PlotflowPlotter) window.PlotflowPlotter.load(b.dataset.plot);
    var feature = document.getElementById('feature');
    if (feature) feature.scrollIntoView({ behavior: 'smooth' });
  });
})();
