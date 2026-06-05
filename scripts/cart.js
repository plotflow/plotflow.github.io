/* ============================================================
   PLOTFLOW · Cart
   A client-side, multi-item cart persisted in localStorage. The
   "Acquire" buttons add editions; the nav "Cart [N]" opens a drawer.
   Checkout posts {items:[{key,qty}]} to the Cloudflare Worker, which
   builds a Stripe Checkout Session and returns its hosted URL.

   Cart items carry their own display fields (name/code/price/edition)
   captured at add-time, so interior pages don't need data/editions.js.
   ============================================================ */
(function () {
  var KEY = "plotflow_cart_v1";
  var CFG = window.PLOTFLOW_CONFIG || {};
  var CUR = CFG.currency || "$";
  var DATA = (window.PLOTFLOW && window.PLOTFLOW.suits) || {};

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

  function add(key) {
    var items = read();
    var found = items.filter(function (i) { return i.key === key; })[0];
    if (found) { found.qty++; }
    else {
      var s = DATA[key] || {};
      items.push({ key: key, qty: 1, name: s.name || key, code: s.code || "", price: s.price || "", edition: s.edition || "" });
    }
    write(items);
    openDrawer();
  }
  function setQty(key, qty) {
    var items = read().map(function (i) { return i.key === key ? Object.assign({}, i, { qty: qty }) : i; })
      .filter(function (i) { return i.qty > 0; });
    write(items);
  }
  function remove(key) { write(read().filter(function (i) { return i.key !== key; })); }
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
      var row = e.target.closest("[data-key]"); if (!row) return;
      var k = row.getAttribute("data-key");
      var item = read().filter(function (i) { return i.key === k; })[0]; if (!item) return;
      if (e.target.closest("[data-inc]")) setQty(k, item.qty + 1);
      else if (e.target.closest("[data-dec]")) setQty(k, item.qty - 1);
      else if (e.target.closest("[data-rm]")) remove(k);
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
        return '<div class="ci" data-key="' + i.key + '">' +
            '<div class="ci-main"><div class="ci-name">' + (i.code ? i.code + " " : "") + i.name + '</div>' +
              '<div class="ci-ed tiny">' + (i.edition || "") + '</div></div>' +
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
      body: JSON.stringify({ items: items.map(function (i) { return { key: i.key, qty: i.qty }; }) })
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
    if (acq) { e.preventDefault(); add(acq.getAttribute("data-acq")); return; }
    var cartBtn = e.target.closest(".cart");
    if (cartBtn) { e.preventDefault(); openDrawer(); }
  });

  // public API
  window.PlotflowCart = { add: add, remove: remove, clear: clear, open: openDrawer, count: count };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { build(); render(); });
  else { build(); render(); }
})();
