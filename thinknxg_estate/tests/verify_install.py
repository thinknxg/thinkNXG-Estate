"""Post-install verification (bench --site SITE execute thinknxg_estate.tests.verify_install.run)."""
import json

import frappe

EXPECTED_MODULES = ["thinkNXG Estate", "Estate Property", "Estate Leasing", "Estate Finance",
                    "Estate Maintenance", "Estate CRM", "Estate Portal", "Estate Voice"]


def run():
	out = {}
	out["installed_apps"] = frappe.get_installed_apps()
	out["doctypes_by_module"] = {
		m: frappe.db.count("DocType", {"module": m}) for m in EXPECTED_MODULES}
	out["module_defs"] = frappe.get_all("Module Def", {"app_name": "thinknxg_estate"}, pluck="name")
	out["legacy_module_defs"] = frappe.get_all(
		"Module Def", {"name": ["in", ["RE Core", "Re Core", "RE CRM", "RE Portal", "RE Voice"]]}, pluck="name")
	out["reports"] = frappe.get_all("Report", {"module": ["in", EXPECTED_MODULES]}, pluck="name")
	out["number_cards"] = frappe.db.count("Number Card", {"module": "thinkNXG Estate"})
	out["charts"] = frappe.db.count("Dashboard Chart", {"module": "thinkNXG Estate"})
	out["workspaces"] = frappe.get_all("Workspace", {"module": ["in", EXPECTED_MODULES]}, pluck="name")
	out["sidebar_items"] = frappe.db.count("Sidebar Item", {"parent": "thinkNXG Estate"})
	out["legacy_sidebars"] = frappe.get_all("Workspace Sidebar", {"name": ["in", ["RE Core"]]}, pluck="name")
	out["desktop_icons"] = frappe.get_all("Desktop Icon", {"app": ["in", ["thinknxg_estate", "re_core", "re_crm", "re_portal", "re_voice"]]}, pluck="name")
	out["voice_commands"] = frappe.db.count("Voice Command")
	out["voice_handlers_legacy"] = frappe.db.count("Voice Command", {"handler": ["like", "re_%"]})
	out["voice_handlers_resolvable"] = all(
		_resolves(h) for h in frappe.get_all("Voice Command", pluck="handler"))
	out["rent_item"] = frappe.db.get_single_value("Property Settings", "rent_item")
	out["amenities"] = frappe.db.count("Amenity")
	out["lead_sources"] = frappe.db.count("Lead Source RE")
	out["kanban"] = frappe.db.exists("Kanban Board", "Deal Pipeline")
	out["roles"] = frappe.get_all("Role", {"name": ["in", ["RE Manager", "Property Manager", "Leasing Officer",
	                                                        "Maintenance Supervisor", "RE Sales Manager",
	                                                        "RE Sales Agent", "Voice Ops Manager", "Tenant"]]},
	                              pluck="name")
	out["custom_fields"] = frappe.get_all("Custom Field", {"module": "thinkNXG Estate"}, pluck="name")
	out["duplicate_standard_custom_fields"] = frappe.db.sql("""
		select cf.name from `tabCustom Field` cf join `tabDocField` df
		on df.parent = cf.dt and df.fieldname = cf.fieldname and df.parenttype='DocType'""", pluck=True)
	out["scheduled_jobs"] = frappe.db.count("Scheduled Job Type", {"method": ["like", "thinknxg_estate.%"]})
	out["legacy_scheduled_jobs"] = frappe.db.count("Scheduled Job Type", {"method": ["like", "re\\_%"]})
	out["print_formats"] = frappe.get_all("Print Format", {"module": ["in", EXPECTED_MODULES]}, pluck="name")
	print(json.dumps(out, indent=1, default=str))
	return out


def _resolves(path):
	try:
		frappe.get_attr(path)
		return True
	except Exception:
		print("UNRESOLVED", path)
		return False
