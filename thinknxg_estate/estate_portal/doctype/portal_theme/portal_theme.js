const API = "thinknxg_estate.portal.api.theme_admin.";

frappe.ui.form.on("Portal Theme", {
	refresh(frm) {
		frm.set_intro("");
		if (frm.is_new()) {
			frm.set_intro(__("Pick a base template and a name, then save. The design fields fill in from the template."), "blue");
			return;
		}
		frm.dashboard.clear_headline();
		frm.dashboard.set_headline(frm.doc.is_live
			? `<span class="indicator-pill green">${__("Live")}</span> ${__("Visitors see the last published copy. Edits below are a draft until you publish.")}`
			: `<span class="indicator-pill orange">${__("Draft")}</span> ${__("Not shown to visitors. Preview it, then publish.")}`);
		frm.page.set_indicator(frm.doc.is_live ? __("Live") : __("Draft"), frm.doc.is_live ? "green" : "orange");

		frm.add_custom_button(__("Preview"), () => preview(frm));
		frm.add_custom_button(__("Publish"), () => publish(frm)).addClass("btn-primary");
		frm.add_custom_button(__("Duplicate"), () => duplicate(frm), __("Actions"));
		frm.add_custom_button(__("Apply Template"), () => apply_template(frm), __("Actions"));
		if (frm.doc.is_live) {
			frm.add_custom_button(__("Revert to Previous Version"), () => {
				frappe.confirm(__("Go back to the copy that was live before the last publish?"), () =>
					frappe.call({ method: API + "revert", args: { theme: frm.doc.name }, freeze: true,
						callback: () => { frappe.show_alert({ message: __("Reverted"), indicator: "green" }); frm.reload_doc(); } }));
			}, __("Actions"));
			frm.add_custom_button(__("Open Live Site"), () => window.open("/properties", "_blank"), __("Actions"));
		}
	},
	template(frm) {
		if (!frm.is_new() && frm.doc.template) {
			frappe.show_alert({ message: __("Template changed. Use Actions > Apply Template to reset the design fields to it."), indicator: "blue" });
		}
	},
});

function need_saved(frm, then) {
	if (frm.is_dirty()) {
		frappe.confirm(__("Save your changes first?"), () => frm.save().then(then));
	} else {
		then();
	}
}

function publish(frm) {
	need_saved(frm, () => {
		frappe.confirm(
			__("Publish {0}? Visitors will see this design straight away.", [frm.doc.name]),
			() => frappe.call({
				method: API + "publish", args: { theme: frm.doc.name }, freeze: true, freeze_message: __("Publishing"),
				callback: () => { frappe.show_alert({ message: __("Published. The site now uses {0}.", [frm.doc.name]), indicator: "green" }); frm.reload_doc(); },
			}));
	});
}

function duplicate(frm) {
	frappe.prompt({ fieldname: "new_name", fieldtype: "Data", label: __("Name of the copy"), reqd: 1, default: `${frm.doc.name} copy` },
		(v) => frappe.call({ method: API + "duplicate", args: { theme: frm.doc.name, new_name: v.new_name },
			callback: (r) => frappe.set_route("Form", "Portal Theme", r.message) }),
		__("Duplicate Theme"), __("Create"));
}

function apply_template(frm) {
	frappe.prompt([
		{ fieldname: "template", fieldtype: "Select", label: __("Template"), options: "Classic\nModern\nLuxury\nMarketplace", default: frm.doc.template, reqd: 1 },
		{ fieldname: "keep_content", fieldtype: "Check", label: __("Keep my branding, text, links and section titles"), default: 1 },
	], (v) => frappe.call({ method: API + "apply_template", args: { theme: frm.doc.name, template: v.template, keep_content: v.keep_content ? 1 : 0 }, freeze: true,
		callback: () => { frappe.show_alert({ message: __("Template applied"), indicator: "green" }); frm.reload_doc(); } }),
	__("Apply Template"), __("Apply"));
}

function preview(frm) {
	need_saved(frm, () => frappe.call({
		method: API + "preview_links", args: { theme: frm.doc.name },
		callback: (r) => {
			const pages = r.message || [];
			const d = new frappe.ui.Dialog({
				title: __("Preview: {0}", [frm.doc.name]), size: "extra-large",
				fields: [
					{ fieldname: "page", fieldtype: "Select", label: __("Page"), options: pages.map((p) => p.label).join("\n"), default: pages[0] && pages[0].label },
					{ fieldname: "col", fieldtype: "Column Break" },
					{ fieldname: "device", fieldtype: "Select", label: __("Device"), options: "Desktop\nTablet\nMobile", default: "Desktop" },
					{ fieldname: "frame", fieldtype: "HTML" },
				],
				primary_action_label: __("Open in New Tab"),
				primary_action() { window.open(url(), "_blank"); },
			});
			const url = () => (pages.find((p) => p.label === d.get_value("page")) || pages[0]).url;
			const widths = { Desktop: "100%", Tablet: "820px", Mobile: "390px" };
			const draw = () => {
				d.get_field("frame").$wrapper.html(
					`<div style="background:#e5e7eb;padding:12px;border-radius:8px;text-align:center">
					<iframe title="${__("Preview")}" src="${url()}" style="width:${widths[d.get_value("device")]};max-width:100%;height:68vh;border:0;background:#fff;border-radius:6px"></iframe></div>
					<p class="text-muted small" style="margin:8px 0 0">${__("This shows the saved draft. Only you can see it; visitors still see the live site.")}</p>`);
			};
			d.fields_dict.page.df.onchange = draw;
			d.fields_dict.device.df.onchange = draw;
			d.show();
			draw();
		},
	}));
}
