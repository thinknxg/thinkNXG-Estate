frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["RE Lease Expirations by Month"] = {
	method: "thinknxg_estate.thinknxg_estate.dashboard_chart_source.re_lease_expirations_by_month.re_lease_expirations_by_month.get",
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
	],
};
