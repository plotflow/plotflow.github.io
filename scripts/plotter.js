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

  var FEED = 1100;   // mm/min, shown in HUD + used for plot-time
  var BASE = 22;     // seconds for a full plot at 1x speed
  var INK = '#e8351f';
  var cur, len = 1, drawn = 0, painted = 0, playing = true, speed = 1, mmPerUnit = 1, totalMin = 1;
  var vb = { x: 0, y: 0, w: 1, h: 1 };
  var tf = { s: 1, ox: 0, oy: 0, dpr: 1, ready: false };
  var prevPt = null;

  if (selSuit) {
    ORDER.forEach(function (k) {
      var o = document.createElement('option');
      o.value = k; o.textContent = DATA[k].name + ' — ' + DATA[k].code;
      selSuit.appendChild(o);
    });
  }

  function fmt(min) {
    var s = Math.max(0, Math.round(min * 60));
    return String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0');
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
    totalMin = (len * mmPerUnit) / FEED;
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

  // Re-fit + repaint the current progress when the bed changes size.
  function refit() { resetCanvas(); paintTo(drawn); }
  window.addEventListener('resize', refit);

  function restart() {
    drawn = 0; playing = true; last = null;
    resetCanvas(); render();
    if (replay) replay.classList.remove('show');
    if (playBtn) playBtn.textContent = 'Pause';
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
  if ($('skip')) $('skip').onclick = function () { drawn = len; playing = false; render(); if (replay) replay.classList.add('show'); if (playBtn) playBtn.textContent = 'Replay'; };
  if ($('speed')) $('speed').addEventListener('click', function (e) {
    var b = e.target.closest('button'); if (!b) return;
    [].forEach.call(e.currentTarget.children, function (x) { x.classList.remove('on'); });
    b.classList.add('on'); speed = parseFloat(b.dataset.s);
  });
  if (selSuit) selSuit.addEventListener('change', function (e) { load(e.target.value); });
  if (replay) replay.addEventListener('click', restart);

  // public API (used by the shop "▶ Plot" buttons)
  window.PlotflowPlotter = { load: load };

  load(ORDER[0]);
  requestAnimationFrame(frame);
})();
