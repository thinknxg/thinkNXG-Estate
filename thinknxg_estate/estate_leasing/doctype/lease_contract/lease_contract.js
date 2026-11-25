frappe.ui.form.on("Lease Contract", {
refresh(frm) {
if (frm.doc.docstatus === 1 && ["Active", "Expiring"].includes(frm.doc.status)) {
frm.add_custom_button(__("Terminate Lease"), () => {
let settlement = null;
let busy = false;
const fmt = (v) => format_currency(v || 0, settlement ? settlement.currency : frm.doc.currency);
const esc = frappe.utils.escape_html;
const charges = () => (dialog.get_value("apply_charge_to_tenant") ? (dialog.get_value("charges") || [])
	.filter(r => r.description || r.amount)
	.map(r => ({ description: r.description, amount: flt(r.amount), vat_applicable: r.vat_applicable ? 1 : 0 })) : []);
const invalidate = () => {
	settlement = null;
	dialog.get_primary_btn().prop("disabled", true);
	dialog.fields_dict.net_html.$wrapper.html(`<div class="text-warning small">${__("Inputs changed — press Calculate Amount before terminating.")}</div>`);
};
const calculate = () => {
	const end = dialog.get_value("tenancy_end_date"), posting = dialog.get_value("posting_date");
	if (!end || !posting) { frappe.msgprint(__("Tenancy End Date and Posting Date are required.")); return; }
	const apply = dialog.get_value("apply_charge_to_tenant") ? 1 : 0;
	frm.call("get_termination_settlement", {
		tenancy_end_date: end, posting_date: posting, charges: JSON.stringify(charges()), apply_charge_to_tenant: apply,
	}).then(r => {
		settlement = r.message;
		dialog.set_value("outstanding_rent", settlement.rent_outstanding || 0);
		dialog.set_value("deposit_balance", settlement.deposit_balance || 0);
		const kv = (k, v, b) => `<tr><td>${k}</td><td class="text-right">${b ? "<b>" + v + "</b>" : v}</td></tr>`;
		const label = {"Payable to Tenant": __("Amount Payable to Tenant"), "Receivable from Tenant": __("Amount Receivable from Tenant"),
			"Settled": __("No Outstanding Settlement / Settled")}[settlement.result];
		const adj = (settlement.adjustments || []).filter(a => a.credit_gross || a.to_invoice).map(a =>
			`<li>${a.due_date}: ${a.to_invoice ? __("to be invoiced") + " " + fmt(a.gross) + "; " : esc(a.sales_invoice || "") + " "}${a.credit_gross ? (a.kind === "prorata" ? __("pro-rata credit") + ` (${a.unused_days}/${a.period_days})` : __("full credit note")) + " " + fmt(a.credit_gross) : ""}</li>`).join("");
		dialog.fields_dict.net_html.$wrapper.html(
			`<table class="table table-bordered table-sm"><tbody>
			${kv(__("Security deposit balance"), fmt(settlement.deposit_balance))}
			${kv("+ " + __("Advance rent / credit to refund"), fmt(settlement.paid_after_end))}
			${kv("− " + __("Outstanding rent (invoices incl. VAT)"), fmt(settlement.rent_outstanding))}
			${kv("− " + __("Tenant charges"), fmt(settlement.charges_net))}
			${kv("− " + __("VAT on charges"), fmt(settlement.charges_vat))}
			${kv(__("Total deductions"), fmt(settlement.total_deductions))}
			${kv(label, fmt(Math.abs(settlement.net_settlement)), 1)}</tbody></table>
			${adj ? `<ul class="small text-muted">${adj}</ul>` : ""}
			${(settlement.warnings || []).map(w => `<div class="text-warning small">${esc(w)}</div>`).join("")}`);
		dialog.set_df_property("mode_of_payment", "reqd", settlement.result === "Settled" ? 0 : 1);
		dialog.refresh();
		dialog.get_primary_btn().prop("disabled", false);
	});
};
const dialog = new frappe.ui.Dialog({
title: __("Terminate Lease"),
size: "extra-large",
fields: [
{ fieldname: "a_sb", fieldtype: "Section Break", label: __("A. Lease Information") },
{ fieldname: "schedule_end_date", fieldtype: "Date", label: __("Schedule End Date"),
  default: frm.doc.end_date, read_only: 1, description: __("Contractual end of the lease. Never changed.") },
{ fieldname: "tenancy_end_date", fieldtype: "Date", label: __("Tenancy End Date"),
  default: frappe.datetime.get_today(), reqd: 1,
  description: __("Actual last day of the tenancy; drives the settlement"), change: () => invalidate() },
{ fieldname: "a_cb", fieldtype: "Column Break" },
{ fieldname: "reasons", fieldtype: "Select", label: __("Reasons"),
  options: ["New Contract", "Lost to another agent", "Tenancy Surrendered",
            "End of Tenancy", "Tenancy Breach", "Break Clause Activation"],
  default: "New Contract", reqd: 1 },
{ fieldname: "security_deposit_amount", fieldtype: "Currency",
  label: __("Original Security Deposit"), default: frm.doc.security_deposit_amount, read_only: 1 },
{ fieldname: "b_sb", fieldtype: "Section Break", label: __("B. Financial Position") },
{ fieldname: "outstanding_rent", fieldtype: "Currency", label: __("Outstanding Rent"), read_only: 1 },
{ fieldname: "b_cb", fieldtype: "Column Break" },
{ fieldname: "deposit_balance", fieldtype: "Currency", label: __("Deposit Balance Held"), read_only: 1 },
{ fieldname: "c_sb", fieldtype: "Section Break", label: __("C. Tenant Charges") },
{ fieldname: "apply_charge_to_tenant", fieldtype: "Check", label: __("Apply Charge to Tenant"), default: 0,
  change: () => { dialog.set_df_property("charges", "hidden", dialog.get_value("apply_charge_to_tenant") ? 0 : 1); invalidate(); } },
{ fieldname: "charges", fieldtype: "Table", label: __("Charges (VAT-exclusive amounts)"), hidden: 1, cannot_add_rows: false,
  data: [], in_place_edit: true,
  fields: [
    { fieldname: "description", fieldtype: "Data", label: __("Charge Description"), in_list_view: 1, columns: 4 },
    { fieldname: "amount", fieldtype: "Currency", label: __("Amount"), in_list_view: 1, columns: 2 },
    { fieldname: "vat_applicable", fieldtype: "Check", label: __("VAT Treatment (Yes/No)"), in_list_view: 1, columns: 2 },
  ] },
{ fieldname: "d_sb", fieldtype: "Section Break", label: __("D. Settlement Calculation") },
{ fieldname: "calculate_amount", fieldtype: "Button", label: __("Calculate Amount"), click: () => calculate() },
{ fieldname: "net_html", fieldtype: "HTML" },
{ fieldname: "e_sb", fieldtype: "Section Break", label: __("E. Accounting Details") },
{ fieldname: "posting_date", fieldtype: "Date", label: __("Posting Date"),
  default: frappe.datetime.get_today(), reqd: 1,
  description: __("Date the settlement enters the General Ledger"), change: () => invalidate() },
{ fieldname: "e_cb", fieldtype: "Column Break" },
{ fieldname: "mode_of_payment", fieldtype: "Link", label: __("Mode of Payment"),
  options: "Mode of Payment", description: __("Required when cash moves; its account is used for the payment/receipt") },
{ fieldname: "f_sb", fieldtype: "Section Break", label: __("F. Notes") },
{ fieldname: "reason", fieldtype: "Small Text", label: __("Notes") },
],
primary_action_label: __("Terminate Lease"),
primary_action: (values) => {
if (busy) return;
if (!settlement) { frappe.msgprint(__("Calculate the settlement first.")); return; }
if (settlement.result !== "Settled" && !values.mode_of_payment) { frappe.msgprint(__("Mode of Payment is required.")); return; }
busy = true;
dialog.get_primary_btn().prop("disabled", true).text(__("Terminating…"));
frm.call("terminate", {
tenancy_end_date: values.tenancy_end_date,
posting_date: values.posting_date,
reasons: values.reasons,
reason: values.reason,
mode_of_payment: values.mode_of_payment,
apply_charge_to_tenant: values.apply_charge_to_tenant ? 1 : 0,
charges: JSON.stringify(charges()),
calc_token: settlement.token,
}).then(() => {
dialog.hide();
frm.reload_doc();
frappe.show_alert({ message: __("Lease terminated and settlement posted."), indicator: "green" });
if (values.reasons === "New Contract") {
frappe.new_doc("Lease Contract", {
tenant: frm.doc.tenant,
unit: frm.doc.unit,
property: frm.doc.property,
});
}
}).catch(() => {
busy = false;
dialog.get_primary_btn().prop("disabled", false).text(__("Terminate Lease"));
});
},
});
dialog.show();
dialog.get_primary_btn().prop("disabled", true);
invalidate();
}).addClass("btn-danger");
}
if (frm.doc.docstatus === 1 && frm.doc.status === "Terminated" && frm.doc.termination_settlement) {
frm.add_custom_button(__("Reverse Termination"), () => {
frappe.prompt({ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 }, (v) => {
frm.call("reverse_termination", { reason: v.reason }).then(() => frm.reload_doc());
}, __("Reverse termination and cancel its settlement entries?"));
});
}
if (frm.doc.rent_schedule) {
frm.add_custom_button(__("Rent Schedule"), () =>
frappe.set_route("Form", "Rent Schedule", frm.doc.rent_schedule), __("View"));
}
if (frm.doc.security_deposit) {
frm.add_custom_button(__("Security Deposit"), () =>
frappe.set_route("Form", "Security Deposit", frm.doc.security_deposit), __("View"));
}
},
unit(frm) { auto_populate_lease_charges(frm, false); },
property(frm) { auto_populate_lease_charges(frm, false); },
start_date(frm) { auto_populate_lease_charges(frm, false); },
end_date(frm) { auto_populate_lease_charges(frm, false); },
});

