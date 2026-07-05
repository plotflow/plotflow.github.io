/* ============================================================
   PLOTFLOW · Newsletter / drop-list signup
   Posts the email to whatever provider is set in config.js
   (PLOTFLOW_CONFIG.newsletterEndpoint). The POST targets a hidden
   iframe so it works cross-origin without CORS and never navigates
   the page; we show an inline confirmation. If no endpoint is
   configured yet, the form shows a friendly notice instead.
   ============================================================ */
(function () {
  var CFG = window.PLOTFLOW_CONFIG || {};
  var form = document.getElementById("newsForm");
  if (!form) return;
  var email = document.getElementById("newsEmail");
  var msg = document.getElementById("newsMsg");
  var field = CFG.newsletterField || "email_address";

  // Provider expects a specific field name; set it on the input.
  email.setAttribute("name", field);

  // Hidden sink so the cross-origin POST response doesn't navigate us away.
  var sink = document.createElement("iframe");
  sink.name = "plotflow-nl-sink";
  sink.setAttribute("aria-hidden", "true");
  sink.style.display = "none";
  document.body.appendChild(sink);
  form.setAttribute("target", "plotflow-nl-sink");
  form.setAttribute("method", "post");

  function valid(v) { return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v); }
  function show(text, ok) {
    msg.textContent = text;
    msg.classList.add("show");
    msg.classList.toggle("ok", !!ok);
  }

  form.addEventListener("submit", function (e) {
    if (!valid(email.value)) {
      e.preventDefault();
      show("Please enter a valid email.", false);
      return;
    }
    if (!CFG.newsletterEndpoint) {
      e.preventDefault();
      show("Drop list opens soon — email hello@plotflow.io to be added.", true);
      return;
    }
    // Let the native POST fly to the hidden iframe.
    form.setAttribute("action", CFG.newsletterEndpoint);
    show("You're on the list. Watch your inbox for the next drop.", true);
    // Clear after the browser has serialized + sent the form.
    setTimeout(function () { form.reset(); }, 100);
  });
})();
