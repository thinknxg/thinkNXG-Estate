frappe.ui.form.on("Lease Contract", {
refresh(frm) {
if (frm.doc.docstatus === 1 && ["Active", "Expiring"].includes(frm.doc.status)) {
frm.add_custom_button(__("Terminate Lease"), () => {
let settlement = null;
const fmt = (v) => format_currency(v || 0, frm.doc.currency);
const refresh_settlement = () => {
const end = dialog.get_value("tenancy_end_date");
if (!end) return;
frm.call("get_termination_settlement", { tenancy_end_date: end }).then(r => {
settlement = r.message;
dialog.set_value("outstanding_rent", settlement.rent_outstanding || 0);
dialog.set_value("deposit_balance", settlement.deposit_balance || 0);
const adv = settlement.advance_invoices || [];
const has_adv = adv.length > 0;
dialog.set_df_property("credit_sb", "hidden", has_adv ? 0 : 1);
dialog.set_df_property("issue_credit_notes", "reqd", has_adv ? 1 : 0);
const rows = adv.map(a => `<tr><td>${frappe.utils.escape_html(a.sales_invoice)}</td><td>${a.due_date}</td><td class="text-right">${fmt(a.grand_total)}</td><td class="text-right">${fmt(a.paid)}</td></tr>`).join("");
dialog.fields_dict.advance_html.$wrapper.html(has_adv
? `<div class="text-muted small" style="margin-bottom:6px">${__("Rent already invoiced after the Tenancy End Date. These invoices are reversed with credit notes dated the Posting Date.")}</div>
<table class="table table-bordered table-sm"><thead><tr><th>${__("Invoice")}</th><th>${__("Due")}</th><th class="text-right">${__("Invoiced")}</th><th class="text-right">${__("Already paid")}</th></tr></thead><tbody>${rows}</tbody></table>`
: "");
const net = settlement.net_settlement || 0;
dialog.fields_dict.net_html.$wrapper.html(
`<div class="text-muted small">${__("Deposit balance")} ${fmt(settlement.deposit_balance)} + ${__("rent paid after end")} ${fmt(settlement.paid_after_end)} − ${__("outstanding rent")} ${fmt(settlement.rent_outstanding)}</div>
<div><b>${net >= 0 ? __("Refundable to tenant") : __("Payable by tenant")}: ${fmt(Math.abs(net))}</b></div>`);
});
};
const dialog = new frappe.ui.Dialog({
title: __("Terminate Lease"),
size: "large",
fields: [
{ fieldname: "schedule_end_date", fieldtype: "Date", label: __("Schedule End Date"),
  default: frm.doc.end_date, read_only: 1,
  description: __("Contractual end of the lease") },
{ fieldname: "tenancy_end_date", fieldtype: "Date", label: __("Tenancy End Date"),
  default: frappe.datetime.get_today(), reqd: 1,
  description: __("Actual last day of the tenancy; used for the final settlement"),
  change: () => refresh_settlement() },
{ fieldname: "posting_date", fieldtype: "Date", label: __("Posting Date"),
  default: frappe.datetime.get_today(), reqd: 1,
  description: __("Date the settlement enters the General Ledger") },
{ fieldname: "reasons", fieldtype: "Select", label: __("Reasons"),
  options: ["New Contract", "Lost to another agent", "Tenancy Surrendered",
            "End of Tenancy", "Tenancy Breach", "Break Clause Activation"],
  default: "New Contract", reqd: 1 },
{ fieldname: "apply_charge_to_tenant", fieldtype: "Check",
  label: __("Apply Charge to Tenant") },
{ fieldname: "rent_sb", fieldtype: "Section Break", label: __("Settlement") },
{ fieldname: "outstanding_rent", fieldtype: "Currency", label: __("Outstanding Rent"), read_only: 1 },
{ fieldname: "calculate_amount", fieldtype: "Button", label: __("Calculate Amount"),
  click: () => refresh_settlement() },
{ fieldname: "col_break_term", fieldtype: "Column Break" },
{ fieldname: "security_deposit_amount", fieldtype: "Currency",
  label: __("Original Security Deposit"), default: frm.doc.security_deposit_amount, read_only: 1 },
{ fieldname: "deposit_balance", fieldtype: "Currency", label: __("Deposit Balance Held"), read_only: 1 },
{ fieldname: "mode_of_payment", fieldtype: "Link", label: __("Mode of Payment"),
  options: "Mode of Payment" },
{ fieldname: "net_sb", fieldtype: "Section Break" },
{ fieldname: "net_html", fieldtype: "HTML" },
{ fieldname: "credit_sb", fieldtype: "Section Break", label: __("Invoices after the Tenancy End Date"), hidden: 1 },
{ fieldname: "advance_html", fieldtype: "HTML" },
{ fieldname: "issue_credit_notes", fieldtype: "Check",
  label: __("Issue credit notes for these invoices") },
{ fieldname: "notes_sb", fieldtype: "Section Break" },
{ fieldname: "reason", fieldtype: "Small Text", label: __("Notes") },
],
primary_action_label: __("Terminate"),
primary_action: (values) => {
frm.call("terminate", {
tenancy_end_date: values.tenancy_end_date,
posting_date: values.posting_date,
reasons: values.reasons,
reason: values.reason,
outstanding_rent: values.outstanding_rent || 0,
mode_of_payment: values.mode_of_payment,
apply_charge_to_tenant: values.apply_charge_to_tenant ? 1 : 0,
issue_credit_notes: values.issue_credit_notes ? 1 : 0,
}).then(() => {
dialog.hide();
frm.reload_doc();
if (values.reasons === "New Contract") {
frappe.new_doc("Lease Contract", {
tenant: frm.doc.tenant,
unit: frm.doc.unit,
property: frm.doc.property,
});
}
});
},
});
dialog.show();
refresh_settlement();
}).addClass("btn-danger");
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
