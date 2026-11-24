"""Smoke-run every thinkNXG Estate report (bench --site SITE execute thinknxg_estate.tests.run_all_reports.run)."""
import frappe

MODULES = ["Estate Property", "Estate Leasing", "Estate Finance", "Estate Maintenance", "Estate CRM", "Estate Voice"]


def run():
	from frappe.desk.query_report import run as run_report

	out = {}
	start, end = f"{frappe.utils.getdate().year}-01-01", f"{frappe.utils.getdate().year}-12-31"
	for name in frappe.get_all("Report", {"module": ["in", MODULES]}, pluck="name", order_by="name"):
		try:
			res = run_report(name, filters={"from_date": start, "to_date": end})
			out[name] = f"ok, {len(res.get('result') or [])} rows"
		except Exception as e:
			out[name] = f"ERROR {type(e).__name__}: {str(e)[:200]}"
	for k, v in out.items():
		print(f"{k:32} {v}")
	return out
