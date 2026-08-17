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
  document.title = suit.code + " " + suit.name + " · PLOTFLOW*";
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
  var recCode = $("pfRecCode");
  if (recCode) recCode.textContent = suit.code;

  // ---- stroke program table (console record layout) ----
  // Same physical model as the Live Plot: pen-down feed, pen-up travel
  // feed, and a fixed cost per pen lift.
  (function () {
    var tbl = $("pdProgram"); if (!tbl) return;
    var re = /([ML])\s*(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)/g, m;
    var px = null, py = null, draw = 0, travel = 0, lifts = 0, verts = 0;
    var minx = 1e9, miny = 1e9, maxx = -1e9, maxy = -1e9;
    while ((m = re.exec(suit.d)) !== null) {
      var x = +m[2], y = +m[3]; verts++;
      if (x < minx) minx = x; if (x > maxx) maxx = x;
      if (y < miny) miny = y; if (y > maxy) maxy = y;
      if (m[1] === "M") { if (px !== null) { travel += Math.hypot(x - px, y - py); lifts++; } }
      else if (px !== null) { draw += Math.hypot(x - px, y - py); }
      px = x; py = y;
    }
    var mm = 420 / Math.max(maxx - minx, maxy - miny);
    var min = (draw * mm) / 1100 + (travel * mm) / 6600 + (lifts * 0.10) / 60;
    var sec = Math.round(min * 60);
    var rows = [
      ["Ink laid", (draw * mm / 1000).toFixed(1) + " m"],
      ["Strokes", (lifts + 1).toLocaleString()],
      ["Vertices", verts.toLocaleString()],
      ["Plot time", Math.floor(sec / 60) + ":" + String(sec % 60).padStart(2, "0")],
      ["Feed", "1100 mm/min"]
    ];
    tbl.innerHTML = rows.map(function (r) {
      return "<tr><td>" + r[0] + "</td><td>" + r[1] + "</td></tr>";
    }).join("");
  })();

  // ---- record navigation (prev / next in shop order) ----
  (function () {
    var prev = $("pdPrev"), next = $("pdNext");
    var ORDER = (window.PLOTFLOW && window.PLOTFLOW.shopOrder) || [];
    var i = ORDER.indexOf(key);
    if (i < 0 || !ORDER.length) return;
    var n = ORDER.length;
    if (prev) prev.href = "product.html?id=" + encodeURIComponent(ORDER[(i - 1 + n) % n]);
    if (next) next.href = "product.html?id=" + encodeURIComponent(ORDER[(i + 1) % n]);
  })();

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
  var acqBtn = $("pdAcquire");
  acqBtn.addEventListener("click", function () {
    if (acqBtn.disabled) return;
    if (window.PlotflowCart) window.PlotflowCart.add(key, color);
  });

  // ---- live stock (remaining count / sold-out) ----
  if (window.PlotflowStock) {
    window.PlotflowStock.ready(function (counts) {
      if (!counts || typeof counts[key] !== "number") return;
      var left = counts[key], size = window.PlotflowStock.size, badge = $("pdStock");
      if (left <= 0) {
        if (badge) { badge.textContent = "Sold out — this edition has closed"; badge.classList.add("low"); badge.hidden = false; }
        acqBtn.textContent = "Sold out";
        acqBtn.disabled = true;
      } else if (badge) {
        badge.textContent = left + " of " + size + " remaining";
        if (left <= 5) badge.classList.add("low");
        badge.hidden = false;
      }
    });
  }

  // ---- live-plot preview (self-contained progressive stroker) ----
  var plot = makePreview(suit, INKS[color].hex);

  function makePreview(s, inkHex) {
    var svg = $("pdSvg"), path = $("pdPath"), canvas = $("pdCanvas"), replay = $("pdReplay");
    var ctx = canvas.getContext("2d");
    var BASE = 18;                 // seconds for a full preview plot (product page keeps a quicker cut)
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

    // Size the sheet to the artwork's aspect (7% margins), centred in the
    // stage — same treatment as the homepage bed, so the drawing fills the
    // paper instead of floating in blank bristol.
    var sheet = document.querySelector(".pfr-sheet");
    var sheetWrap = document.querySelector(".pfr-stagewrap");
    function fitSheet() {
      if (!sheet || !sheetWrap) return;
      var pad2 = 22;
      var aw = sheetWrap.clientWidth - pad2 * 2, ah = sheetWrap.clientHeight - pad2 * 2;
      if (aw <= 0 || ah <= 0) return;
      var ar = vb.w / vb.h;
      var w = aw, h = w / ar;
      if (h > ah) { h = ah; w = h * ar; }
      sheet.style.width = w + "px";
      sheet.style.height = h + "px";
      sheet.style.left = (pad2 + (aw - w) / 2) + "px";
      sheet.style.top = (pad2 + (ah - h) / 2) + "px";
      sheet.style.right = "auto";
      sheet.style.bottom = "auto";
    }
    fitSheet();

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

    window.addEventListener("resize", function () { fitSheet(); resetCanvas(); paintTo(drawn); });
    if (replay) replay.addEventListener("click", restart);

    resetCanvas();
    requestAnimationFrame(frame);

    return {
      restart: restart,
      setInk: function (hex) { ink = hex; },
      wallpaper: function (inkHex) {
        var W = 1170, H = 2532;
        var off = document.createElement("canvas");
        off.width = W; off.height = H;
        var oc = off.getContext("2d");

        oc.fillStyle = "#f6f3ec";
        oc.fillRect(0, 0, W, H);

        var sc = Math.min(W / vb.w, H / vb.h) * 0.8;
        var offX = (W - vb.w * sc) / 2;
        var offY = (H - vb.h * sc) / 2;

        oc.strokeStyle = inkHex;
        oc.lineWidth = Math.max(1.5, 2);
        oc.lineJoin = "round";
        oc.lineCap = "round";

        var step = Math.max(0.5, 2 / sc);
        var liftSq = (step * 3) * (step * 3);
        var prev = null;
        oc.beginPath();
        for (var L = 0; L < len; L += step) {
          var p = path.getPointAtLength(L);
          var mx = offX + (p.x - vb.x) * sc;
          var my = offY + (p.y - vb.y) * sc;
          if (!prev) { oc.moveTo(mx, my); }
          else {
            var dx = p.x - prev.x, dy = p.y - prev.y;
            if (dx * dx + dy * dy > liftSq) oc.moveTo(mx, my);
            else oc.lineTo(mx, my);
          }
          prev = p;
        }
        oc.stroke();

        oc.font = "bold 28px 'Archivo', sans-serif";
        oc.fillStyle = "rgba(21,22,15,0.25)";
        oc.textAlign = "center";
        oc.fillText("PLOTFLOW*", W / 2, H - 60);

        return off.toDataURL("image/png");
      }
    };
  }

  // ---- wallpaper download ----
  var dlBtn = $("pdWallpaper");
  if (dlBtn) {
    dlBtn.addEventListener("click", function () {
      dlBtn.textContent = "Rendering…";
      setTimeout(function () {
        var dataUrl = plot.wallpaper(INKS[color].hex);
        var a = document.createElement("a");
        a.href = dataUrl;
        a.download = key + "-" + color + "-wallpaper.png";
        a.click();
        dlBtn.textContent = "↓ Download phone wallpaper";
        revealNudge();
      }, 50);
    });
  }

  // ---- soft gate: gentle drop-list nudge after a download ----
  // The wallpaper is always free; this just invites a signup once per visit,
  // and only if an email provider is wired up.
  function revealNudge() {
    var nudge = $("pdNudge");
    if (!nudge || nudge.dataset.done) return;
    if (!(window.PlotflowSubscribe && window.PlotflowSubscribe.configured())) return;
    try { if (sessionStorage.getItem("pf_nudge")) return; } catch (e) {}
    nudge.hidden = false;
  }

  (function wireNudge() {
    var form = $("pdNudgeForm"); if (!form) return;
    var inp = $("pdNudgeEmail"), msg = $("pdNudgeMsg"), nudge = $("pdNudge");
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var sub = window.PlotflowSubscribe;
      if (!sub || !sub.valid(inp.value)) {
        msg.textContent = "Please enter a valid email."; msg.hidden = false;
        return;
      }
      sub.submit(inp.value);
      form.hidden = true;
      msg.textContent = "You're on the list. Watch for the next drop.";
      msg.hidden = false;
      nudge.dataset.done = "1";
      try { sessionStorage.setItem("pf_nudge", "1"); } catch (e) {}
    });
  })();
})();
