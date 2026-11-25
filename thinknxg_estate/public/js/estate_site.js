/* thinkNXG Estate public site: behaviour shared by every page (header, hearts, card slideshows,
   compare, toasts). Page-specific code lives in estate_search.js and estate_detail.js.
   All handlers are delegated, so cards inserted by the search page work without re-binding. */
(function () {
  "use strict";
  var E = window.ESTATE = window.ESTATE || {};
  var T = E.T || {};
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  E.$ = $; E.$$ = $$;

  E.toast = function (msg) {
    var t = $("#toast"); if (!t) { return; }
    t.textContent = msg; t.style.display = "block";
    clearTimeout(t._h); t._h = setTimeout(function () { t.style.display = "none"; }, 2600);
  };
  E.needSignIn = function () {
    E.toast(T.signin);
    setTimeout(function () {
      location.href = "/properties/account?next=" + encodeURIComponent(location.pathname + location.search);
    }, 900);
  };
  E.call = function (method, args, ok, fail) {
    frappe.call({ method: method, args: args, type: "POST",
      callback: function (r) { ok && ok(r.message); },
      error: function (r) { if (fail) { return fail(r); } if (r && r.status === 403) { E.needSignIn(); } else { E.toast(T.error); } } });
  };
  E.debounce = function (fn, ms) { var h; return function () { var a = arguments, c = this; clearTimeout(h); h = setTimeout(function () { fn.apply(c, a); }, ms); }; };
  E.esc = function (s) { var d = document.createElement("div"); d.textContent = s == null ? "" : String(s); return d.innerHTML; };

  // Header: shadow once scrolled, mobile drawer, dropdown menus, language switch
  var header = $("#eb-header");
  if (header) {
    var onScroll = function () { header.classList.toggle("scrolled", window.scrollY > 6); };
    onScroll(); window.addEventListener("scroll", onScroll, { passive: true });
  }
  var drawer = $("#eb-drawer"), burger = $("#eb-burger");
  function drawerOpen(open) {
    if (!drawer) { return; }
    drawer.hidden = !open; burger.setAttribute("aria-expanded", open ? "true" : "false");
    document.body.classList.toggle("eb-lock", open);
    if (open) { var a = $("a", drawer); a && a.focus(); } else { burger.focus(); }
  }
  if (burger) { burger.addEventListener("click", function () { drawerOpen(true); }); }
  if (drawer) { drawer.addEventListener("click", function (e) { if (e.target.closest("[data-close]")) { drawerOpen(false); } }); }
  $$("[data-menu]").forEach(function (m) {
    var btn = $("[data-menu-btn]", m);
    btn.addEventListener("click", function (e) { e.stopPropagation(); var o = !m.classList.contains("open"); $$("[data-menu]").forEach(function (x) { x.classList.remove("open"); }); m.classList.toggle("open", o); btn.setAttribute("aria-expanded", o); });
  });
  document.addEventListener("click", function (e) { if (!e.target.closest("[data-menu]")) { $$("[data-menu]").forEach(function (x) { x.classList.remove("open"); }); } });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { drawer && !drawer.hidden && drawerOpen(false); $$("[data-menu]").forEach(function (x) { x.classList.remove("open"); }); }
  });
  function switchLang(code) {
    document.cookie = "preferred_language=" + code + "; path=/; max-age=31536000; samesite=lax";
    var done = function () { var u = new URL(location.href); u.searchParams.delete("_lang"); location.href = u.toString(); };
    if (E.visitor) { E.call("thinknxg_estate.portal.api.visitor.set_language", { language: code }, done, done); } else { done(); }
  }
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-lang]"); if (b) { e.preventDefault(); switchLang(b.dataset.lang); }
  });

  // Wishlist hearts (cards and detail page)
  document.addEventListener("click", function (e) {
    var btn = e.target.closest(".pc-heart"); if (!btn) { return; }
    e.preventDefault();
    if (!E.visitor) { return E.needSignIn(); }
    E.call("thinknxg_estate.portal.api.visitor.toggle_wishlist", { listing: btn.dataset.listing }, function (m) {
      btn.classList.toggle("on", !!m.saved); btn.setAttribute("aria-pressed", m.saved ? "true" : "false");
      btn.classList.add("pop"); setTimeout(function () { btn.classList.remove("pop"); }, 400);
      E.toast(m.saved ? T.saved : T.removed);
      $$('.pc-heart[data-listing="' + btn.dataset.listing + '"]').forEach(function (h) { h.classList.toggle("on", !!m.saved); });
    });
  });

  // Card photo slideshow; later photos load only when first needed
  document.addEventListener("click", function (e) {
    var nav = e.target.closest(".pc-nav"); if (!nav) { return; }
    e.preventDefault(); e.stopPropagation();
    var media = nav.closest(".pc-media"), slides = $$(".pc-slide", media);
    var cur = slides.findIndex(function (s) { return s.classList.contains("on"); });
    var next = (cur + (nav.classList.contains("pc-next") ? 1 : -1) + slides.length) % slides.length;
    var s = slides[next]; if (s.dataset.src) { s.src = s.dataset.src; s.removeAttribute("data-src"); }
    slides[cur].classList.remove("on"); s.classList.add("on");
    var pos = $(".pc-pos", media); if (pos) { pos.textContent = next + 1; }
  });

  // Compare (remembered in this browser only; max three)
  var KEY = "estate_compare";
  function load(k) { try { return JSON.parse(localStorage.getItem(k) || "[]"); } catch (x) { return []; } }
  function store(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (x) {} }
  E.load = load; E.store = store;
  var picked = load(KEY);
  E.paintCompare = function () {
    var bar = $("#comparebar"); if (!bar) { return; }
    bar.classList.toggle("show", picked.length > 0);
    $("#compare-count").textContent = (T.selected || "{0}").replace("{0}", picked.length);
    $("#compare-go").href = "/properties/compare?l=" + picked.map(encodeURIComponent).join(",");
    $$(".compare-box").forEach(function (b) { b.checked = picked.indexOf(b.dataset.listing) > -1; });
    $$("[data-compare]").forEach(function (b) { b.classList.toggle("on", picked.indexOf(b.dataset.compare) > -1); });
  };
  E.toggleCompare = function (name, on) {
    var i = picked.indexOf(name);
    if (on && i < 0) { if (picked.length >= 3) { E.toast(T.compareMax); return false; } picked.push(name); }
    if (!on && i > -1) { picked.splice(i, 1); }
    store(KEY, picked); E.paintCompare(); return true;
  };
  document.addEventListener("change", function (e) {
    var b = e.target.closest(".compare-box"); if (b && !E.toggleCompare(b.dataset.listing, b.checked)) { b.checked = false; }
  });
  var clear = $("#compare-clear");
  if (clear) { clear.addEventListener("click", function () { picked = []; store(KEY, picked); E.paintCompare(); }); }
  E.paintCompare();
  E.refreshCompare = E.paintCompare;

  // Search suggestions (hero and results search box): cities, areas and property names
  E.attachSuggest = function (input, box, onPick) {
    var items = [], act = -1, seq = 0;
    function close() { box.classList.remove("open"); input.setAttribute("aria-expanded", "false"); act = -1; }
    function paint() {
      var html = "", last = "";
      var heads = E.suggestHeads || {};
      items.forEach(function (it, i) {
        if (it.type !== last) { html += '<div class="hd">' + E.esc(heads[it.type] || "") + "</div>"; last = it.type; }
        var icon = it.type === "listing" ? "i-building" : "i-pin";
        html += '<button type="button" role="option" data-i="' + i + '"><svg class="i"><use href="#' + icon + '"/></svg><span>' + E.esc(it.label) +
          (it.sub ? ' <small style="margin:0;opacity:.7">' + E.esc(it.sub) + "</small>" : "") + "</span>" + (it.count ? "<small>" + it.count + "</small>" : "") + "</button>";
      });
      box.innerHTML = html; box.classList.toggle("open", items.length > 0); input.setAttribute("aria-expanded", items.length > 0 ? "true" : "false");
    }
    var fetchIt = E.debounce(function () {
      var q = input.value.trim(); if (q.length < 2) { items = []; return close(); }
      var mine = ++seq;
      frappe.call({ method: "thinknxg_estate.portal.api.catalog.suggest", type: "GET", args: { q: q }, callback: function (r) {
        if (mine !== seq) { return; } items = (r.message && r.message.items) || []; act = -1; paint(); } });
    }, 220);
    input.addEventListener("input", fetchIt);
    input.addEventListener("keydown", function (e) {
      if (!items.length || !box.classList.contains("open")) { return; }
      var btns = E.$$("button", box);
      if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); act = (act + (e.key === "ArrowDown" ? 1 : -1) + btns.length) % btns.length; btns.forEach(function (b, i) { b.classList.toggle("act", i === act); }); }
      else if (e.key === "Enter" && act > -1) { e.preventDefault(); onPick(items[act]); close(); }
      else if (e.key === "Escape") { close(); }
    });
    box.addEventListener("mousedown", function (e) { var b = e.target.closest("button[data-i]"); if (b) { e.preventDefault(); onPick(items[+b.dataset.i]); close(); } });
    document.addEventListener("click", function (e) { if (!e.target.closest(".eb-suggest") && e.target !== input) { close(); } });
    return { close: close };
  };
})();
