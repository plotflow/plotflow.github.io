/* ============================================================
   PLOTFLOW · Live stock
   Fetches remaining-count-per-edition from the checkout Worker's
   /stock endpoint and hands it to whoever's listening (shop grid,
   product page). Editions are limited runs; this shows how many of
   each are left so a sell-out reads as scarcity, not a dead link.

   Fails silent: if the endpoint is unreachable or not yet deployed,
   no badges render and the site behaves exactly as before.
   Depends on: scripts/config.js (PLOTFLOW_CONFIG.checkoutEndpoint)
   ============================================================ */
(function () {
  var CFG = window.PLOTFLOW_CONFIG || {};
  var base = (CFG.checkoutEndpoint || "").replace(/\/+$/, "");
  var SIZE = 25; // pieces per numbered edition

  var data = null;     // { zaku: 22, ... } remaining counts, or null on failure
  var done = false;
  var waiting = [];

  function flush() {
    var list = waiting; waiting = [];
    list.forEach(function (cb) { try { cb(data); } catch (e) {} });
  }

  if (base) {
    fetch(base + "/stock", { method: "GET" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { data = d && typeof d === "object" ? d : null; done = true; flush(); })
      .catch(function () { data = null; done = true; flush(); });
  } else {
    done = true;
  }

  window.PlotflowStock = {
    size: SIZE,
    // cb receives the counts object (or null if unavailable), once.
    ready: function (cb) {
      if (typeof cb !== "function") return;
      if (done) cb(data); else waiting.push(cb);
    }
  };
})();
