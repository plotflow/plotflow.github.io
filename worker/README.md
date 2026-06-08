# PLOTFLOW · Checkout Worker

A tiny Cloudflare Worker that turns the site's cart into a **Stripe Checkout
Session** and hands back the hosted-checkout URL. It holds the Stripe **secret
key** (as an encrypted secret, never in this repo) and defines prices
server-side, so the browser can never set its own amount.

```
browser cart  ──POST {items:[{key,qty,color}]}──▶  Worker  ──▶  Stripe
   ◀──────────── { url } (Stripe-hosted checkout) ───────────
```

Prices and product names live in `src/index.js` → `CATALOG` as ad-hoc
`price_data` line items, so **there is nothing to create in the Stripe
dashboard** — no products, no Price IDs to paste. Editing a price is a
one-line change to `cents`.

Pen color (`black`/`red`/`blue`) is a free variant: it's validated against
`PEN_COLORS`, appended to the line-item name (so it shows in Stripe and the
order email), and never changes the price.

## One-time setup

### 1. Get your Stripe secret key (test mode first)
In the Stripe dashboard, toggle **Test mode** (top right), then go to
**Developers → API keys** and copy the **Secret key** (`sk_test_…`).

### 2. Install + authenticate Wrangler
```bash
npm install -g wrangler
wrangler login          # opens the browser to authorize your Cloudflare account
```
(If you don't have a Cloudflare account yet, create a free one first.)

### 3. Add the secret key
```bash
cd worker
wrangler secret put STRIPE_SECRET_KEY   # paste your sk_test_… key
```

### 4. Deploy
```bash
wrangler deploy
```
Wrangler prints a URL like `https://plotflow-checkout.<subdomain>.workers.dev`.

### 5. Point the site at it
Put that URL in `scripts/config.js` → `checkoutEndpoint`, commit, and push.
(Send me the URL and I'll wire it up.)

## Testing
With test-mode keys, use Stripe's test card `4242 4242 4242 4242`, any future
expiry, any CVC/ZIP. A successful payment redirects to `/success.html`; the
cart is cleared there.

## Going live
Set the **live** `sk_live_…` secret (`wrangler secret put STRIPE_SECRET_KEY`)
and redeploy. No price changes needed — `CATALOG` is the same in both modes.

## Config (top of `src/index.js`)
- `CATALOG` — edition name + price in cents. Keys must match `data/editions.js`.
- `SHIPPING` — flat fee added on top (currently $9). Set `cents: 0` for free.
- `ALLOWED_ORIGINS`, `SHIP_COUNTRIES`, `SUCCESS_URL`, `CANCEL_URL`.
- For numbered-edition inventory limits or order fulfillment hooks, add a
  Stripe webhook later.
