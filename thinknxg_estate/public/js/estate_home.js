/* Landing page of /properties: hero search tabs, suggestions, budget choices and recent searches. */
(function () {
  "use strict";
  var E = window.ESTATE, H = window.ESTATE_HOME, $ = E.$, $$ = E.$$;
  var form = $("#hero-search"); if (!form) { return; }
  E.suggestHeads = { city: H.T.cities, locality: H.T.areas, listing: H.T.listing };
  var q = $("#s-q"), city = $("#s-city"), loc = $("#s-locality"), budget = $("#s-budget");
  var purpose = $("#s-purpose"), usage = $("#s-usage"), dev = $("#s-dev");

  // Budget choices follow the price range of what is for rent or sale
  function nice(n) { var p = Math.pow(10, Math.max(Math.floor(Math.log10(n)) - 1, 0)); return Math.round(n / p) * p; }
  function fmt(n) { return Number(n).toLocaleString(); }
  function buildBudget(tab) {
    var range = tab === "Rent" ? H.price.Rent : tab === "Sale" ? H.price.Sale : null;
    if (!range) { var all = [].concat(H.price.Rent || [], H.price.Sale || []).filter(Boolean); range = all.length ? [Math.min.apply(0, all), Math.max.apply(0, all)] : null; }
    budget.innerHTML = '<option value="">' + E.esc(H.T.any) + "</option>";
    if (!range || !range[1] || range[0] === range[1]) { return; }
    var lo = range[0], hi = range[1], steps = [], n = 4;
    for (var i = 1; i <= n; i++) { steps.push(nice(lo * Math.pow(hi / lo, i / n))); }
    steps = steps.filter(function (v, i) { return v > 0 && steps.indexOf(v) === i; });
    steps.forEach(function (v, i) {
      budget.insertAdjacentHTML("beforeend", '<option value="0-' + v + '">' + E.esc(H.T.upTo.replace("{0}", fmt(v))) + "</option>");
      if (i === steps.length - 1) { budget.insertAdjacentHTML("beforeend", '<option value="' + v + '-">' + E.esc(H.T.over.replace("{0}", fmt(v))) + "</option>"); }
    });
  }
  function setTab(tab) {
    $$(".eb-tab", form).forEach(function (t) { var on = t.dataset.tab === tab; t.classList.toggle("on", on); t.setAttribute("aria-selected", on); });
    purpose.value = tab === "Rent" || tab === "Sale" ? tab : ""; purpose.disabled = !purpose.value;
    usage.value = tab === "Commercial" ? "Commercial" : ""; usage.disabled = !usage.value;
    dev.disabled = tab !== "Projects";
    buildBudget(tab);
  }
  $$(".eb-tab", form).forEach(function (t) { t.addEventListener("click", function () { setTab(t.dataset.tab); }); });
  setTab("Rent");

  E.attachSuggest(q, $("#s-suggest"), function (it) {
    if (it.type === "listing") { location.href = "/" + it.value; return; }
    q.value = it.value; city.value = it.type === "city" ? it.value : (it.sub || ""); loc.value = it.type === "locality" ? it.value : "";
    if (it.type === "locality" && it.sub) { city.value = ""; }
  });
  q.addEventListener("input", function () { city.value = ""; loc.value = ""; });

  form.addEventListener("submit", function () {
    // Keep the address clean: the picked place replaces the free text, empty fields are not sent.
    if (city.value || loc.value) { q.disabled = true; }
    var m = budget.value.split("-");
    if (budget.value) { $("#s-min").value = m[0] > 0 ? m[0] : ""; $("#s-max").value = m[1] || ""; $("#s-min").disabled = !$("#s-min").value; $("#s-max").disabled = !$("#s-max").value; }
    $$("input, select", form).forEach(function (el) { if (el.name && !el.disabled && el.value === "") { el.disabled = true; } });
    var label = q.value || city.value || loc.value;
    if (label) {
      var list = E.load("estate_recent_searches").filter(function (x) { return x.label !== label; });
      list.unshift({ label: label, qs: $$("input, select", form).filter(function (el) { return el.name && !el.disabled; }).map(function (el) { return encodeURIComponent(el.name) + "=" + encodeURIComponent(el.value); }).join("&") });
      E.store("estate_recent_searches", list.slice(0, 4));
    }
  });

  // Recent searches (this browser only)
  var recent = E.load("estate_recent_searches"), box = $("#recent-searches");
  if (recent.length && box) {
    recent.forEach(function (r) { var a = document.createElement("a"); a.href = "/properties?" + r.qs; a.textContent = r.label; box.appendChild(a); });
    box.hidden = false;
  }
})();
