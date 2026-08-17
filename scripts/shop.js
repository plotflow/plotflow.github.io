/* ============================================================
   PLOTFLOW · Study archive
   Builds the console's study list from window.PLOTFLOW
   (data/editions.js): one row per study with stats computed from
   its stroke program. The Universal-Century sheets are fan works,
   displayed only — commercial work goes through commissions.
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
      '<a class="thumb" href="' + href + '" aria-label="' + s.name + ' study record">' +
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
      '<div class="act"><span class="study">Study · not for sale</span>' +
        '<a class="rec" href="' + href + '">Open record →</a></div>';
    grid.appendChild(row);
  });

  // "▶ Plot" hands the study to the hero plotter (button sits inside the record link).
  grid.addEventListener('click', function (e) {
    var b = e.target.closest('[data-plot]');
    if (!b) return;
    e.preventDefault();
    if (window.PlotflowPlotter) window.PlotflowPlotter.load(b.dataset.plot);
    var feature = document.getElementById('feature');
    if (feature) feature.scrollIntoView({ behavior: 'smooth' });
  });
})();