function auto_populate_lease_charges(frm, force) {
if (frm.doc.docstatus !== 0) return;
if (!frm.doc.property && !frm.doc.unit) return;
if (!frm.doc.start_date || !frm.doc.end_date) return;
// Don't clobber manually entered/edited rows unless the admin explicitly
// clicked "Auto-fill Charges" (force = true). A freshly opened form can
// have a single blank grid row by default - that doesn't count as
// "already has data".
const has_real_charge_rows = (frm.doc.charges || []).some(r => r.amount);
if (!force && has_real_charge_rows) return;

frappe.call({
method: "thinknxg_estate.core.api.get_lease_term_charges_preview",
args: {
property: frm.doc.property,
unit: frm.doc.unit,
start_date: frm.doc.start_date,
end_date: frm.doc.end_date,
},
callback: (r) => {
const charges = (r.message && r.message.charges) || [];
if (!charges.length) return;
frm.clear_table("charges");
charges.forEach((c) => {
const row = frm.add_child("charges");
row.charge_type = c.charge_type;
row.description = c.description;
row.amount = c.amount;
});
frm.refresh_field("charges");
frappe.show_alert({
message: __("Charges auto-filled from Property/Unit ({0} rows). Review and edit as needed.", [charges.length]),
indicator: "green",
});
},
});
}
