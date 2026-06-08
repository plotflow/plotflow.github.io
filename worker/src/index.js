/* ============================================================
   PLOTFLOW · Checkout + Order Notification Worker (Cloudflare)

   POST /              → creates a Stripe Checkout Session
   POST /webhook       → handles Stripe webhook (checkout.session.completed)
                          and emails order details to the shop owner

   Secrets (set via `wrangler secret put`):
     STRIPE_SECRET_KEY      sk_test_… or sk_live_…
     STRIPE_WEBHOOK_SECRET  whsec_…  (from Stripe Dashboard → Webhooks)
     RESEND_API_KEY         re_…     (from resend.com)
   ============================================================ */

const ALLOWED_ORIGINS = [
  "https://plotflow.io",
  "https://www.plotflow.io",
  "http://localhost:8000",
  "http://127.0.0.1:8000"
];

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

const SHIPPING = { label: "Standard shipping", cents: 900 };

const SUCCESS_URL = "https://plotflow.io/success.html?session_id={CHECKOUT_SESSION_ID}";
const CANCEL_URL  = "https://plotflow.io/?checkout=cancelled";
const SHIP_COUNTRIES = ["US", "CA", "GB", "AU", "DE", "FR", "JP"];

const NOTIFY_EMAIL = "devin@plotflow.io";
const FROM_EMAIL   = "orders@plotflow.io";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // ---- webhook endpoint ----
    if (url.pathname === "/webhook" && request.method === "POST") {
      return handleWebhook(request, env);
    }

    // ---- checkout endpoint ----
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

    const orderSummary = [];
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
      orderSummary.push(`${qty}× ${prod.name}`);
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

    form.set("metadata[editions]", orderSummary.join(", "));

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

// ---- Stripe Webhook Handler ----

async function handleWebhook(request, env) {
  const payload = await request.text();
  const sig = request.headers.get("stripe-signature");

  if (env.STRIPE_WEBHOOK_SECRET && sig) {
    const valid = await verifyStripeSignature(payload, sig, env.STRIPE_WEBHOOK_SECRET);
    if (!valid) return new Response("Invalid signature", { status: 400 });
  }

  let event;
  try { event = JSON.parse(payload); } catch (e) { return new Response("Bad JSON", { status: 400 }); }

  if (event.type === "checkout.session.completed") {
    const session = event.data.object;

    const sessionDetail = await fetch(
      `https://api.stripe.com/v1/checkout/sessions/${session.id}?expand[]=line_items&expand[]=customer_details`,
      { headers: { "Authorization": "Bearer " + env.STRIPE_SECRET_KEY } }
    ).then(r => r.json());

    const items = (sessionDetail.line_items && sessionDetail.line_items.data) || [];
    const cust = sessionDetail.customer_details || {};
    const ship = sessionDetail.shipping_details || sessionDetail.collected_information?.shipping_details || {};
    const addr = ship.address || {};
    const meta = sessionDetail.metadata || {};

    const itemLines = items.map(li =>
      `${li.quantity}× ${li.description} — $${(li.amount_total / 100).toFixed(2)}`
    ).join("\n");

    const total = sessionDetail.amount_total ? `$${(sessionDetail.amount_total / 100).toFixed(2)}` : "—";

    const shipAddr = [
      ship.name || cust.name || "",
      addr.line1, addr.line2,
      [addr.city, addr.state, addr.postal_code].filter(Boolean).join(", "),
      addr.country
    ].filter(Boolean).join("\n");

    const text = [
      "NEW ORDER — PLOTFLOW",
      "═".repeat(40),
      "",
      `Customer: ${cust.name || "—"}`,
      `Email:    ${cust.email || "—"}`,
      `Phone:    ${cust.phone || "—"}`,
      "",
      "EDITIONS",
      "─".repeat(20),
      itemLines || meta.editions || "—",
      "",
      `Subtotal + shipping: ${total}`,
      "",
      "SHIP TO",
      "─".repeat(20),
      shipAddr || "No address collected",
      "",
      `Session: ${session.id}`,
      `Payment: ${session.payment_intent}`,
      `Dashboard: https://dashboard.stripe.com/payments/${session.payment_intent}`,
    ].join("\n");

    const html = `
      <div style="font-family:monospace;max-width:600px;margin:0 auto;padding:20px">
        <h2 style="margin:0 0 4px">NEW ORDER — PLOTFLOW*</h2>
        <hr style="border:2px solid #e8351f;margin:8px 0 20px">
        <table style="font-size:14px;line-height:1.6">
          <tr><td style="color:#888;padding-right:12px">Customer</td><td><strong>${esc(cust.name || "—")}</strong></td></tr>
          <tr><td style="color:#888;padding-right:12px">Email</td><td>${esc(cust.email || "—")}</td></tr>
          <tr><td style="color:#888;padding-right:12px">Phone</td><td>${esc(cust.phone || "—")}</td></tr>
        </table>
        <h3 style="margin:20px 0 6px;font-size:13px;letter-spacing:2px;text-transform:uppercase;color:#e8351f">Editions</h3>
        <div style="background:#f5f4ef;padding:12px 16px;border-left:3px solid #e8351f;font-size:14px">
          ${items.map(li => `<div>${li.quantity}× <strong>${esc(li.description)}</strong> — $${(li.amount_total / 100).toFixed(2)}</div>`).join("") || esc(meta.editions || "—")}
        </div>
        <p style="font-size:15px;margin:12px 0"><strong>Total: ${esc(total)}</strong></p>
        <h3 style="margin:20px 0 6px;font-size:13px;letter-spacing:2px;text-transform:uppercase;color:#e8351f">Ship To</h3>
        <div style="background:#f5f4ef;padding:12px 16px;border-left:3px solid #e8351f;font-size:14px;white-space:pre-line">${esc(shipAddr || "No address collected")}</div>
        <p style="margin-top:20px;font-size:12px;color:#888">
          <a href="https://dashboard.stripe.com/payments/${session.payment_intent}" style="color:#e8351f">View in Stripe →</a>
        </p>
      </div>`;

    if (env.RESEND_API_KEY) {
      await fetch("https://api.resend.com/emails", {
        method: "POST",
        headers: {
          "Authorization": "Bearer " + env.RESEND_API_KEY,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          from: `PlotFlow Orders <${FROM_EMAIL}>`,
          to: [NOTIFY_EMAIL],
          subject: `New order: ${meta.editions || "PlotFlow edition"}`,
          html: html,
          text: text
        })
      });
    }
  }

  return new Response("ok", { status: 200 });
}

// ---- Stripe signature verification (HMAC-SHA256) ----

async function verifyStripeSignature(payload, header, secret) {
  try {
    const pairs = Object.fromEntries(header.split(",").map(p => {
      const [k, v] = p.split("="); return [k.trim(), v];
    }));
    const timestamp = pairs.t;
    const sig = pairs.v1;
    if (!timestamp || !sig) return false;

    const age = Math.floor(Date.now() / 1000) - parseInt(timestamp);
    if (Math.abs(age) > 300) return false;

    const key = await crypto.subtle.importKey(
      "raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]
    );
    const signed = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(`${timestamp}.${payload}`));
    const expected = Array.from(new Uint8Array(signed)).map(b => b.toString(16).padStart(2, "0")).join("");
    return expected === sig;
  } catch (e) { return false; }
}

// ---- Helpers ----

function esc(s) { return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }

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
