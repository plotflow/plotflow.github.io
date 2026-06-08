/* ============================================================
   PLOTFLOW · Product page
   Renders a single edition from window.PLOTFLOW (data/editions.js)
   based on ?id=<key>. Includes a self-contained live-plot preview
   that strokes the suit's path onto a canvas in the chosen pen
   color, over a Strathmore Bristol paper background. Choosing a
   color re-plots the preview and updates what gets added to cart.
   Depends on: data/editions.js, scripts/cart.js (PlotflowCart)
   ============================================================ */
(function () {
  var DATA = (window.PLOTFLOW && window.PLOTFLOW.suits) || {};
  var $ = function (id) { return document.getElementById(id); };

  // Pen inks (display hex) + paper. Keys must match the cart/Worker allow-list.
  var INKS = {
    black: { name: "Black", hex: "#17150f" },
    red:   { name: "Red",   hex: "#d8342a" },
    blue:  { name: "Blue",  hex: "#1f4aa0" }
  };
  var DEFAULT_COLOR = "black";

  var params = new URLSearchParams(location.search);
  var key = params.get("id");
  var suit = key && DATA[key];

  if (!suit) {
    var miss = $("pdMissing"); if (miss) miss.hidden = false;
    return;
  }

  // ---- populate text ----
  document.title = suit.code + " " + suit.name + " — PLOTFLOW*";
  $("pd").hidden = false;
  $("pdCode").textContent = suit.code;
  $("pdName").textContent = suit.name;
  $("pdJp").textContent = suit.jp || "";
  $("pdEd").textContent = suit.edition || "";
  $("pdPrice").textContent = suit.price || "";
  $("pdAcquirePrice").textContent = suit.price || "";
  $("pdLore").textContent = suit.lore || "";
  $("pdBedlabel").textContent = suit.code + " " + suit.name;
  var sizeM = (suit.edition || "").split("·").pop().trim();
  $("pdSize").textContent = sizeM || "11×14″";

  // ---- color swatches ----
  var color = DEFAULT_COLOR;
  var swWrap = $("pdSwatches");
  Object.keys(INKS).forEach(function (c) {
    var ink = INKS[c];
    var b = document.createElement("button");
    b.className = "pd-swatch" + (c === color ? " on" : "");
    b.setAttribute("role", "radio");
    b.setAttribute("aria-checked", c === color ? "true" : "false");
    b.setAttribute("aria-label", ink.name + " ink");
    b.dataset.color = c;
    b.innerHTML = '<span class="pd-dot" style="background:' + ink.hex + '"></span>' +
                  '<span class="pd-swatch-name tiny">' + ink.name + '</span>';
    swWrap.appendChild(b);
  });
  swWrap.addEventListener("click", function (e) {
    var b = e.target.closest("[data-color]"); if (!b) return;
    color = b.dataset.color;
    [].forEach.call(swWrap.children, function (x) {
      var on = x === b;
      x.classList.toggle("on", on);
      x.setAttribute("aria-checked", on ? "true" : "false");
    });
    $("pdInk").textContent = INKS[color].name + " ink";
    plot.setInk(INKS[color].hex);
    plot.restart();
  });
  $("pdInk").textContent = INKS[color].name + " ink";

  // ---- acquire ----
  $("pdAcquire").addEventListener("click", function () {
    if (window.PlotflowCart) window.PlotflowCart.add(key, color);
  });

  // ---- live-plot preview (self-contained progressive stroker) ----
  var plot = makePreview(suit, INKS[color].hex);

  function makePreview(s, inkHex) {
    var svg = $("pdSvg"), path = $("pdPath"), canvas = $("pdCanvas"), replay = $("pdReplay");
    var ctx = canvas.getContext("2d");
    var BASE = 18;                 // seconds for a full preview plot
    var ink = inkHex;
    var len = 1, drawn = 0, painted = 0, playing = true, last = null;
    var vb = { x: 0, y: 0, w: s.w || 1, h: s.h || 1 };
    var tf = { s: 1, ox: 0, oy: 0, dpr: 1, ready: false };
    var prevPt = null;

    // crop viewBox to the suit's bounding box (+ padding), like the hero plotter
    path.setAttribute("d", s.d);
    svg.setAttribute("viewBox", vb.x + " " + vb.y + " " + vb.w + " " + vb.h);
    try {
      var bb = path.getBBox();
      var pad = Math.max(bb.width, bb.height) * 0.06;
      vb = { x: bb.x - pad, y: bb.y - pad, w: bb.width + pad * 2, h: bb.height + pad * 2 };
    } catch (e) {}
    svg.setAttribute("viewBox", vb.x + " " + vb.y + " " + vb.w + " " + vb.h);
    len = path.getTotalLength(); if (!len || !isFinite(len)) len = 1;

    function mapX(ux) { return (tf.ox + (ux - vb.x) * tf.s) * tf.dpr; }
    function mapY(uy) { return (tf.oy + (uy - vb.y) * tf.s) * tf.dpr; }

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
      ctx.strokeStyle = ink;
      ctx.lineWidth = Math.max(1, 1.1 * tf.dpr);
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      painted = 0;
      prevPt = null;
    }

    function paintTo(target) {
      if (!tf.ready || target <= painted) return;
      var step = Math.max(0.5, 2 / tf.s);
      var liftSq = (step * 3) * (step * 3);
      ctx.beginPath();
      if (prevPt) ctx.moveTo(mapX(prevPt.x), mapY(prevPt.y));
      var L = painted;
      while (L < target) {
        L = Math.min(target, L + step);
        var p = path.getPointAtLength(L);
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

    function frame(t) {
      if (last == null) last = t;
      var dt = (t - last) / 1000; last = t;
      if (playing && tf.ready) {
        drawn = Math.min(len, drawn + (len / BASE) * dt);
        paintTo(drawn);
        if (drawn >= len) { playing = false; if (replay) replay.hidden = false; }
      }
      requestAnimationFrame(frame);
    }

    function restart() {
      drawn = 0; playing = true; last = null;
      if (replay) replay.hidden = true;
      resetCanvas();
    }

    window.addEventListener("resize", function () { resetCanvas(); paintTo(drawn); });
    if (replay) replay.addEventListener("click", restart);

    resetCanvas();
    requestAnimationFrame(frame);

    return {
      restart: restart,
      setInk: function (hex) { ink = hex; }
    };
  }
})();
