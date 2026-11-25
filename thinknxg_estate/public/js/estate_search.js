/* Search page of /properties: filters, chips, sorting, grid / list / map, saved searches.
   The server renders the first page; every later change asks catalog.search_results for the
   matching cards (filtering always happens in the database, never in the browser) and keeps
   the address bar in step, so the back button, reloads and shared links all work. */
(function () {
  "use strict";
  var E = window.ESTATE, S = window.ESTATE_SEARCH, T = S.T, $ = E.$, $$ = E.$$;
  var cards = $("#cards"), form = $("#filter-form");
  var MULTI = ["city", "locality", "unit_type", "furnishing", "amenity"];
  var PILLS = ["listing_type", "usage", "development_status", "bedrooms", "bathrooms"];
  var NUMBERS = ["min_price", "max_price", "min_area", "max_area"];
  var FLAGS = ["featured", "new", "permit"];
  var EXTRA = ["category", "project", "north", "south", "east", "west"];
  var state = { view: S.view, page: S.page, extra: {}, seq: 0, last: null };
  EXTRA.forEach(function (k) { if (S.args[k]) { state.extra[k] = S.args[k]; } });

  // ---------- read and write the form ----------
  function pillValue(name) { var on = $('[data-pills="' + name + '"] .on'); return on ? on.dataset.value : ""; }
  function setPill(name, value) {
    $$('[data-pills="' + name + '"] .eb-pill').forEach(function (p) { p.classList.toggle("on", String(p.dataset.value).toLowerCase() === String(value || "").toLowerCase()); });
    if (name === "listing_type") { $$("#purpose-seg button").forEach(function (b) { b.classList.toggle("on", b.dataset.value === (value || "")); }); }
  }
  function params() {
    var p = {};
    var q = $("#f-q").value.trim(); if (q) { p.q = q; }
    PILLS.forEach(function (k) { var v = pillValue(k); if (v) { p[k] = v; } });
    MULTI.forEach(function (k) { var v = $$('input[name="' + k + '"]:checked', form).map(function (i) { return i.value; }); if (v.length) { p[k] = v.join(","); } });
    NUMBERS.forEach(function (k) { var v = $("#" + k); if (v && v.value && +v.value > 0) { p[k] = v.value; } });
    FLAGS.forEach(function (k) { var c = $('input[name="' + k + '"]', form); if (c && c.checked) { p[k] = "1"; } });
    var sort = $("#f-sort").value; if (sort && sort !== "relevance") { p.sort = sort; }
    Object.keys(state.extra).forEach(function (k) { p[k] = state.extra[k]; });
    return p;
  }
  function qs(p, extra) {
    var o = Object.assign({}, p, extra || {}); var out = [];
    Object.keys(o).forEach(function (k) { if (o[k] !== "" && o[k] != null) { out.push(encodeURIComponent(k) + "=" + encodeURIComponent(o[k])); } });
    return out.join("&");
  }
  function fromUrl() {
    var u = new URLSearchParams(location.search), a = {};
    u.forEach(function (v, k) { a[k] = v; });
    $("#f-q").value = a.q || "";
    PILLS.forEach(function (k) { setPill(k, a[k] || ""); });
    MULTI.forEach(function (k) { var set = (a[k] || "").split(","); $$('input[name="' + k + '"]', form).forEach(function (i) { i.checked = set.indexOf(i.value) > -1; }); });
    NUMBERS.forEach(function (k) { var v = $("#" + k); if (v) { v.value = a[k] || ""; } });
    FLAGS.forEach(function (k) { var c = $('input[name="' + k + '"]', form); if (c) { c.checked = !!a[k]; } });
    $("#f-sort").value = a.sort || "relevance";
    state.extra = {}; EXTRA.forEach(function (k) { if (a[k]) { state.extra[k] = a[k]; } });
    state.view = a.view || "grid"; state.page = parseInt(a.page, 10) || 1;
    syncPrice(); syncLocalities(); syncViewButtons();
  }

  // ---------- loading results ----------
  function skeleton(n) {
    var h = ""; for (var i = 0; i < n; i++) { h += '<div class="eb-skel"><i class="im"></i><i class="ln"></i><i class="ln s"></i><i class="ln" style="margin-bottom:18px"></i></div>'; }
    return h;
  }
  function render(r) {
    cards.innerHTML = r.html; cards.classList.remove("busy");
    $("#empty").hidden = r.total > 0;
    $("#r-summary").textContent = r.summary; $("#r-heading").textContent = r.heading;
    $$(".n-total").forEach(function (n) { n.textContent = r.total; });
    $("#pager").innerHTML = r.pager;
    $("#chips").innerHTML = r.chips.map(function (c) {
      return '<button type="button" class="eb-chip" data-key="' + E.esc(c.key) + '" data-value="' + E.esc(c.value || "") + '">' + E.esc(c.label) + '<svg class="i"><use href="#i-x"/></svg></button>';
    }).join("") + (r.chips.length > 1 ? '<button type="button" class="eb-linkbtn" data-clear-all>' + E.esc(S.clearLabel || $("#clear-all").textContent) + "</button>" : "");
    var badge = $("#filters-open"); if (badge) {
      var n = r.chips.filter(function (c) { return c.key !== "q"; }).length, b = $(".eb-dot", badge);
      if (n && !b) { badge.insertAdjacentHTML("beforeend", ' <b class="eb-dot" style="position:static"></b>'); b = $(".eb-dot", badge); }
      if (b) { n ? (b.textContent = n) : b.remove(); }
    }
    E.refreshCompare && E.refreshCompare();
    applyLayout();
  }
  function load(page, opts) {
    opts = opts || {}; var p = params(); state.page = page || 1;
    var key = qs(p, { page: state.page > 1 ? state.page : "", view: state.view !== "grid" ? state.view : "" });
    if (key === state.last && !opts.force) { return; }
    state.last = key;
    if (!opts.noPush) { history.pushState({}, "", key ? "?" + key : location.pathname); }
    var seq = ++state.seq;
    cards.classList.add("busy");
    var skel = setTimeout(function () { if (seq === state.seq) { cards.innerHTML = skeleton(state.view === "list" ? 3 : 6); cards.classList.remove("busy"); } }, 350);
    frappe.call({ method: "thinknxg_estate.portal.api.catalog.search_results", type: "GET",
      args: Object.assign({}, p, { page: state.page, layout: state.view === "list" ? "list" : "grid", view: state.view }),
      callback: function (r) { clearTimeout(skel); if (seq !== state.seq) { return; } render(r.message); document.title = r.message.heading + " | " + document.title.split(" | ").pop();
        if (opts.scroll !== false) { var top = $(".eb-toolbar").getBoundingClientRect().top + window.scrollY - 90; if (state.view !== "map" && window.scrollY > top) { window.scrollTo({ top: top, behavior: "smooth" }); } }
        if (state.view === "map") { mapRefresh(); } },
      error: function () { clearTimeout(skel); cards.classList.remove("busy"); E.toast(E.T.error); } });
  }
  var loadSoon = E.debounce(function () { load(1); }, 380);
  var loadNow = E.debounce(function () { load(1); }, 120);

  // ---------- filter controls ----------
  form.addEventListener("change", function (e) {
    if (e.target.name === "city") { syncLocalities(); }
    if (!e.target.matches('input[type="range"]')) { loadNow(); }
  });
  form.addEventListener("click", function (e) {
    var pill = e.target.closest(".eb-pill"); if (!pill) { return; }
    var name = pill.parentNode.dataset.pills; setPill(name, pill.dataset.value);
    if (name === "listing_type") { syncPrice(true); }
    loadNow();
  });
  $("#purpose-seg").addEventListener("click", function (e) {
    var b = e.target.closest("button"); if (!b) { return; } setPill("listing_type", b.dataset.value); syncPrice(true); loadNow();
  });
  $("#f-q").addEventListener("input", loadSoon);
  $("#f-q").addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); load(1); } });
  E.suggestHeads = { city: T.cities, locality: T.areas, listing: T.properties };
  E.attachSuggest($("#f-q"), $("#q-suggest"), function (it) {
    if (it.type === "listing") { location.href = "/" + it.value; return; }
    $("#f-q").value = ""; var cb = $$('input[name="' + it.type + '"]', form).filter(function (i) { return i.value === it.value; })[0];
    if (cb) { cb.checked = true; syncLocalities(); } else { $("#f-q").value = it.value; }
    load(1);
  });
  $("#f-sort").addEventListener("change", function () { load(1); });
  NUMBERS.forEach(function (k) { var el = $("#" + k); if (el) { el.addEventListener("input", function () { if (k.indexOf("price") > -1) { syncSliderFromNumbers(); } loadSoon(); }); } });
  $$("[data-filter-list]").forEach(function (inp) {
    inp.addEventListener("input", function () {
      var needle = inp.value.trim().toLowerCase();
      $$(".eb-opt", $(inp.dataset.filterList)).forEach(function (o) { var hide = needle && o.textContent.toLowerCase().indexOf(needle) < 0; o.parentNode.hidden = o.parentNode.tagName === "SPAN" ? (hide || o.parentNode.dataset.hidecity === "1") : hide; });
    });
  });

  // localities shown follow the cities picked
  function syncLocalities() {
    var cities = $$('input[name="city"]:checked', form).map(function (i) { return i.value; });
    $$("#locality-list > span").forEach(function (s) {
      var hide = cities.length && cities.indexOf(s.dataset.city) < 0; s.dataset.hidecity = hide ? "1" : ""; s.hidden = !!hide;
      if (hide) { var cb = $("input", s); if (cb && cb.checked) { cb.checked = false; } }
    });
  }

  // ---------- budget slider ----------
  var lo = $("#price-lo"), hi = $("#price-hi"), minI = $("#min_price"), maxI = $("#max_price"), fill = $(".eb-range-fill");
  var bounds = [0, 0];
  function priceBounds() {
    var t = pillValue("listing_type"), r = t === "Rent" ? S.price.Rent : t === "Sale" ? S.price.Sale : null;
    if (!r) { var all = [].concat(S.price.Rent || [], S.price.Sale || []); r = all.length ? [Math.min.apply(0, all), Math.max.apply(0, all)] : [0, 0]; }
    return r;
  }
  function stepFor(max) { return Math.max(Math.pow(10, Math.floor(Math.log10(Math.max(max, 10))) - 2), 1); }
  function paintFill() {
    var span = (+lo.max - +lo.min) || 1, a = (+lo.value - +lo.min) / span * 100, b = (+hi.value - +lo.min) / span * 100;
    fill.style.insetInlineStart = a + "%"; fill.style.width = Math.max(b - a, 0) + "%";
  }
  function syncPrice(reset) {
    bounds = priceBounds(); var step = stepFor(bounds[1]);
    var min = Math.floor(bounds[0] / step) * step, max = Math.ceil(bounds[1] / step) * step;
    [lo, hi].forEach(function (r) { r.min = min; r.max = max; r.step = step; });
    $("#price-range").style.opacity = max > min ? 1 : .35; lo.disabled = hi.disabled = max <= min;
    if (reset) { minI.value = ""; maxI.value = ""; }
    lo.value = minI.value || min; hi.value = maxI.value || max; paintFill();
  }
  function syncSliderFromNumbers() { lo.value = minI.value || lo.min; hi.value = maxI.value || hi.max; paintFill(); }
  [lo, hi].forEach(function (r) {
    r.addEventListener("input", function () {
      if (+lo.value > +hi.value) { if (r === lo) { lo.value = hi.value; } else { hi.value = lo.value; } }
      minI.value = +lo.value > +lo.min ? lo.value : ""; maxI.value = +hi.value < +hi.max ? hi.value : ""; paintFill(); loadSoon();
    });
  });
  syncPrice();

  // ---------- chips, clear all, view, sort, pages ----------
  function clearOne(key, value) {
    if (MULTI.indexOf(key) > -1) { $$('input[name="' + key + '"]', form).forEach(function (i) { if (i.value === value) { i.checked = false; } }); if (key === "city") { syncLocalities(); } }
    else if (PILLS.indexOf(key) > -1) { setPill(key, ""); if (key === "listing_type") { syncPrice(true); } }
    else if (key === "price") { minI.value = ""; maxI.value = ""; syncPrice(); }
    else if (key === "area") { ["min_area", "max_area"].forEach(function (k) { var e = $("#" + k); if (e) { e.value = ""; } }); }
    else if (FLAGS.indexOf(key) > -1) { var c = $('input[name="' + key + '"]', form); if (c) { c.checked = false; } }
    else if (key === "q") { $("#f-q").value = ""; }
    else if (key === "map") { ["north", "south", "east", "west"].forEach(function (k) { delete state.extra[k]; }); }
    else { delete state.extra[key]; }
  }
  function clearAll() {
    PILLS.forEach(function (k) { setPill(k, ""); }); $$("input[type=checkbox]", form).forEach(function (i) { i.checked = false; });
    NUMBERS.forEach(function (k) { var e = $("#" + k); if (e) { e.value = ""; } }); $("#f-q").value = ""; $("#f-sort").value = "relevance";
    state.extra = {}; syncPrice(true); syncLocalities(); load(1);
  }
  document.addEventListener("click", function (e) {
    var chip = e.target.closest(".eb-chip"); if (chip) { clearOne(chip.dataset.key, chip.dataset.value); return load(1); }
    if (e.target.closest("[data-clear-all]") || e.target.closest("#clear-all") || e.target.closest("#clear-all-m")) { return clearAll(); }
    var pg = e.target.closest("#pager a[data-page]"); if (pg) { e.preventDefault(); return load(+pg.dataset.page); }
  });
  function applyLayout() {
    var list = state.view === "list"; cards.classList.toggle("list", list);
    $$(".pc", cards).forEach(function (c) { c.classList.toggle("pc-list", list); c.classList.toggle("pc-grid", !list); });
  }
  function syncViewButtons() { $$("#view-seg button").forEach(function (b) { b.classList.toggle("on", b.dataset.view === state.view); }); }
  $("#view-seg").addEventListener("click", function (e) {
    var b = e.target.closest("button"); if (!b) { return; } var v = b.dataset.view;
    if (v === state.view) { return; }
    if (v === "map" || state.view === "map") { var p = params(); var k = qs(p, { view: v !== "grid" ? v : "" }); location.href = "/properties" + (k ? "?" + k : ""); return; }
    state.view = v; syncViewButtons(); load(state.page, { force: true, scroll: false });
  });
  window.addEventListener("popstate", function () { fromUrl(); state.last = null; load(state.page, { noPush: true, force: true, scroll: false }); });

  // ---------- mobile filter drawer ----------
  var panel = $("#filters"), back = $("#filters-back");
  function drawer(open) { panel.classList.toggle("open", open); back.classList.toggle("show", open); document.body.classList.toggle("eb-lock", open); }
  var openBtn = $("#filters-open"); if (openBtn) { openBtn.addEventListener("click", function () { drawer(true); }); }
  $("#filters-close").addEventListener("click", function () { drawer(false); });
  $("#apply-filters").addEventListener("click", function () { drawer(false); });
  back.addEventListener("click", function () { drawer(false); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") { drawer(false); } });

  // ---------- save this search ----------
  $("#save-search").addEventListener("click", function () {
    if (!E.visitor) { return E.needSignIn(); }
    var p = params(); if (!Object.keys(p).length) { return E.toast(T.saveNeed); }
    E.call("thinknxg_estate.portal.api.visitor.save_search", { params: JSON.stringify(p) }, function () { E.toast(T.searchSaved); },
      function (r) { var m = ""; try { m = JSON.parse(JSON.parse(r._server_messages).pop()).message; } catch (x) {} E.toast(m || E.T.error); });
  });

  // ---------- map ----------
  var map, layer, pins = {}, programmatic = 0, moved = false;
  function compact(n) { try { return new Intl.NumberFormat(E.lang === "ar" ? "ar" : "en", { notation: "compact", maximumFractionDigits: 1 }).format(n); } catch (x) { return Math.round(n); } }
  function mapInit() {
    map = L.map("estate-map", { scrollWheelZoom: true, zoomControl: true }).setView(S.center, S.zoom);
    L.tileLayer(S.tile, { maxZoom: 19, attribution: S.attribution }).addTo(map);
    layer = L.layerGroup().addTo(map);
    var flag = function () { if (!programmatic) { moved = true; $("#search-area").classList.add("show"); } };
    map.on("dragend zoomend", flag);
    $("#search-area").addEventListener("click", function () {
      var b = map.getBounds(), r = function (n) { return Math.round(n * 1e5) / 1e5; };
      state.extra.north = r(b.getNorth()); state.extra.south = r(b.getSouth()); state.extra.east = r(b.getEast()); state.extra.west = r(b.getWest());
      moved = false; this.classList.remove("show"); load(1);
    });
    var toggle = $("#map-toggle");
    if (toggle) { toggle.addEventListener("click", function () { var s = $("#split"), on = s.classList.toggle("show-map"); $("span", toggle).textContent = on ? T.showList : T.showMap; if (on) { map.invalidateSize(); } }); }
    cards.addEventListener("mouseover", function (e) { var c = e.target.closest(".pc"); if (c && pins[c.dataset.name]) { pins[c.dataset.name].classList.add("on"); } });
    cards.addEventListener("mouseout", function (e) { var c = e.target.closest(".pc"); if (c && pins[c.dataset.name]) { pins[c.dataset.name].classList.remove("on"); } });
    mapRefresh();
  }
  function mapRefresh() {
    var p = params(); delete p.sort;
    frappe.call({ method: "thinknxg_estate.portal.api.listings.map_points", type: "GET", args: p, callback: function (r) {
      var m = r.message, pts = []; layer.clearLayers(); pins = {};
      m.points.forEach(function (pt) {
        var icon = L.divIcon({ className: "eb-pinwrap", iconSize: [0, 0], html: '<span class="eb-pin" data-name="' + E.esc(pt.name) + '">' + E.esc(compact(pt.headline_price || 0)) + "</span>" });
        var mk = L.marker([pt.lat, pt.lng], { icon: icon, title: pt.title, riseOnHover: true }).addTo(layer);
        mk.bindPopup('<div class="eb-pop-card">' + (pt.cover ? '<img src="' + encodeURI(pt.cover) + '" alt="">' : "") + "<b>" + E.esc(pt.title) + '</b><div class="p">' + E.esc(m.currency) + " " + E.esc(Number(pt.headline_price || 0).toLocaleString()) +
          " <small>" + E.esc(pt.price_period || "") + "</small></div><div>" + E.esc([pt.unit_type, pt.locality, pt.city].filter(Boolean).join(" · ")) + '</div><a class="go" href="/' + encodeURI(pt.route) + '">' + E.esc(T.view) + " →</a></div>", { minWidth: 230 });
        mk.on("click", function () { var c = $('.pc[data-name="' + pt.name + '"]', cards); $$(".pc.hl", cards).forEach(function (x) { x.classList.remove("hl"); }); if (c) { c.classList.add("hl"); c.scrollIntoView({ behavior: "smooth", block: "nearest" }); } });
        mk.on("popupclose", function () { $$(".pc.hl", cards).forEach(function (x) { x.classList.remove("hl"); }); });
        pts.push([pt.lat, pt.lng]); setTimeout(function () { pins[pt.name] = $('.eb-pin[data-name="' + pt.name + '"]'); }, 0);
      });
      var hasBox = state.extra.north !== undefined;
      programmatic++;
      if (pts.length && !hasBox) { map.fitBounds(pts, { padding: [50, 50], maxZoom: 15 }); }
      setTimeout(function () { programmatic--; }, 400);
      $("#map-note").textContent = m.points.length ? (m.points.length < m.matching ? T.pins.replace("{0}", m.points.length).replace("{1}", m.matching) : "") : T.noPins;
      $("#map-note").style.display = $("#map-note").textContent ? "block" : "none";
    } });
  }
  if (state.view === "map" && window.L) { mapInit(); }
  applyLayout();
})();
