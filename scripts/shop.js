/* ============================================================
   PLOTFLOW · Study archive
   Builds the console's study list from window.PLOTFLOW
   (data/editions.js): one row per study with stats computed from
   its stroke program. The Universal-Century sheets are fan works,
   displayed only: commercial work goes through commissions.
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

  ORDER.forEach(function (key, i) {
    var s = SUITS[key]; if (!s) return;
    var t = stats(s.d), p = Math.max(t.bb[2], t.bb[3]) * 0.05;
    var href = 'product.html?id=' + encodeURIComponent(key);
    var plate = document.createElement('article');
    plate.className = 'plate';
    plate.dataset.key = key;
    plate.innerHTML =
      '<a class="pl-sheet" href="' + href + '">' +
        '<span class="pl-no">' + String(i + 1).padStart(2, '0') + '</span>' +
        '<span class="pl-code">' + s.code + '</span>' +
        '<svg viewBox="' + (t.bb[0] - p) + ' ' + (t.bb[1] - p) + ' ' +
          (t.bb[2] + 2 * p) + ' ' + (t.bb[3] + 2 * p) + '" preserveAspectRatio="xMidYMid meet">' +
          '<path d="' + s.d + '"/></svg>' +
        '<button class="pl-plot" data-plot="' + key + '" aria-label="Plot ' + s.name + '">▶&#xFE0E; Plot this sheet</button>' +
      '</a>' +
      '<a class="pl-name" href="' + href + '">' + s.name +
        '<span class="jp">' + s.jp + '</span></a>' +
      '<div class="pl-stats">' +
        '<span><label>Ink</label>' + t.ink.toFixed(1) + ' m</span>' +
        '<span><label>Strokes</label>' + t.strokes.toLocaleString() + '</span>' +
        '<span><label>Plot</label>' + fmt(t.min) + '</span>' +
      '</div>' +
      '<div class="pl-foot">Study · not for sale</div>';
    grid.appendChild(plate);
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
