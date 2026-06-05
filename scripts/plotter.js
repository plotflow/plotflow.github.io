/* ============================================================
   PLOTFLOW · Live Plot component
   Animates a suit's single continuous path being drawn by a
   virtual AxiDraw, with a moving pen head + live readouts.
   Depends on: window.PLOTFLOW (data/editions.js)
   Exposes:    window.PlotflowPlotter.load(key)
   ============================================================ */
(function () {
  var DATA = (window.PLOTFLOW && window.PLOTFLOW.suits) || {};
  var ORDER = (window.PLOTFLOW && window.PLOTFLOW.plotterOrder) || Object.keys(DATA);

  var $ = function (id) { return document.getElementById(id); };
  var stage = $('stage'), ppath = $('ppath'), pen = $('pen'), penC = $('pen-c'), penX = $('pen-x');
  if (!stage || !ppath) return; // plotter markup not on this page

  var pbar = $('pbar'), pct = $('pct'), cx = $('cx'), cy = $('cy');
  var ink = $('ink'), inktot = $('inktot'), elapsed = $('elapsed'), total = $('total');
  var bed = $('bed'), bedlabel = $('bedlabel'), selSuit = $('suit'), playBtn = $('play'), replay = $('replay');

  var FEED = 1100;   // mm/min, shown in HUD + used for plot-time
  var BASE = 22;     // seconds for a full plot at 1x speed
  var cur, len = 1, drawn = 0, playing = true, speed = 1, mmPerUnit = 1, totalMin = 1;

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

  function load(key) {
    cur = DATA[key]; if (!cur) return;
    if (selSuit) selSuit.value = key;
    stage.setAttribute('viewBox', '0 0 ' + cur.w + ' ' + cur.h);
    bed.style.aspectRatio = cur.w + '/' + cur.h;
    ppath.setAttribute('d', cur.d);
    len = ppath.getTotalLength(); if (!len || !isFinite(len)) len = 1;
    var md = Math.max(cur.w, cur.h);
    mmPerUnit = 420 / md;                 // longest side ≈ 420mm
    totalMin = (len * mmPerUnit) / FEED;
    penC.setAttribute('r', md * 0.014);
    penX.setAttribute('d', 'M ' + (-md * 0.032) + ' 0 H ' + (md * 0.032) + ' M 0 ' + (-md * 0.032) + ' V ' + (md * 0.032));
    ppath.style.strokeDasharray = len;
    ppath.style.strokeDashoffset = len;   // hidden until plotting begins
    pen.setAttribute('opacity', '0');
    if (inktot) inktot.textContent = (len * mmPerUnit / 1000).toFixed(2);
    if (total) total.textContent = fmt(totalMin);
    if (bedlabel) bedlabel.textContent = 'BED 01 · ' + cur.code;
    drawn = 0; playing = true;
    if (replay) replay.classList.remove('show');
    if (playBtn) playBtn.textContent = 'Pause';
    render();
  }

  function render() {
    var p = drawn / len;
    ppath.style.strokeDashoffset = (len - drawn);
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
    if (drawn >= len) drawn = 0;
    playing = !playing;
    if (playBtn) playBtn.textContent = playing ? 'Pause' : 'Resume';
    if (replay) replay.classList.remove('show');
  }
  if (playBtn) playBtn.onclick = toggle;
  if ($('restart')) $('restart').onclick = function () { drawn = 0; playing = true; if (replay) replay.classList.remove('show'); if (playBtn) playBtn.textContent = 'Pause'; };
  if ($('skip')) $('skip').onclick = function () { drawn = len; playing = false; render(); if (replay) replay.classList.add('show'); if (playBtn) playBtn.textContent = 'Replay'; };
  if ($('speed')) $('speed').addEventListener('click', function (e) {
    var b = e.target.closest('button'); if (!b) return;
    [].forEach.call(e.currentTarget.children, function (x) { x.classList.remove('on'); });
    b.classList.add('on'); speed = parseFloat(b.dataset.s);
  });
  if (selSuit) selSuit.addEventListener('change', function (e) { load(e.target.value); });
  if (replay) replay.addEventListener('click', function () { drawn = 0; playing = true; replay.classList.remove('show'); if (playBtn) playBtn.textContent = 'Pause'; });

  // public API (used by the shop "▶ Plot" buttons)
  window.PlotflowPlotter = { load: load };

  load(ORDER[0]);
  requestAnimationFrame(frame);
})();
