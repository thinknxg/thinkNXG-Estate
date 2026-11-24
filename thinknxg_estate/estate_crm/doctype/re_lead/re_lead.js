frappe.ui.form.on("RE Lead", {
	refresh(frm) {
		if (!frm.is_new() && !frm.doc.deal &&
			!["Converted", "Disqualified"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Create Deal"), () =>
				frm.call("make_deal").then((r) =>
					frappe.set_route("Form", "RE Deal", r.message))
			).addClass("btn-primary");
		}
		if (!frm.is_new() && frm.doc.status === "New") {
			frm.add_custom_button(__("Mark Contacted"), () => {
				frm.set_value("status", "Contacted");
				frm.save();
			});
		}
		render_matches(frm);
	},
	interest_type: render_matches,
	preferred_property_type: render_matches,
	preferred_location: render_matches,
	budget_min: render_matches,
	budget_max: render_matches,
	bedrooms_required: render_matches,
	min_area_sqm: render_matches,
	possession_date: render_matches,
});

function render_matches(frm) {
	const wrapper = frm.get_field("matching_html");
	if (!wrapper || frm.is_new()) return;
	if (frm.is_dirty()) {
		wrapper.$wrapper.html(`<p class="text-muted small">${__("Save the lead to refresh matching properties.")}</p>`);
		return;
	}
	frappe.call({
		method: "thinknxg_estate.crm.matching.get_matching_units",
		args: { lead: frm.doc.name, limit: 8 },
		callback(r) {
			const rows = r.message || [];
			if (!rows.length) {
				wrapper.$wrapper.html(`<p class="text-muted">${__("No available unit matches these requirements yet.")}</p>`);
				return;
			}
			const body = rows.map((m) => `
				<tr>
					<td><a href="/app/unit/${encodeURIComponent(m.unit)}">${frappe.utils.escape_html(m.unit_title || m.unit)}</a>
						<div class="small text-muted">${frappe.utils.escape_html(m.property_name || "")} · ${frappe.utils.escape_html(m.locality || m.city || "")}</div></td>
					<td>${frappe.utils.escape_html(m.unit_type || "")}${m.bedrooms ? " · " + m.bedrooms + " " + __("BR") : ""}</td>
					<td class="text-right">${format_currency(m.price)}</td>
					<td><span class="indicator-pill ${m.score >= 75 ? "green" : m.score >= 55 ? "blue" : "orange"}">${m.score}%</span>
						<div class="small text-muted">${m.reasons.map(frappe.utils.escape_html).join(", ")}</div></td>
					<td><button class="btn btn-xs btn-default" data-unit="${frappe.utils.escape_html(m.unit)}">${__("Set as interest")}</button></td>
				</tr>`).join("");
			wrapper.$wrapper.html(`
				<table class="table table-sm">
					<thead><tr><th>${__("Unit")}</th><th>${__("Type")}</th><th class="text-right">${__("Price")}</th><th>${__("Match")}</th><th></th></tr></thead>
					<tbody>${body}</tbody>
				</table>`);
			wrapper.$wrapper.find("button[data-unit]").on("click", function () {
				frm.set_value("unit_of_interest", $(this).attr("data-unit"));
				frm.save();
			});
		},
	});
}
