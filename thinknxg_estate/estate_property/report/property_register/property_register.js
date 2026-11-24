frappe.query_reports["Property Register"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
		{ fieldname: "city", label: __("City"), fieldtype: "Data" },
	],
};
