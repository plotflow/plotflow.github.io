/* ============================================================
   PLOTFLOW · Front-end config
   Public, safe-to-commit settings only. NEVER put a Stripe secret
   key here — secrets live in the Cloudflare Worker (see worker/).
   ============================================================ */
window.PLOTFLOW_CONFIG = {
  // URL of the deployed Cloudflare Worker that creates Stripe Checkout
  // Sessions. Fill this in after `wrangler deploy` (see worker/README.md).
  // e.g. "https://plotflow-checkout.<your-subdomain>.workers.dev"
  checkoutEndpoint: "",

  // Display currency symbol for cart subtotals (Stripe is the source of
  // truth for actual charges).
  currency: "$"
};
