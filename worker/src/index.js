/* ============================================================
   PLOTFLOW · Checkout Worker (Cloudflare)
   Turns the site's cart into a Stripe Checkout Session and returns
   the hosted-checkout URL.

   Prices live HERE, server-side (see CATALOG), built as ad-hoc
   `price_data` line items — so there is nothing to create in the
   Stripe dashboard and nothing for the browser to tamper with. The
   client only ever sends {items:[{key,qty}]}.

   Secret:  wrangler secret put STRIPE_SECRET_KEY   (paste sk_test_… / sk_live_…)
   Deploy:  wrangler deploy                         (see ../README.md)
   ============================================================ */

// Origins allowed to call this endpoint (the live site + local dev).
const ALLOWED_ORIGINS = [
  "https://plotflow.io",
  "https://www.plotflow.io",
  "http://localhost:8000",
  "http://127.0.0.1:8000"
];

// edition key -> { name shown on Stripe checkout, price in cents }.
// Keys must match data/editions.js. Change a price by editing `cents`.
const CURRENCY = "usd";
const CATALOG = {
  zaku:      { name: "Zaku II — MS-06",      cents: 4500 },
  guncannon: { name: "Guncannon — RX-77",    cents: 4500 },
  bigzam:    { name: "Big Zam — MA-08",      cents: 4500 },
  dom:       { name: "Dom — MS-09",          cents: 4500 },
  zgok:      { name: "Z'Gok — MSM-07",       cents: 4500 },
  gp02:      { name: "GP-02A — RX-78GP02",   cents: 4500 },
  gm:        { name: "GM — RGM-79",          cents: 4500 },
  guntank:   { name: "Guntank — RX-75",      cents: 4500 }
};

// Flat shipping fee added on top, all countries. Set cents = 0 for free shipping.
const SHIPPING = { label: "Standard shipping", cents: 900 };

const SUCCESS_URL = "https://plotflow.io/success.html?session_id={CHECKOUT_SESSION_ID}";
const CANCEL_URL  = "https://plotflow.io/?checkout=cancelled";

// Countries we ship to (collected on the Stripe-hosted page).
const SHIP_COUNTRIES = ["US", "CA", "GB", "AU", "DE", "FR", "JP"];

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const cors = corsHeaders(origin);

    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (request.method !== "POST") return json({ error: "Method not allowed" }, 405, cors);
    if (!env.STRIPE_SECRET_KEY) return json({ error: "Server not configured" }, 500, cors);

    let body;
    try { body = await request.json(); } catch (e) { return json({ error: "Invalid JSON" }, 400, cors); }

    const items = Array.isArray(body.items) ? body.items : [];
    const form = new URLSearchParams();
    form.set("mode", "payment");

    let n = 0;
    for (const it of items) {
      const key = String((it && it.key) || "");
      const qty = Math.max(1, Math.min(99, parseInt(it && it.qty, 10) || 0));
      const prod = CATALOG[key];
      if (!prod) return json({ error: "Unavailable item: " + key }, 400, cors);
      form.set(`line_items[${n}][price_data][currency]`, CURRENCY);
      form.set(`line_items[${n}][price_data][unit_amount]`, String(prod.cents));
      form.set(`line_items[${n}][price_data][product_data][name]`, prod.name);
      form.set(`line_items[${n}][quantity]`, String(qty));
      n++;
    }
    if (!n) return json({ error: "Cart is empty" }, 400, cors);

    form.set("success_url", SUCCESS_URL);
    form.set("cancel_url", CANCEL_URL);
    form.set("billing_address_collection", "required");
    form.set("phone_number_collection[enabled]", "true");
    SHIP_COUNTRIES.forEach((c, i) => form.set(`shipping_address_collection[allowed_countries][${i}]`, c));

    if (SHIPPING.cents > 0) {
      form.set("shipping_options[0][shipping_rate_data][type]", "fixed_amount");
      form.set("shipping_options[0][shipping_rate_data][fixed_amount][amount]", String(SHIPPING.cents));
      form.set("shipping_options[0][shipping_rate_data][fixed_amount][currency]", CURRENCY);
      form.set("shipping_options[0][shipping_rate_data][display_name]", SHIPPING.label);
    }

    const resp = await fetch("https://api.stripe.com/v1/checkout/sessions", {
      method: "POST",
      headers: {
        "Authorization": "Bearer " + env.STRIPE_SECRET_KEY,
        "Content-Type": "application/x-www-form-urlencoded"
      },
      body: form.toString()
    });
    const data = await resp.json();
    if (!resp.ok) return json({ error: (data.error && data.error.message) || "Stripe error" }, 502, cors);
    return json({ url: data.url, id: data.id }, 200, cors);
  }
};

function corsHeaders(origin) {
  const allow = ALLOWED_ORIGINS.indexOf(origin) !== -1 ? origin : ALLOWED_ORIGINS[0];
  return {
    "Access-Control-Allow-Origin": allow,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Vary": "Origin"
  };
}

function json(obj, status, cors) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: Object.assign({ "Content-Type": "application/json" }, cors)
  });
}
