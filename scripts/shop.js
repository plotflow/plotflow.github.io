/* ============================================================
   PLOTFLOW · Shop grid
   Builds edition cards from window.PLOTFLOW (data/editions.js).
   The "▶ Plot" button hands the suit to the hero plotter.
   ============================================================ */
(function () {
  var P = window.PLOTFLOW || {};
  var SUITS = P.suits || {};
  var ORDER = P.shopOrder || Object.keys(SUITS);
  var grid = document.getElementById('grid');
  if (!grid) return;

  var STAR = '<svg viewBox="0 0 100 100"><line x1="50" y1="6" x2="50" y2="94"/><line x1="6" y1="50" x2="94" y2="50"/><line x1="19" y1="19" x2="81" y2="81"/><line x1="81" y1="19" x2="19" y2="81"/></svg>';

  ORDER.forEach(function (key, i) {
    var s = SUITS[key]; if (!s) return;
    var card = document.createElement('article');
    card.className = 'card';
    var no = '№ PF-0' + (10 + i);
    card.innerHTML =
      '<div class="cover">' +
        '<div class="art"><svg viewBox="0 0 ' + s.w + ' ' + s.h + '" preserveAspectRatio="xMidYMid meet">' +
          '<path d="' + s.d + '" fill="none" stroke="currentColor" stroke-width=".7" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/></svg></div>' +
        '<div class="grain"></div><div class="ht"></div>' +
        '<div class="top"><span class="tiny">PLOTFLOW*</span><span class="tiny num">' + no + '</span></div>' +
        '<div class="name">' + s.name + '</div>' +
        '<div class="jp">' + s.jp + '</div>' +
        '<span class="ast star">' + STAR + '</span>' +
        '<div class="foot"><span class="tiny">' + s.code + '</span><span class="tiny">マシンドロー</span></div>' +
        '<button class="plotbtn" data-plot="' + key + '">▶︎ Plot</button>' +
      '</div>' +
      '<div class="buy"><div><div class="ed">' + s.edition + '</div><div class="t">' + s.code + ' ' + s.name + '</div></div>' +
        '<div style="display:flex;align-items:center"><span class="pr">' + s.price + '</span><button class="acq" data-acq="' + key + '">Acquire</button></div></div>';
    grid.appendChild(card);

    // Crop the viewBox to the suit's actual bounding box (+ padding) so every
    // edition fills its cover at a consistent scale, instead of being
    // letterboxed inside the mostly-empty original canvas.
    var svg = card.querySelector('.art svg');
    var path = card.querySelector('.art path');
    try {
      var bb = path.getBBox();
      var pad = Math.max(bb.width, bb.height) * 0.06;
      svg.setAttribute('viewBox',
        (bb.x - pad) + ' ' + (bb.y - pad) + ' ' +
        (bb.width + pad * 2) + ' ' + (bb.height + pad * 2));
    } catch (e) { /* getBBox unavailable — keep full-canvas viewBox */ }
  });

  grid.addEventListener('click', function (e) {
    var b = e.target.closest('[data-plot]');
    if (!b) return;
    if (window.PlotflowPlotter) window.PlotflowPlotter.load(b.dataset.plot);
    var feature = document.getElementById('feature');
    if (feature) feature.scrollIntoView({ behavior: 'smooth' });
  });
})();
