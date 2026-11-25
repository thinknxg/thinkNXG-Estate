const API = "thinknxg_estate.portal.api.theme_admin.";
const esc = frappe.utils.escape_html;

frappe.ui.form.on("Portal Theme Settings", {
	refresh(frm) {
		frm.disable_save();
		frm.add_custom_button(__("New Theme"), () => frappe.new_doc("Portal Theme"));
		frm.add_custom_button(__("Open Live Site"), () => window.open("/properties", "_blank"));
		load(frm);
	},
});

function swatches(list) {
	return `<span style="display:inline-flex;border-radius:6px;overflow:hidden;border:1px solid var(--border-color)">${list.map((c) => `<i style="display:block;width:22px;height:22px;background:${esc(c)}"></i>`).join("")}</span>`;
}

function load(frm) {
	frappe.call({ method: API + "gallery", callback: (r) => render(frm, r.message) });
}

function render(frm, data) {
	const tpls = Object.fromEntries(data.templates.map((t) => [t.name, t]));
	const themeCard = (t) => `
		<div class="frappe-card" style="padding:14px;margin-bottom:12px;display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap">
			<div><b>${esc(t.name)}</b> <span class="indicator-pill ${t.live ? "green" : "gray"}">${t.live ? __("Live") : __("Draft")}</span>
				<div class="text-muted small">${__("Template")}: ${esc((tpls[t.template] || {}).label || t.template)}
				${t.published_on ? " · " + __("Published {0}", [frappe.datetime.str_to_user(t.published_on)]) : ""}</div></div>
			<div class="btn-group">
				<button class="btn btn-default btn-sm" data-act="edit" data-name="${esc(t.name)}">${__("Edit")}</button>
				<button class="btn btn-default btn-sm" data-act="preview" data-name="${esc(t.name)}">${__("Preview")}</button>
				${t.live ? "" : `<button class="btn btn-primary btn-sm" data-act="publish" data-name="${esc(t.name)}">${__("Publish")}</button>`}
			</div>
		</div>`;
	const tplCard = (t) => `
		<div class="frappe-card" style="padding:14px;margin:0 12px 12px 0;width:260px;display:inline-block;vertical-align:top">
			${swatches(t.swatches)} ${t.dark ? `<span class="indicator-pill blue">${__("Dark")}</span>` : ""}
			<h5 style="margin:10px 0 4px">${esc(t.label)}</h5>
			<p class="text-muted small" style="min-height:62px">${esc(t.description)}</p>
			<button class="btn btn-default btn-sm" data-act="create" data-name="${esc(t.name)}">${__("Create a Theme from This")}</button>
		</div>`;
	const html = `
		<h4 style="margin:6px 0 12px">${__("Your themes")}</h4>
		${data.themes.length ? data.themes.map(themeCard).join("") : `<p class="text-muted">${__("No themes yet.")}</p>`}
		<h4 style="margin:24px 0 12px">${__("Start from a template")}</h4>
		<div>${data.templates.map(tplCard).join("")}</div>`;
	const $w = frm.get_field("gallery").$wrapper;
	$w.html(html);
	$w.find("button[data-act]").on("click", function () {
		const name = this.dataset.name, act = this.dataset.act;
		if (act === "edit") { frappe.set_route("Form", "Portal Theme", name); }
		if (act === "create") {
			frappe.call({ method: API + "create_from_template", args: { template: name }, freeze: true,
				callback: (r) => frappe.set_route("Form", "Portal Theme", r.message) });
		}
		if (act === "publish") {
			frappe.confirm(__("Publish {0}? Visitors will see this design straight away.", [name]), () =>
				frappe.call({ method: API + "publish", args: { theme: name }, freeze: true,
					callback: () => { frappe.show_alert({ message: __("Published"), indicator: "green" }); frm.reload_doc(); } }));
		}
		if (act === "preview") {
			frappe.call({ method: API + "preview_links", args: { theme: name }, callback: (r) => window.open(r.message[0].url, "_blank") });
		}
	});
}
