frappe.query_reports["Property Profitability"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.year_start() },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.year_end() },
		{ fieldname: "property", label: __("Property"), fieldtype: "Link", options: "Property" },
	],
};
