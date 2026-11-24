frappe.query_reports["Broker Commission Statement"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.year_start() },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.year_end() },
		{ fieldname: "agent", label: __("Agent / Broker"), fieldtype: "Link", options: "RE Agent" },
		{ fieldname: "status", label: __("Status"), fieldtype: "Select", options: "\nDraft\nApproved\nPaid" },
	],
};
