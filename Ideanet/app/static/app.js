/* Ideanet front-end behaviour. Plain JavaScript, no build step, no libraries.
   Every page works without it (forms still submit); this only adds the polish. */
(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- light / dark ---------- */
  var MOON = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z"/></svg>';
  var SUN = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M18.4 5.6L17 7M7 17l-1.4 1.4"/></svg>';
  function isDark() {
    var t = document.documentElement.getAttribute("data-theme");
    if (t) return t === "dark";
    return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  }
  function paintToggle() {
    $$("#theme-toggle, .theme-btn").forEach(function (b) {
      b.innerHTML = isDark() ? SUN : MOON;
      b.setAttribute("aria-label", isDark() ? "Switch to light mode" : "Switch to dark mode");
    });
  }
  paintToggle();
  $$("#theme-toggle, .theme-btn").forEach(function (b) {
    b.addEventListener("click", function () {
      var next = isDark() ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem("ideanet-theme", next); } catch (e) {}
      paintToggle();
    });
  });

  /* ---------- score card: count up ---------- */
  $$("[data-score]").forEach(function (card) {
    var score = parseFloat(card.getAttribute("data-score")) || 0;
    var num = $(".sc-num b", card);
    var fills = $$(".sc-seg u", card);
    function paint(v) {
      if (num) num.textContent = v.toFixed(1);
      fills.forEach(function (u, k) { u.style.transform = "scaleX(" + Math.max(0, Math.min(1, v - k)) + ")"; });
    }
    if (reduced) { paint(score); return; }
    paint(0);
    var start = null;
    function tick(t) {
      start = start || t;
      var k = Math.min(1, (t - start) / 1100);
      paint(score * (1 - Math.pow(1 - k, 3)));
      if (k < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  });

  /* ---------- overlays ---------- */
  var lastFocus = null;
  function openOverlay(el) {
    if (!el) return;
    lastFocus = document.activeElement;
    el.hidden = false;
    var f = $("button, a", el); if (f) f.focus();
    el.dispatchEvent(new CustomEvent("overlay:open"));
  }
  function closeOverlay(el) {
    if (!el || el.hidden) return;
    el.hidden = true;
    el.dispatchEvent(new CustomEvent("overlay:close"));
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }
  $$(".overlay").forEach(function (o) {
    o.addEventListener("click", function (e) { if (e.target === o) closeOverlay(o); });
    $$("[data-close]", o).forEach(function (b) { b.addEventListener("click", function () { closeOverlay(o); }); });
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") $$(".overlay").forEach(closeOverlay);
  });
  $$("[data-open-overlay]").forEach(function (b) {
    b.addEventListener("click", function () { openOverlay(document.getElementById(b.getAttribute("data-open-overlay"))); });
  });

  /* ---------- similar-projects carousel (Instagram-story style) ---------- */
  $$("[data-carousel]").forEach(function (root) {
    var STORY_MS = 5000;
    var items = $$(".preview", root);
    var segs = $$(".story-seg", root);
    var bars = segs.map(function (s) { return $("b", s); });
    var prev = $("[data-prev]", root), next = $("[data-next]", root);
    var play = $("[data-play]", root), counter = $("[data-counter]", root);
    var n = items.length, idx = 0, p = 0, playing = !reduced, hold = false, raf = null, last = null;
    if (!n) return;

    function anyOpen() { return $$(".overlay", root.closest("section") || document).some(function (o) { return !o.hidden; }); }
    function paintBars() {
      bars.forEach(function (b, k) { b.style.transform = "scaleX(" + (k < idx ? 1 : k === idx ? p : 0) + ")"; });
    }
    function show(i, animate) {
      idx = Math.max(0, Math.min(n - 1, i)); p = 0; last = null;
      items.forEach(function (it, k) {
        it.hidden = k !== idx;
        it.classList.remove("zoom");
        if (k === idx && animate !== false && !reduced) { void it.offsetWidth; it.classList.add("zoom"); }
      });
      segs.forEach(function (s, k) { if (k === idx) s.setAttribute("aria-current", "true"); else s.removeAttribute("aria-current"); });
      if (prev) prev.disabled = idx === 0;
      if (next) next.disabled = idx === n - 1;
      if (counter) counter.textContent = (idx + 1) + " of " + n;
      paintBars();
    }
    function paintPlay() {
      if (!play) return;
      play.innerHTML = playing
        ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 5v14M16 5v14"/></svg>'
        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 5l11 7-11 7z"/></svg>';
      play.setAttribute("aria-label", playing ? "Pause auto-advance" : "Play auto-advance");
    }
    function tick(t) {
      raf = null;
      if (!playing || hold || anyOpen()) { last = null; raf = requestAnimationFrame(tick); return; }
      if (last == null) last = t;
      p = Math.min(1, p + (t - last) / STORY_MS); last = t;
      paintBars();
      if (p >= 1) {
        if (idx < n - 1) show(idx + 1); else { playing = false; paintPlay(); return; }
      }
      raf = requestAnimationFrame(tick);
    }
    function kick() { if (raf == null) raf = requestAnimationFrame(tick); }

    segs.forEach(function (s, k) { s.addEventListener("click", function () { show(k); kick(); }); });
    if (prev) prev.addEventListener("click", function () { show(idx - 1); kick(); });
    if (next) next.addEventListener("click", function () { show(idx + 1); kick(); });
    if (play) play.addEventListener("click", function () {
      if (!playing && idx >= n - 1) show(0);
      playing = !playing; paintPlay(); kick();
    });
    items.forEach(function (it, k) {
      var hold_on = function () { hold = true; }, hold_off = function () { hold = false; };
      ["pointerdown", "mouseenter", "focus"].forEach(function (ev) { it.addEventListener(ev, hold_on); });
      ["pointerup", "pointerleave", "pointercancel", "mouseleave", "blur"].forEach(function (ev) { it.addEventListener(ev, hold_off); });
      it.addEventListener("click", function () { openOverlay(document.getElementById(it.getAttribute("data-detail"))); });
    });
    $$(".overlay", root.closest("section") || document).forEach(function (o) {
      o.addEventListener("overlay:close", function () { hold = false; last = null; });
    });
    show(0, false); paintPlay(); kick();
  });

  /* ---------- explore form ---------- */
  var ta = $("#idea");
  if (ta) {
    var form = ta.form, send = form && $('button[type="submit"]', form);
    var sync = function () { if (send) send.disabled = ta.value.trim().length < 3; };
    ta.addEventListener("input", sync); sync();
    var ex = $("[data-example]");
    if (ex) ex.addEventListener("click", function () { ta.value = ex.getAttribute("data-example"); sync(); ta.focus(); });
  }

  /* ---------- toggles: like, save, follow, comments ---------- */
  $$("[data-like]").forEach(function (b) {
    b.addEventListener("click", function () {
      var on = b.getAttribute("aria-pressed") !== "true";
      b.setAttribute("aria-pressed", on ? "true" : "false");
      b.classList.toggle("liked", on);
      var c = $("span", b), svg = $("svg", b);
      if (c) c.textContent = Math.max(0, (parseInt(c.textContent, 10) || 0) + (on ? 1 : -1));
      if (svg) svg.setAttribute("fill", on ? "currentColor" : "none");
    });
  });
  $$("[data-save]").forEach(function (b) {
    b.addEventListener("click", function () {
      var on = b.getAttribute("aria-pressed") !== "true";
      b.setAttribute("aria-pressed", on ? "true" : "false");
      b.classList.toggle("on", on);
      var svg = $("svg", b); if (svg) svg.setAttribute("fill", on ? "currentColor" : "none");
    });
  });
  $$("[data-follow]").forEach(function (b) {
    b.addEventListener("click", function () {
      var on = b.getAttribute("aria-pressed") !== "true";
      b.setAttribute("aria-pressed", on ? "true" : "false");
      b.classList.toggle("on", on);
      b.textContent = on ? "Following" : "Follow";
    });
  });
  $$("[data-toggle-comments]").forEach(function (b) {
    b.addEventListener("click", function () {
      var box = document.getElementById(b.getAttribute("data-toggle-comments"));
      if (!box) return;
      box.hidden = !box.hidden;
      b.setAttribute("aria-expanded", box.hidden ? "false" : "true");
      b.classList.toggle("on", !box.hidden);
      if (!box.hidden) { var i = $("input", box); if (i) i.focus(); }
    });
  });
  $$(".c-form").forEach(function (f) {
    var i = $("input", f), b = $("button", f);
    if (!i || !b) return;
    var s = function () { b.disabled = !i.value.trim(); };
    i.addEventListener("input", s); s();
  });

  /* ---------- hackathon row arrows ---------- */
  $$("[data-scroll]").forEach(function (b) {
    b.addEventListener("click", function () {
      var row = document.getElementById(b.getAttribute("data-target"));
      if (row) row.scrollBy({ left: parseInt(b.getAttribute("data-scroll"), 10) * 240, behavior: reduced ? "auto" : "smooth" });
    });
  });

  /* ---------- profile calendar ("Project days") ---------- */
  var cal = $("#cal-root");
  if (cal) {
    var MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];
    var DOWS = ["Mo","Tu","We","Th","Fr","Sa","Su"];
    var days = {};
    try { days = JSON.parse(cal.getAttribute("data-days") || "{}"); } catch (e) {}
    var today = cal.getAttribute("data-today") || new Date().toISOString().slice(0, 10);
    var ym = { y: +today.slice(0, 4), m: +today.slice(5, 7) - 1 };
    var keys = Object.keys(days).sort();
    var minYM = keys.length ? (+keys[0].slice(0, 4)) * 12 + (+keys[0].slice(5, 7) - 1) : ym.y * 12 + ym.m;
    var maxYM = ym.y * 12 + ym.m;
    var grid = $("#cal-grid"), label = $("#cal-label"), foot = $("#cal-count");
    var pv = $("#cal-prev"), nx = $("#cal-next");
    var pad = function (v) { return (v < 10 ? "0" : "") + v; };
    var render = function () {
      var lead = (new Date(Date.UTC(ym.y, ym.m, 1)).getUTCDay() + 6) % 7;
      var dim = new Date(Date.UTC(ym.y, ym.m + 1, 0)).getUTCDate();
      var html = DOWS.map(function (d) { return '<div class="dow" aria-hidden="true">' + d + "</div>"; }).join("");
      for (var b = 0; b < lead; b++) html += '<span class="blank"></span>';
      var total = 0;
      for (var d = 1; d <= dim; d++) {
        var key = ym.y + "-" + pad(ym.m + 1) + "-" + pad(d);
        var c = days[key] || 0; total += c;
        var future = key > today;
        var cls = "day " + (future ? "future" : "l" + Math.min(c, 3)) + (key === today ? " today" : "");
        var lab = d + " " + MONTHS[ym.m] + ": " + (future ? "upcoming" : c === 0 ? "no projects" : c + (c === 1 ? " project" : " projects"));
        html += '<button type="button" class="' + cls + '"' + (future ? " disabled" : "") + ' aria-label="' + lab + '">' + d + "</button>";
      }
      grid.innerHTML = html;
      label.textContent = MONTHS[ym.m] + " " + ym.y;
      foot.textContent = total === 0 ? "No projects this month" : total + (total === 1 ? " project" : " projects") + " this month";
      var cur = ym.y * 12 + ym.m;
      pv.disabled = cur <= minYM; nx.disabled = cur >= maxYM;
    };
    var step = function (k) {
      var m = ym.m + k, y = ym.y;
      if (m < 0) { m = 11; y--; } if (m > 11) { m = 0; y++; }
      ym = { y: y, m: m }; render();
    };
    pv.addEventListener("click", function () { step(-1); });
    nx.addEventListener("click", function () { step(1); });
    render();
  }

  /* ---------- show / hide password (login and signup) ---------- */
  $$("[data-show-password]").forEach(function (b) {
    b.addEventListener("click", function () {
      var inputs = $$(b.getAttribute("data-show-password"));
      var show = b.getAttribute("aria-pressed") !== "true";
      inputs.forEach(function (i) { i.type = show ? "text" : "password"; });
      b.setAttribute("aria-pressed", show ? "true" : "false");
      b.textContent = show ? "Hide password" : "Show password";
    });
  });
})();

/* show a waiting message while the local AI works (it can take up to a minute) */
document.addEventListener("submit", function (e) {
  var f = e.target;
  if (f && f.getAttribute && f.getAttribute("action") === "/result") {
    var b = f.querySelector('button[type="submit"]');
    if (b) { b.textContent = "Gemma is thinking... please wait"; setTimeout(function () { b.disabled = true; }, 0); }
  }
});
