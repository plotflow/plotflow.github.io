/* ============================================================
   PLOTFLOW · Cart
   A client-side, multi-item cart persisted in localStorage. The
   "Acquire" buttons add editions; the nav "Cart [N]" opens a drawer.
   Checkout posts {items:[{key,qty}]} to the Cloudflare Worker, which
   builds a Stripe Checkout Session and returns its hosted URL.

   Cart items carry their own display fields (name/code/price/edition)
   captured at add-time, so interior pages don't need data/editions.js.
   Each item also carries a pen `color` (black/red/blue); the same suit
   in two colors is two distinct line items, identified by key|color.
   ============================================================ */
(function () {
  var KEY = "plotflow_cart_v1";
  var CFG = window.PLOTFLOW_CONFIG || {};
  var CUR = CFG.currency || "$";
  var DATA = (window.PLOTFLOW && window.PLOTFLOW.suits) || {};
  var COLORS = { black: "Black", red: "Red", blue: "Blue" };

  function normColor(c) { c = String(c || "black").toLowerCase(); return COLORS[c] ? c : "black"; }
  function colorName(c) { return COLORS[normColor(c)]; }
  function lineId(i) { return i.key + "|" + normColor(i.color); }

  function read() {
    try { return JSON.parse(localStorage.getItem(KEY)) || []; } catch (e) { return []; }
  }
  function write(items) {
    localStorage.setItem(KEY, JSON.stringify(items));
    render();
  }
  function priceNum(s) { return parseFloat(String(s == null ? "" : s).replace(/[^0-9.]/g, "")) || 0; }
  function money(n) { return CUR + (Math.round(n * 100) / 100).toLocaleString(); }

  function count() { return read().reduce(function (n, i) { return n + i.qty; }, 0); }
  function subtotal() { return read().reduce(function (s, i) { return s + priceNum(i.price) * i.qty; }, 0); }

  function add(key, color) {
    color = normColor(color);
    var items = read();
    var found = items.filter(function (i) { return i.key === key && normColor(i.color) === color; })[0];
    if (found) { found.qty++; }
    else {
      var s = DATA[key] || {};
      items.push({ key: key, color: color, qty: 1, name: s.name || key, code: s.code || "", price: s.price || "", edition: s.edition || "" });
    }
    write(items);
    openDrawer();
  }
  function setQty(id, qty) {
    var items = read().map(function (i) { return lineId(i) === id ? Object.assign({}, i, { qty: qty }) : i; })
      .filter(function (i) { return i.qty > 0; });
    write(items);
  }
  function remove(id) { write(read().filter(function (i) { return lineId(i) !== id; })); }
  function clear() { write([]); }

  /* ---- drawer markup (built once, appended to <body>) ---- */
  var overlay, drawer, itemsEl, subEl, checkoutBtn;
  function build() {
    overlay = document.createElement("div");
    overlay.className = "cart-overlay";

    drawer = document.createElement("aside");
    drawer.className = "cart-drawer";
    drawer.setAttribute("aria-hidden", "true");
    drawer.innerHTML =
      '<div class="cart-head"><div><span class="cart-title">Cart</span><span class="star cart-ast">*</span>' +
        '<span class="jp cart-jp">買い物かご</span></div>' +
        '<button class="cart-close" aria-label="Close cart">×</button></div>' +
      '<div class="cart-items"></div>' +
      '<div class="cart-foot">' +
        '<div class="cart-sub"><span class="tiny">Subtotal</span><span class="cart-sub-val">' + money(0) + '</span></div>' +
        '<p class="cart-note tiny">Shipping + any taxes calculated at checkout. Each edition is plotted to order.</p>' +
        '<button class="cart-checkout">Checkout</button>' +
      '</div>';

    document.body.appendChild(overlay);
    document.body.appendChild(drawer);

    itemsEl = drawer.querySelector(".cart-items");
    subEl = drawer.querySelector(".cart-sub-val");
    checkoutBtn = drawer.querySelector(".cart-checkout");

    overlay.addEventListener("click", closeDrawer);
    drawer.querySelector(".cart-close").addEventListener("click", closeDrawer);
    checkoutBtn.addEventListener("click", checkout);

    itemsEl.addEventListener("click", function (e) {
      var row = e.target.closest("[data-id]"); if (!row) return;
      var id = row.getAttribute("data-id");
      var item = read().filter(function (i) { return lineId(i) === id; })[0]; if (!item) return;
      if (e.target.closest("[data-inc]")) setQty(id, item.qty + 1);
      else if (e.target.closest("[data-dec]")) setQty(id, item.qty - 1);
      else if (e.target.closest("[data-rm]")) remove(id);
    });

    document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeDrawer(); });
  }

  function openDrawer() { if (!drawer) return; drawer.classList.add("open"); overlay.classList.add("show"); drawer.setAttribute("aria-hidden", "false"); }
  function closeDrawer() { if (!drawer) return; drawer.classList.remove("open"); overlay.classList.remove("show"); drawer.setAttribute("aria-hidden", "true"); }

  function render() {
    // nav badges
    [].forEach.call(document.querySelectorAll(".cart"), function (b) { b.textContent = "Cart [" + count() + "]"; });
    if (!itemsEl) return;
    var items = read();
    if (!items.length) {
      itemsEl.innerHTML = '<div class="cart-empty tiny">Your cart is empty.</div>';
    } else {
      itemsEl.innerHTML = items.map(function (i) {
        return '<div class="ci" data-id="' + lineId(i) + '">' +
            '<div class="ci-main"><div class="ci-name">' + (i.code ? i.code + " " : "") + i.name + '</div>' +
              '<div class="ci-ed tiny">' + (i.edition ? i.edition + " · " : "") + colorName(i.color) + ' ink</div></div>' +
            '<div class="ci-qty"><button data-dec aria-label="Decrease">−</button>' +
              '<span>' + i.qty + '</span>' +
              '<button data-inc aria-label="Increase">+</button></div>' +
            '<div class="ci-price">' + money(priceNum(i.price) * i.qty) + '</div>' +
            '<button class="ci-rm" data-rm aria-label="Remove">×</button>' +
          '</div>';
      }).join("");
    }
    if (subEl) subEl.textContent = money(subtotal());
    if (checkoutBtn) checkoutBtn.disabled = items.length === 0;
  }

  function checkout() {
    var items = read();
    if (!items.length) return;
    if (!CFG.checkoutEndpoint) {
      alert("Checkout isn't connected yet. (Set checkoutEndpoint in scripts/config.js once the Stripe Worker is deployed.)");
      return;
    }
    var orig = checkoutBtn.textContent;
    checkoutBtn.disabled = true; checkoutBtn.textContent = "Redirecting…";
    fetch(CFG.checkoutEndpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items: items.map(function (i) { return { key: i.key, qty: i.qty, color: normColor(i.color) }; }) })
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
      .then(function (res) {
        if (res.ok && res.d.url) { window.location.href = res.d.url; }
        else { throw new Error((res.d && res.d.error) || "Checkout failed"); }
      })
      .catch(function (err) {
        alert("Could not start checkout. " + err.message);
        checkoutBtn.disabled = false; checkoutBtn.textContent = orig;
      });
  }

  /* ---- global wiring ---- */
  document.addEventListener("click", function (e) {
    var acq = e.target.closest("[data-acq]");
    if (acq) { e.preventDefault(); add(acq.getAttribute("data-acq"), acq.getAttribute("data-color")); return; }
    var cartBtn = e.target.closest(".cart");
    if (cartBtn) { e.preventDefault(); openDrawer(); }
  });

  var toastEl, toastT;
  function toast(msg) {
    if (!toastEl) { toastEl = document.createElement("div"); toastEl.className = "cart-toast"; document.body.appendChild(toastEl); }
    toastEl.textContent = msg;
    toastEl.classList.add("show");
    clearTimeout(toastT);
    toastT = setTimeout(function () { toastEl.classList.remove("show"); }, 3500);
  }

  // Notice when returning from a cancelled Stripe checkout (cart is preserved).
  function checkCancelled() {
    var params = new URLSearchParams(location.search);
    if (params.get("checkout") === "cancelled") {
      toast("Checkout cancelled — your cart is saved.");
      params.delete("checkout");
      var qs = params.toString();
      history.replaceState({}, "", location.pathname + (qs ? "?" + qs : "") + location.hash);
    }
  }

  // public API
  window.PlotflowCart = { add: add, remove: remove, clear: clear, open: openDrawer, count: count };

  function init() { build(); render(); checkCancelled(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else { init(); }
})();
