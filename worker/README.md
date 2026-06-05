# PLOTFLOW · Checkout Worker

A tiny Cloudflare Worker that turns the site's cart into a **Stripe Checkout
Session** and hands back the hosted-checkout URL. It holds the Stripe **secret
key** (as an encrypted secret, never in this repo) and resolves prices
server-side, so the browser can never set its own amount.

```
browser cart  ──POST {items:[{key,qty}]}──▶  Worker  ──▶  Stripe
   ◀──────────── { url } (Stripe-hosted checkout) ───────────
```

## One-time setup

### 1. Create the editions in Stripe (test mode first)
In the Stripe dashboard, toggle **Test mode**, then for each edition create a
**Product** with a one-off **Price**. Copy each Price ID (`price_…`).

### 2. Map the prices
Edit `src/index.js` → `PRICES`, replacing every `price_REPLACE_ME` with the
matching Price ID. The keys (`zaku`, `guncannon`, …) must match the keys in
`data/editions.js`.

### 3. Install + authenticate Wrangler
```bash
npm install -g wrangler
wrangler login
```

### 4. Add the secret key
```bash
cd worker
wrangler secret put STRIPE_SECRET_KEY   # paste your sk_test_… key
```

### 5. Deploy
```bash
wrangler deploy
```
Wrangler prints a URL like `https://plotflow-checkout.<subdomain>.workers.dev`.

### 6. Point the site at it
Put that URL in `scripts/config.js` → `checkoutEndpoint`, commit, and push.

## Testing
With test-mode keys, use Stripe's test card `4242 4242 4242 4242`, any future
expiry, any CVC/ZIP. A successful payment redirects to `/success.html`.

## Going live
Swap to live-mode Price IDs in `PRICES`, set the **live** `sk_live_…` secret
(`wrangler secret put STRIPE_SECRET_KEY`), and redeploy.

## Notes
- `ALLOWED_ORIGINS`, `SHIP_COUNTRIES`, and the success/cancel URLs are at the
  top of `src/index.js`.
- Shipping is collected but not charged (standard shipping is included). To
  charge shipping or enable tax, add `shipping_options` / `automatic_tax` to
  the session.
- For inventory limits on numbered editions, set inventory on the Stripe
  Price/Product, or add a webhook later to decrement stock.
