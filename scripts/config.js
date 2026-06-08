/* ============================================================
   PLOTFLOW · Front-end config
   Public, safe-to-commit settings only. NEVER put a Stripe secret
   key here — secrets live in the Cloudflare Worker (see worker/).
   ============================================================ */
window.PLOTFLOW_CONFIG = {
  checkoutEndpoint: "https://plotflow-checkout.plotflow-io.workers.dev",
  currency: "$"
};
