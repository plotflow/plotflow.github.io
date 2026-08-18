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

  // Parse the stroke program into polylines once, for the hover animation.
  function polysOf(d) {
    var re = /([ML])\s*(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)/g, m, cur = null, out = [];
    while ((m = re.exec(d)) !== null) {
      var x = +m[2], y = +m[3];
      if (m[1] === 'M') { cur = [[x, y]]; out.push(cur); }
      else if (cur) cur.push([x, y]);
    }
    return out;
  }

  // Hovering a plate replays its stroke program inside the card: the canvas
  // draws the polylines in execution order, the way the machine lays them.
  var PLOT_MS = 2400, INK = '#e8351f';
  function attachHoverPlot(sheet, canvas, polys, vb) {
    var ctx = canvas.getContext('2d'), raf = null, tf = null, segs = 0;
    for (var i = 0; i < polys.length; i++) segs += Math.max(0, polys[i].length - 1);

    function setup() {
      var w = canvas.clientWidth, h = canvas.clientHeight;
      if (!w || !h) return false;
      var dpr = window.devicePixelRatio || 1;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      var sc = Math.min(w / vb.w, h / vb.h);
      tf = { s: sc * dpr, ox: ((w - vb.w * sc) / 2) * dpr, oy: ((h - vb.h * sc) / 2) * dpr };
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.strokeStyle = INK;
      ctx.lineWidth = Math.max(1, 0.85 * dpr);
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';
      return true;
    }
    function mx(x) { return tf.ox + (x - vb.x) * tf.s; }
    function my(y) { return tf.oy + (y - vb.y) * tf.s; }

    // Stroke every segment up to `upto`, in program order.
    function paint(upto) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.beginPath();
      var n = 0;
      for (var i = 0; i < polys.length && n < upto; i++) {
        var pl = polys[i];
        if (pl.length < 2) continue;
        ctx.moveTo(mx(pl[0][0]), my(pl[0][1]));
        for (var j = 1; j < pl.length && n < upto; j++, n++) ctx.lineTo(mx(pl[j][0]), my(pl[j][1]));
      }
      ctx.stroke();
    }

    function stop() {
      if (raf) { cancelAnimationFrame(raf); raf = null; }
      sheet.classList.remove('plotting');
      if (tf) ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    function start() {
      if (raf) return;
      if (!setup()) return;
      sheet.classList.add('plotting');
      var t0 = null;
      raf = requestAnimationFrame(function step(t) {
        if (t0 === null) t0 = t;
        var k = Math.min(1, (t - t0) / PLOT_MS);
        paint(Math.round(segs * k));
        if (k < 1) { raf = requestAnimationFrame(step); }
        else { raf = null; }   // finished: the drawn canvas stays until pointer-out
      });
    }

    sheet.addEventListener('pointerenter', function (e) {
      if (e.pointerType === 'touch') return;   // no hover on touch: leave the static plate
      start();
    });
    sheet.addEventListener('pointerleave', stop);
    sheet.addEventListener('focusin', start);
    sheet.addEventListener('focusout', stop);
  }

  ORDER.forEach(function (key, i) {
    var s = SUITS[key]; if (!s) return;
    var t = stats(s.d), p = Math.max(t.bb[2], t.bb[3]) * 0.05;
    var vb = { x: t.bb[0] - p, y: t.bb[1] - p, w: t.bb[2] + 2 * p, h: t.bb[3] + 2 * p };
    var href = 'product.html?id=' + encodeURIComponent(key);
    var plate = document.createElement('article');
    plate.className = 'plate';
    plate.dataset.key = key;
    plate.innerHTML =
      '<a class="pl-sheet" href="' + href + '" aria-label="' + s.name + ' study record">' +
        '<span class="pl-no">' + String(i + 1).padStart(2, '0') + '</span>' +
        '<span class="pl-code">' + s.code + '</span>' +
        '<svg viewBox="' + vb.x + ' ' + vb.y + ' ' + vb.w + ' ' + vb.h + '" preserveAspectRatio="xMidYMid meet">' +
          '<path d="' + s.d + '"/></svg>' +
        '<canvas class="pl-canvas" aria-hidden="true"></canvas>' +
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
    attachHoverPlot(plate.querySelector('.pl-sheet'), plate.querySelector('.pl-canvas'),
                    polysOf(s.d), vb);
  });
})();
