frappe.ui.form.on("Security Deposit", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.status === "Held") {
			frm.add_custom_button(__("Refund / Settle"), () => {
				frappe.prompt(
					[
						{ fieldname: "balance", fieldtype: "Currency", read_only: 1,
						  label: __("Deposit Balance Held"),
						  default: flt(frm.doc.amount) - flt(frm.doc.deduction_amount) - flt(frm.doc.refunded_amount) },
						{ fieldname: "deduction_amount", fieldtype: "Currency",
						  label: __("Deduction Amount"), default: 0 },
						{ fieldname: "posting_date", fieldtype: "Date", label: __("Posting Date"),
						  default: frappe.datetime.get_today(), reqd: 1 },
						{ fieldname: "deduction_reason", fieldtype: "Small Text",
						  label: __("Deduction Reason"), default: frm.doc.deduction_reason },
					],
					(v) => frm.call("refund", { deduction_amount: v.deduction_amount, deduction_reason: v.deduction_reason, posting_date: v.posting_date }).then(() => frm.reload_doc()),
					__("Settle Deposit"), __("Process")
				);
			}).addClass("btn-primary");
		}
	},
});
