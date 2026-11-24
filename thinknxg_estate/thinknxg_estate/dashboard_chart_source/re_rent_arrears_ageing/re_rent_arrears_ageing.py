import frappe

from thinknxg_estate.core.ops_dashboard import arrears_ageing_chart
from thinknxg_estate.core.security import staff_only


@frappe.whitelist()
@staff_only
def get(
	chart_name=None,
	chart=None,
	no_cache=None,
	filters=None,
	from_date=None,
	to_date=None,
	timespan=None,
	time_interval=None,
	heatmap_year=None,
):
	filters = frappe.parse_json(filters) or {}
	if chart_name and not filters:
		filters = frappe.parse_json(frappe.db.get_value("Dashboard Chart", chart_name, "filters_json")) or {}
	if isinstance(filters, list):
		filters = {}
	return arrears_ageing_chart(company=filters.get("company"))
