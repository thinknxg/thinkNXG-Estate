frappe.query_reports["Site Visit Conversion"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.year_start() },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.year_end() },
		{ fieldname: "agent", label: __("Agent"), fieldtype: "Link", options: "RE Agent" },
	],
};
