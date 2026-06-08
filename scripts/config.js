/* ============================================================
   PLOTFLOW · Front-end config
   Public, safe-to-commit settings only. NEVER put a Stripe secret
   key here — secrets live in the Cloudflare Worker (see worker/).
   ============================================================ */
window.PLOTFLOW_CONFIG = {
  checkoutEndpoint: "https://plotflow-checkout.plotflow-io.workers.dev",
  currency: "$",

  // Newsletter / drop-list signup. Paste your email provider's form-POST URL
  // here to switch the signup form on (until then it shows a friendly notice).
  //   • Kit (ConvertKit):  https://app.kit.com/forms/XXXXXX/subscriptions   field: email_address
  //   • Buttondown:        https://buttondown.com/api/emails/embed-subscribe/USERNAME   field: email
  //   • Mailchimp:         the form action URL from the embed code            field: EMAIL
  newsletterEndpoint: "",
  newsletterField: "email_address"
};
