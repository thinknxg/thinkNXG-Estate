frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["RE Rent Billed vs Collected"] = {
	method: "thinknxg_estate.thinknxg_estate.dashboard_chart_source.re_rent_billed_vs_collected.re_rent_billed_vs_collected.get",
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
	],
};
