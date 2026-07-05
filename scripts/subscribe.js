/* ============================================================
   PLOTFLOW · Subscribe helper
   A tiny, reusable email-to-Kit submitter for one-off signup spots
   (e.g. the post-wallpaper-download nudge) that aren't the main
   homepage form. Posts to PLOTFLOW_CONFIG.newsletterEndpoint via a
   shared hidden iframe so it works cross-origin without CORS and
   never navigates the page.
   Depends on: scripts/config.js
   ============================================================ */
(function () {
  var CFG = window.PLOTFLOW_CONFIG || {};
  var sink, form, input;

  function ensure() {
    if (form) return;
    sink = document.createElement("iframe");
    sink.name = "plotflow-sub-sink";
    sink.setAttribute("aria-hidden", "true");
    sink.style.display = "none";
    document.body.appendChild(sink);

    form = document.createElement("form");
    form.method = "post";
    form.target = "plotflow-sub-sink";
    form.style.display = "none";
    input = document.createElement("input");
    input.type = "hidden";
    input.name = CFG.newsletterField || "email_address";
    form.appendChild(input);
    document.body.appendChild(form);
  }

  function valid(v) { return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(String(v || "")); }

  window.PlotflowSubscribe = {
    valid: valid,
    configured: function () { return !!CFG.newsletterEndpoint; },
    // Fire-and-forget POST. Returns true if it was sent, false if invalid
    // email or no provider configured.
    submit: function (emailVal) {
      if (!CFG.newsletterEndpoint || !valid(emailVal)) return false;
      ensure();
      form.action = CFG.newsletterEndpoint;
      input.value = emailVal;
      form.submit();
      return true;
    }
  };
})();
