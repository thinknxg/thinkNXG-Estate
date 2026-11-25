/* Property detail page: photo viewer, inquiry and viewing form, save / compare / share,
   payment plan, lease request, location map and recently viewed. */
(function () {
  "use strict";
  var E = window.ESTATE, D = window.ESTATE_DETAIL, T = D.T, $ = E.$, $$ = E.$$;

  // ---------- photo viewer ----------
  var lb = $("#lightbox"), cur = 0, imgs = D.gallery;
  function show(i) {
    cur = (i + imgs.length) % imgs.length;
    $("#lb-img").src = imgs[cur]; $("#lb-img").alt = D.title + " – " + T.photoOf.replace("{0}", cur + 1).replace("{1}", imgs.length);
    $("#lb-count").textContent = T.photoOf.replace("{0}", cur + 1).replace("{1}", imgs.length);
    $$("#lb-thumbs img").forEach(function (t, k) { t.classList.toggle("on", k === cur); });
    var on = $("#lb-thumbs img.on"); on && on.scrollIntoView({ inline: "center", block: "nearest" });
  }
  function openLb(i) {
    if (!imgs.length) { return; }
    if (!$("#lb-thumbs").children.length) { $("#lb-thumbs").innerHTML = imgs.map(function (s, k) { return '<img src="' + encodeURI(s) + '" alt="" data-k="' + k + '" loading="lazy">'; }).join(""); }
    lb.classList.add("open"); document.body.classList.add("eb-lock"); show(i); $("#lb-close").focus();
  }
  function closeLb() { lb.classList.remove("open"); document.body.classList.remove("eb-lock"); }
  $$("#gallery [data-i]").forEach(function (b) { b.addEventListener("click", function () { openLb(+b.dataset.i); }); });
  if (imgs.length < 2) { $("#lb-prev").hidden = $("#lb-next").hidden = true; }
  $("#lb-close").addEventListener("click", closeLb);
  $("#lb-prev").addEventListener("click", function () { show(cur - 1); });
  $("#lb-next").addEventListener("click", function () { show(cur + 1); });
  $("#lb-thumbs").addEventListener("click", function (e) { var t = e.target.closest("img"); if (t) { show(+t.dataset.k); } });
  lb.addEventListener("click", function (e) { if (e.target === lb || e.target.classList.contains("eb-lb-stage")) { closeLb(); } });
  document.addEventListener("keydown", function (e) {
    if (!lb.classList.contains("open")) { return; }
    var rtl = document.dir === "rtl" || document.documentElement.dir === "rtl";
    if (e.key === "Escape") { closeLb(); } else if (e.key === "ArrowRight") { show(cur + (rtl ? -1 : 1)); } else if (e.key === "ArrowLeft") { show(cur + (rtl ? 1 : -1)); }
  });
  var sx = 0; lb.addEventListener("touchstart", function (e) { sx = e.changedTouches[0].clientX; }, { passive: true });
  lb.addEventListener("touchend", function (e) { var dx = e.changedTouches[0].clientX - sx; if (Math.abs(dx) > 50) { show(cur + (dx < 0 ? 1 : -1)); } }, { passive: true });

  // ---------- inquiry / viewing ----------
  var rendered = new Date().toISOString().slice(0, 19).replace("T", " "), mode = "General";
  function setMode(m) {
    mode = m; $$(".eb-modes button").forEach(function (t) { t.classList.toggle("on", t.dataset.mode === m); });
    $("#inq-viewing").hidden = m !== "Viewing"; $("#inq-send").textContent = m === "Viewing" ? T.sendViewing : T.send;
  }
  $$(".eb-modes button").forEach(function (t) { t.addEventListener("click", function () { setMode(t.dataset.mode); }); });
  $$("[data-jump]").forEach(function (b) { b.addEventListener("click", function () {
    setMode(b.dataset.jump); $("#contact-card").scrollIntoView({ behavior: "smooth", block: "start" });
    setTimeout(function () { $("#inq-name").focus({ preventScroll: true }); }, 400); }); });
  $("#inq-send").addEventListener("click", function () {
    var btn = this; btn.disabled = true; $("#inq-err").textContent = "";
    frappe.call({
      method: "thinknxg_estate.portal.api.listings.submit_inquiry", type: "POST",
      args: { full_name: $("#inq-name").value, mobile: $("#inq-mobile").value, email: $("#inq-email").value, message: $("#inq-msg").value,
        listing: D.name, website_url: $("#inq-website-url").value, form_ts: rendered, inquiry_type: mode,
        preferred_date: mode === "Viewing" ? $("#inq-date").value : null, preferred_time_slot: mode === "Viewing" ? $("#inq-slot").value : null },
      callback: function () {
        var done = $("#inq-done"); done.textContent = mode === "Viewing" ? T.viewingDone : T.inquiryDone;
        $("#inq-form").hidden = true; $(".eb-modes").hidden = true; done.hidden = false;
      },
      error: function (r) {
        btn.disabled = false; var msg = "";
        try { msg = JSON.parse(JSON.parse(r._server_messages).pop()).message; var d = document.createElement("div"); d.innerHTML = msg; msg = d.textContent; } catch (x) {}
        $("#inq-err").textContent = msg || (r && r._server_messages ? T.check : E.T.error);
      } });
  });

  // ---------- save, compare, share ----------
  var save = $("#save-btn");
  save.addEventListener("click", function () {
    if (!E.visitor) { return E.needSignIn(); }
    E.call("thinknxg_estate.portal.api.visitor.toggle_wishlist", { listing: D.name }, function (m) {
      save.classList.toggle("on", !!m.saved); save.setAttribute("aria-pressed", m.saved ? "true" : "false");
      $("span", save).textContent = m.saved ? T.saved : T.save; E.toast(m.saved ? E.T.saved : E.T.removed);
    });
  });
  $("#cmp-btn").addEventListener("click", function () { E.toggleCompare(D.name, !this.classList.contains("on")); });
  E.paintCompare();
  $("#share-btn").addEventListener("click", function () {
    var data = { title: D.title, url: location.origin + "/" + D.route };
    if (navigator.share) { navigator.share(data).catch(function () {}); return; }
    var done = function () { E.toast(T.shared); };
    if (navigator.clipboard) { navigator.clipboard.writeText(data.url).then(done, done); } else { var i = document.createElement("input"); i.value = data.url; document.body.appendChild(i); i.select(); try { document.execCommand("copy"); } catch (x) {} i.remove(); done(); }
  });

  // ---------- payment plan ----------
  var seg = $("#plan-seg");
  if (seg) {
    var fmt = function (v) { return D.currency + " " + v.toLocaleString(undefined, { minimumFractionDigits: 3, maximumFractionDigits: 3 }); };
    var plan = function (n) {
      $$("button", seg).forEach(function (b) { b.classList.toggle("on", +b.dataset.n === n); });
      $("#plan-per").textContent = fmt(Math.round(D.annual / n * 1000) / 1000); $("#plan-month").textContent = fmt(Math.round(D.annual / 12 * 1000) / 1000);
    };
    $$("button", seg).forEach(function (b) { b.addEventListener("click", function () { plan(+b.dataset.n); }); }); plan(4);
  }

  // ---------- lease request ----------
  var lease = $("#lease-go");
  if (lease) { lease.addEventListener("click", function () {
    var msg = $("#lease-msg"); lease.disabled = true;
    frappe.call({ method: "thinknxg_estate.core.listing_portal_api.listing_portal.request_lease_contract", type: "POST",
      args: { unit: D.unit, start_date: $("#lease-start").value, duration_months: $("#lease-months").value },
      callback: function () { msg.style.color = "#047857"; msg.textContent = T.leaseDone; },
      error: function (r) { lease.disabled = false; msg.style.color = "#b91c1c"; var m = E.T.error; try { var d = document.createElement("div"); d.innerHTML = JSON.parse(JSON.parse(r._server_messages).pop()).message; m = d.textContent; } catch (x) {} msg.textContent = m; } });
  }); }

  // ---------- map ----------
  var mapEl = $("#listing-map");
  if (mapEl && window.L) {
    var ll = [parseFloat(mapEl.dataset.lat), parseFloat(mapEl.dataset.lng)];
    var m = L.map(mapEl, { scrollWheelZoom: false }).setView(ll, 15);
    L.tileLayer(D.tile, { maxZoom: 19, attribution: D.attribution }).addTo(m);
    L.marker(ll, { icon: L.divIcon({ className: "eb-pinwrap", iconSize: [0, 0], html: '<span class="eb-pin on">●</span>' }) }).addTo(m);
  }

  // ---------- recently viewed (this browser only) ----------
  var KEY = "estate_recent", seen = E.load(KEY).filter(function (n) { return n !== D.name; });
  E.store(KEY, [D.name].concat(seen).slice(0, 12));
  if (seen.length) {
    frappe.call({ method: "thinknxg_estate.portal.api.catalog.cards_by_name", type: "GET", args: { names: seen.slice(0, 4).join(",") }, callback: function (r) {
      if (r.message && r.message.count) { $("#recent-cards").innerHTML = r.message.html; $("#recent").hidden = false; E.paintCompare(); } } });
  }
})();
