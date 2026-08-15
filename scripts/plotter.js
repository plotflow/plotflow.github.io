/* ============================================================
   PLOTFLOW · Live Plot component
   Progressively strokes a suit's path onto a <canvas> the way an
   AxiDraw would — walking the geometry with getPointAtLength and
   lifting the pen at subpath breaks — with a moving pen head + HUD.
   (A CSS stroke-dashoffset reveal is unreliable here: each suit's
   path has thousands of M-command subpaths, which the dash trick
   renders all at once.)
   Depends on: window.PLOTFLOW (data/editions.js)
   Exposes:    window.PlotflowPlotter.load(key)
   ============================================================ */
(function () {
  var DATA = (window.PLOTFLOW && window.PLOTFLOW.suits) || {};
  var ORDER = (window.PLOTFLOW && window.PLOTFLOW.plotterOrder) || Object.keys(DATA);

  var $ = function (id) { return document.getElementById(id); };
  var stage = $('stage'), ppath = $('ppath'), pen = $('pen'), penC = $('pen-c'), penX = $('pen-x');
  var canvas = $('pcanvas');
  if (!stage || !ppath || !canvas) return; // plotter markup not on this page
  var ctx = canvas.getContext('2d');

  var pbar = $('pbar'), pct = $('pct'), cx = $('cx'), cy = $('cy');
  var ink = $('ink'), inktot = $('inktot'), elapsed = $('elapsed'), total = $('total');
  var bed = $('bed'), bedlabel = $('bedlabel'), selSuit = $('suit'), playBtn = $('play'), replay = $('replay');

  var FEED = 1100;         // mm/min pen-down draw speed, shown in HUD
  var TRAVEL_FEED = 6600;  // mm/min pen-up travel (the carriage moves much faster between strokes)
  var LIFT_S = 0.10;       // seconds per pen lift+lower cycle (servo up + down)
  // Plot time = draw + pen-up travel + lift cycles — tuned against PlotGrid
  // actuals (~0.45 s/stroke incl. overhead), not just ink-length ÷ feed.
  var BASE = 30;     // seconds the simulation runs at 1x watch speed —
                     // the machine-speed multiplier shown in the dock is
                     // derived from the real plot time (≈ x45–x60)
  var INK = '#e8351f';
  var cur, len = 1, drawn = 0, painted = 0, playing = true, speed = 1, mmPerUnit = 1, totalMin = 1;
  var termBody = $('pfTermBody');           // command journal (homepage only)
  var polys = [], strokes = [], termIdx = -1;   // parsed geometry + journal cursor
  var vb = { x: 0, y: 0, w: 1, h: 1 };
  var tf = { s: 1, ox: 0, oy: 0, dpr: 1, ready: false };
  var prevPt = null;

  if (selSuit) {
    ORDER.forEach(function (k) {
      var o = document.createElement('option');
      o.value = k; o.textContent = DATA[k].name + ' · ' + DATA[k].code;
      selSuit.appendChild(o);
    });
  }

  function fmt(min) {
    var s = Math.max(0, Math.round(min * 60));
    return String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0');
  }

  // Walk the raw path string once: pen-down length, pen-up travel length, and
  // lift count (each M after the first is a pen lift + travel + pen lower).
  function pathStats(d) {
    var draw = 0, travel = 0, lifts = 0, px = null, py = null, pen = false;
    var re = /([ML])\s*(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)/g, m;
    while ((m = re.exec(d)) !== null) {
      var x = +m[2], y = +m[3];
      if (m[1] === 'M') {
        if (px !== null) { travel += Math.hypot(x - px, y - py); lifts++; }
        pen = false;
      } else if (px !== null) {
        draw += Math.hypot(x - px, y - py);
      }
      px = x; py = y;
    }
    return { draw: draw, travel: travel, lifts: lifts };
  }

  // Map a point in suit/user coordinates to canvas device pixels, matching the
  // SVG stage's preserveAspectRatio="xMidYMid meet" so the pen lines up.
  function mapX(ux) { return (tf.ox + (ux - vb.x) * tf.s) * tf.dpr; }
  function mapY(uy) { return (tf.oy + (uy - vb.y) * tf.s) * tf.dpr; }

  // Size the canvas backing store to the bed and (re)derive the meet transform.
  // Resizing the backing store clears it, so this also resets the ink.
  function resetCanvas() {
    var w = canvas.clientWidth, h = canvas.clientHeight;
    tf.ready = w > 0 && h > 0;
    if (!tf.ready) return;
    tf.dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(w * tf.dpr);
    canvas.height = Math.round(h * tf.dpr);
    tf.s = Math.min(w / vb.w, h / vb.h);
    tf.ox = (w - vb.w * tf.s) / 2;
    tf.oy = (h - vb.h * tf.s) / 2;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = INK;
    ctx.lineWidth = Math.max(1, 1.2 * tf.dpr);
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    painted = 0;
    prevPt = null;
  }

  // Stroke ink from `painted` up to `target` length, sampling the path and
  // lifting the pen (moveTo) wherever the geometry jumps between subpaths.
  function paintTo(target) {
    if (!tf.ready || target <= painted) return;
    var step = Math.max(0.5, 2 / tf.s);   // ~2 CSS px between samples
    var liftSq = (step * 3) * (step * 3); // a jump this big ⇒ pen lift
    ctx.beginPath();
    if (prevPt) ctx.moveTo(mapX(prevPt.x), mapY(prevPt.y));
    var L = painted;
    while (L < target) {
      L = Math.min(target, L + step);
      var p = ppath.getPointAtLength(L);
      if (!prevPt) { ctx.moveTo(mapX(p.x), mapY(p.y)); }
      else {
        var dx = p.x - prevPt.x, dy = p.y - prevPt.y;
        if (dx * dx + dy * dy > liftSq) ctx.moveTo(mapX(p.x), mapY(p.y));
        else ctx.lineTo(mapX(p.x), mapY(p.y));
      }
      prevPt = p;
    }
    ctx.stroke();
    painted = target;
  }

  function load(key) {
    cur = DATA[key]; if (!cur) return;
    if (selSuit) selSuit.value = key;
    ppath.setAttribute('d', cur.d);

    // Crop the stage to the suit's bounding box (+ padding) so every suit is
    // drawn large and centred on the same sheet, instead of being letterboxed
    // inside the mostly-empty original canvas. The bed keeps its fixed CSS
    // shape so the paper is consistent across all editions.
    vb = { x: 0, y: 0, w: cur.w, h: cur.h };
    try {
      var bb = ppath.getBBox();
      var pad = Math.max(bb.width, bb.height) * 0.06;
      vb = { x: bb.x - pad, y: bb.y - pad, w: bb.width + pad * 2, h: bb.height + pad * 2 };
    } catch (e) { /* getBBox unavailable — keep full-canvas viewBox */ }
    stage.setAttribute('viewBox', vb.x + ' ' + vb.y + ' ' + vb.w + ' ' + vb.h);

    len = ppath.getTotalLength(); if (!len || !isFinite(len)) len = 1;
    var md = Math.max(vb.w, vb.h);
    mmPerUnit = 420 / md;                 // longest side ≈ 420mm
    // parse the raw path once: polylines for fast full-draw, stroke table
    // (start/end/len/cumulative draw length) for the command journal
    polys = []; strokes = []; termIdx = -1;
    if (termBody) termBody.textContent = '';
    (function () {
      var re = /([ML])\s*(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)/g, m, curP = null;
      while ((m = re.exec(cur.d)) !== null) {
        var x = +m[2], y = +m[3];
        if (m[1] === 'M') { curP = [[x, y]]; polys.push(curP); }
        else if (curP) curP.push([x, y]);
      }
      var cum = 0;
      for (var i = 0; i < polys.length; i++) {
        var pl = polys[i], L = 0;
        for (var j = 0; j < pl.length - 1; j++)
          L += Math.hypot(pl[j+1][0]-pl[j][0], pl[j+1][1]-pl[j][1]);
        cum += L;
        strokes.push({ sx: pl[0][0], sy: pl[0][1], len: L, cum: cum });
      }
    })();
    var st = pathStats(cur.d);
    totalMin = (st.draw * mmPerUnit) / FEED
             + (st.travel * mmPerUnit) / TRAVEL_FEED
             + (st.lifts * LIFT_S) / 60;
    updateSimX();
    penC.setAttribute('r', md * 0.014);
    penX.setAttribute('d', 'M ' + (-md * 0.032) + ' 0 H ' + (md * 0.032) + ' M 0 ' + (-md * 0.032) + ' V ' + (md * 0.032));
    pen.setAttribute('opacity', '0');
    if (inktot) inktot.textContent = (len * mmPerUnit / 1000).toFixed(2);
    if (total) total.textContent = fmt(totalMin);
    if (bedlabel) bedlabel.textContent = 'BED 01 · ' + cur.code;
    drawn = 0; playing = true; last = null;   // reset the clock → always start from a blank sheet
    resetCanvas();
    if (replay) replay.classList.remove('show');
    if (playBtn) playBtn.textContent = 'Pause';
    render();
  }

  function render() {
    if (!tf.ready) resetCanvas();   // self-heal if the bed wasn't laid out yet
    var p = drawn / len;
    paintTo(drawn);
    updateJournal();
    if (pbar) pbar.style.width = (p * 100) + '%';
    if (pct) pct.textContent = Math.round(p * 100);
    if (ink) ink.textContent = (drawn * mmPerUnit / 1000).toFixed(2);
    if (elapsed) elapsed.textContent = fmt(totalMin * p);
    if (drawn > 0 && drawn < len) {
      var pt = ppath.getPointAtLength(drawn);
      pen.setAttribute('transform', 'translate(' + pt.x + ' ' + pt.y + ')');
      pen.setAttribute('opacity', '1');
      if (cx) cx.textContent = Math.round(pt.x * mmPerUnit);
      if (cy) cy.textContent = Math.round(pt.y * mmPerUnit);
    } else if (drawn >= len) {
      pen.setAttribute('opacity', '0');
    }
  }

  // Draw every stroke directly from the parsed polylines in one canvas pass —
  // used by Skip and end-state refits, where sampling the whole path with
  // getPointAtLength would stall the frame for ~a second.
  function fastPaintAll() {
    if (!tf.ready) resetCanvas();
    if (!tf.ready) return;
    ctx.beginPath();
    for (var i = 0; i < polys.length; i++) {
      var pl = polys[i];
      ctx.moveTo(mapX(pl[0][0]), mapY(pl[0][1]));
      for (var j = 1; j < pl.length; j++) ctx.lineTo(mapX(pl[j][0]), mapY(pl[j][1]));
    }
    ctx.stroke();
    painted = len;
    var lastP = polys.length ? polys[polys.length-1][polys[polys.length-1].length-1] : null;
    prevPt = lastP ? { x: lastP[0], y: lastP[1] } : null;
  }

  // Command journal — emit pyaxidraw-style lines for the strokes just drawn.
  function pad4(n) { return String(n).padStart(4, '0'); }
  function updateJournal() {
    if (!termBody || !strokes.length) return;
    var lo = 0, hi = strokes.length - 1, idx = 0;   // first stroke with cum >= drawn
    while (lo <= hi) { var mid = (lo + hi) >> 1;
      if (strokes[mid].cum < drawn) { lo = mid + 1; } else { idx = mid; hi = mid - 1; } }
    if (drawn >= len) idx = strokes.length - 1;
    if (idx === termIdx) return;
    termIdx = idx;
    var out = [], from = Math.max(0, idx - 2);
    for (var k = from; k <= idx; k++) {
      var st2 = strokes[k];
      out.push('ad.penup()                       z=+1');
      out.push('ad.moveto(' + (st2.sx * mmPerUnit).toFixed(2) + ', ' + (st2.sy * mmPerUnit).toFixed(2) + ')     travel');
      out.push('ad.pendown()                     z=-1 · nib 0.30 mm');
      out.push('ad.lineto(…)                     stroke ' + pad4(k + 1) + '/' + strokes.length + ' · ' + (st2.len * mmPerUnit).toFixed(1) + ' mm');
    }
    out.push(drawn >= len ? 'ad.penup()                       z=+1 · job complete' : '_');
    termBody.textContent = out.join('\n');
  }

  // Re-fit + repaint the current progress when the bed changes size.
  function refit() { resetCanvas(); if (drawn >= len) fastPaintAll(); else paintTo(drawn); }
  window.addEventListener('resize', refit);

  function restart() {
    drawn = 0; playing = true; last = null;
    resetCanvas(); render();
    if (replay) replay.classList.remove('show');
    if (playBtn) playBtn.textContent = 'Pause';
  }

  // honest speed disclosure: the sim runs the real plot in BASE/speed seconds
  function updateSimX() {
    var el = $('simx');
    if (!el || !totalMin) return;
    var x = Math.round((totalMin * 60) / (BASE / speed));
    el.textContent = 'SIM \u2248 \u00d7' + x + ' machine speed';
  }

  var last = null;
  function frame(t) {
    if (last == null) last = t;
    var dt = (t - last) / 1000; last = t;
    if (playing) {
      drawn = Math.min(len, drawn + (len / (BASE / speed)) * dt);
      render();
      if (drawn >= len) {
        playing = false;
        if (replay) replay.classList.add('show');
        if (playBtn) playBtn.textContent = 'Replay';
      }
    }
    requestAnimationFrame(frame);
  }

  function toggle() {
    if (drawn >= len) { restart(); return; }
    playing = !playing;
    if (playBtn) playBtn.textContent = playing ? 'Pause' : 'Resume';
    if (replay) replay.classList.remove('show');
  }
  if (playBtn) playBtn.onclick = toggle;
  if ($('restart')) $('restart').onclick = restart;
  if ($('skip')) $('skip').onclick = function () { drawn = len; playing = false; fastPaintAll(); render(); if (replay) replay.classList.add('show'); if (playBtn) playBtn.textContent = 'Replay'; };
  if ($('speed')) $('speed').addEventListener('click', function (e) {
    var b = e.target.closest('button'); if (!b) return;
    [].forEach.call(e.currentTarget.children, function (x) { x.classList.remove('on'); });
    b.classList.add('on'); speed = parseFloat(b.dataset.s);
    updateSimX();
  });
  if (selSuit) selSuit.addEventListener('change', function (e) { load(e.target.value); });
  if (replay) replay.addEventListener('click', restart);

  // public API (used by the shop "▶ Plot" buttons)
  window.PlotflowPlotter = { load: load };

  load(ORDER[0]);
  requestAnimationFrame(frame);
})();
