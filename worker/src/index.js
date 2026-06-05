/* ============================================================
   PLOTFLOW · Checkout Worker (Cloudflare)
   Creates a Stripe Checkout Session from a cart of edition keys.
   The browser only sends {items:[{key,qty}]}; prices are resolved
   here from PRICES so the client can never set its own amount.

   Secret:  wrangler secret put STRIPE_SECRET_KEY
   Deploy:  wrangler deploy   (see ../README.md)
   ============================================================ */

// Origins allowed to call this endpoint (the live site + local dev).
const ALLOWED_ORIGINS = [
  "https://plotflow.io",
  "https://www.plotflow.io",
  "http://localhost:8000",
  "http://127.0.0.1:8000"
];

// edition key  ->  Stripe Price ID.  Create each edition as a Product+Price
// in your Stripe dashboard (test mode first) and paste the price IDs here.
const PRICES = {
  zaku:      "price_REPLACE_ME",
  guncannon: "price_REPLACE_ME",
  bigzam:    "price_REPLACE_ME",
  dom:       "price_REPLACE_ME",
  zgok:      "price_REPLACE_ME",
  gp02:      "price_REPLACE_ME",
  gm:        "price_REPLACE_ME",
  guntank:   "price_REPLACE_ME"
};

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
    const line_items = [];
    for (const it of items) {
      const key = String(it && it.key || "");
      const qty = Math.max(1, Math.min(99, parseInt(it && it.qty, 10) || 0));
      const price = PRICES[key];
      if (!price || price === "price_REPLACE_ME") return json({ error: "Unavailable item: " + key }, 400, cors);
      line_items.push({ price, quantity: qty });
    }
    if (!line_items.length) return json({ error: "Cart is empty" }, 400, cors);

    const form = new URLSearchParams();
    form.set("mode", "payment");
    line_items.forEach((li, i) => {
      form.set(`line_items[${i}][price]`, li.price);
      form.set(`line_items[${i}][quantity]`, String(li.quantity));
    });
    form.set("success_url", SUCCESS_URL);
    form.set("cancel_url", CANCEL_URL);
    form.set("billing_address_collection", "required");
    form.set("phone_number_collection[enabled]", "true");
    SHIP_COUNTRIES.forEach((c, i) => form.set(`shipping_address_collection[allowed_countries][${i}]`, c));

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
