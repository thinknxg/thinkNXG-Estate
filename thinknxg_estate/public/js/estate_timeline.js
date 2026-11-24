// "Communication History" for leads, deals, tenants, owners and properties.
(function () {
	const DOCTYPES = ["RE Lead", "RE Deal", "Tenant", "Property Owner", "Property"];

	function show(doctype, name) {
		frappe.call({
			method: "thinknxg_estate.channels.timeline.get_timeline",
			args: { doctype, name },
			callback(r) {
				const items = r.message || [];
				const esc = frappe.utils.escape_html;
				const html = items.length ? items.map((i) => `
					<div class="mb-3 pb-2 border-bottom">
						<div class="small text-muted">${frappe.datetime.str_to_user(i.at)} · ${esc(i.channel)}${i.direction ? " · " + esc(i.direction) : ""}</div>
						<div>${esc(i.summary || "")}</div>
						${i.reference_doctype ? `<a class="small" href="/app/${frappe.router.slug(i.reference_doctype)}/${encodeURIComponent(i.reference_name)}">${esc(i.reference_doctype)} ${esc(i.reference_name)}</a>` : ""}
					</div>`).join("") : `<p class="text-muted">${__("No communication recorded yet.")}</p>`;
				const d = new frappe.ui.Dialog({ title: __("Communication History"), size: "large" });
				d.$body.html(`<div style="max-height:60vh;overflow:auto">${html}</div>`);
				d.show();
			},
		});
	}

	DOCTYPES.forEach((doctype) => {
		frappe.ui.form.on(doctype, {
			refresh(frm) {
				if (frm.is_new()) return;
				frm.add_custom_button(__("Communication History"), () => show(doctype, frm.doc.name), __("View"));
			},
		});
	});
})();
