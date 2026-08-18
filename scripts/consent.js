/* ============================================================
   PLOTFLOW · Cookie consent: GA4 Consent Mode v2, opt-in (EU pattern)
   The gtag.js loader is NOT injected until the visitor accepts;
   declining stores the choice and never loads it. Consent defaults
   are set to 'denied' in each page's <head> before this runs.
   Reopen anytime via the "Cookie settings" link this adds to the footer.
   ============================================================ */
(function () {
  var KEY = 'pf-consent';
  var GA_ID = 'G-1HJ4VQ4K1B';

  function choice() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function store(v) { try { localStorage.setItem(KEY, v); } catch (e) { /* private mode */ } }

  function loadGA() {
    if (document.getElementById('pf-ga')) return;
    gtag('consent', 'update', { analytics_storage: 'granted' });
    var s = document.createElement('script');
    s.id = 'pf-ga';
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
    document.head.appendChild(s);
  }

  var STYLE =
    '#pf-consent{position:fixed;left:18px;bottom:18px;z-index:9999;width:400px;max-width:calc(100vw - 36px);' +
    'background:rgba(21,23,15,.95);border:1px solid rgba(245,244,239,.22);box-shadow:0 16px 44px rgba(0,0,0,.45);' +
    'padding:16px 18px;color:#c3c5b8;font-size:13px;line-height:1.6;backdrop-filter:blur(10px)}' +
    '#pf-consent .hd{display:flex;justify-content:space-between;font-size:9.5px;letter-spacing:.2em;' +
    'color:#8f9184;margin-bottom:8px;text-transform:uppercase;font-weight:700}' +
    '#pf-consent .hd b{color:#f6f3ec}' +
    '#pf-consent p{margin:0 0 12px}' +
    '#pf-consent .btns{display:flex;gap:10px;align-items:center}' +
    '#pf-consent button{cursor:pointer;font-family:inherit;font-size:10.5px;font-weight:800;letter-spacing:.14em;text-transform:uppercase}' +
    '#pf-consent .ok{background:#e8351f;border:none;color:#fff;padding:9px 18px}' +
    '#pf-consent .no{background:none;border:1px solid rgba(245,244,239,.28);color:#c3c5b8;padding:8px 16px}' +
    '.pf-consent-link{cursor:pointer;text-decoration:underline}' +
    '@media (max-width:520px){#pf-consent{left:10px;right:10px;bottom:10px;width:auto}}';

  function removeBanner() {
    var el = document.getElementById('pf-consent');
    if (el) el.remove();
  }

  function showBanner() {
    if (document.getElementById('pf-consent')) return;
    if (!document.getElementById('pf-consent-style')) {
      var st = document.createElement('style');
      st.id = 'pf-consent-style';
      st.textContent = STYLE;
      document.head.appendChild(st);
    }
    var el = document.createElement('div');
    el.id = 'pf-consent';
    el.setAttribute('role', 'dialog');
    el.setAttribute('aria-label', 'Cookie consent');
    el.innerHTML =
      '<div class="hd"><span><b>Cookies</b> · tracking</span><span>GA4</span></div>' +
      '<p>We use Google Analytics to count visits and see which editions get attention. Analytics loads only if you accept.</p>' +
      '<div class="btns"><button class="ok">Accept</button><button class="no">Decline</button></div>';
    el.querySelector('.ok').addEventListener('click', function () {
      store('granted'); loadGA(); removeBanner();
    });
    el.querySelector('.no').addEventListener('click', function () {
      store('denied'); removeBanner();
    });
    document.body.appendChild(el);
  }

  // "Cookie settings" reopen link, appended to the footer bottom row on every page
  function addFooterLink() {
    var foot = document.querySelector('.foot-bot');
    if (!foot) return;
    var a = document.createElement('span');
    a.className = 'pf-consent-link';
    a.textContent = 'COOKIE SETTINGS';
    a.addEventListener('click', function () { removeBanner(); showBanner(); });
    foot.appendChild(a);
  }

  var c = choice();
  if (c === 'granted') loadGA();
  else if (c !== 'denied') showBanner();
  addFooterLink();
})();
