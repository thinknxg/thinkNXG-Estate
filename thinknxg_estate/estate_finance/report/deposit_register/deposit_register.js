frappe.query_reports["Deposit Register"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
		{ fieldname: "status", label: __("Status"), fieldtype: "Select", options: "\nHeld\nPartially Refunded\nRefunded\nForfeited\nDraft" },
	],
};
