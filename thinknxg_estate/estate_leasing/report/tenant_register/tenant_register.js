frappe.query_reports["Tenant Register"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
		{ fieldname: "only_active", label: __("Only Tenants with an Active Lease"), fieldtype: "Check", default: 1 },
	],
};
