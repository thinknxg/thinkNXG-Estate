"""In-place upgrade of a site running the four legacy apps to thinkNXG Estate.

Business data never moves: every DocType keeps its name and its table. What changes is
ownership (module / app), navigation, a few stored dotted paths, and the CRM links that
let portal activity reach the unified lead record.

Sequence (driven by `bench --site SITE install-app thinknxg_estate`):

before_sync  (before thinkNXG Estate's DocTypes are synced)
  1. Delete Custom Field / Property Setter records that are now standard fields of the
     unified DocTypes (columns and values stay, only the duplicate definition goes).

  ... Frappe syncs the DocTypes, reports, cards and charts, re-homing them in Estate modules ...

after_sync   (after fixtures)
  2. Rewrite stored handler paths of Voice Commands (re_voice.* -> thinknxg_estate.voice.*).
  3. Link legacy portal records (ERPNext Lead based) to the CRM's RE Lead.
  4. Keep the access-code tenant portal on if tenants were already using it.
  5. Remove legacy workspaces, sidebar, desktop icons and scheduled jobs.
  6. Remove the four legacy apps from the site's installed apps (without uninstalling them,
     which would delete data) and drop their now-empty Module Defs.

Every step is idempotent. Take a backup first: `bench --site SITE backup --with-files`.
"""

import json
import os

import frappe

LEGACY_APPS = ("re_voice", "re_portal", "re_crm", "re_core")  # removal order: dependants first
LEGACY_MODULES = ("RE Core", "Re Core", "RE CRM", "RE Portal", "RE Voice")
LEGACY_WORKSPACES = ("RE Core", "Property Operations", "RE Finance", "RE Maintenance", "RE CRM",
                     "RE Portal", "Voice CRM")
LEGACY_SIDEBARS = ("RE Core", "RE CRM", "RE Portal", "RE Voice", "Voice CRM", "Property Ops")
LEGACY_PREFIXES = {"re_voice.": "thinknxg_estate.voice.", "re_crm.re_crm.": "thinknxg_estate.crm.",
                   "re_crm.": "thinknxg_estate.crm.", "re_portal.": "thinknxg_estate.portal.",
                   "re_core.re_core.": "thinknxg_estate.core.", "re_core.": "thinknxg_estate.core."}


def installed_legacy_apps():
	installed = frappe.get_installed_apps()
	return [app for app in LEGACY_APPS if app in installed]


def _folded():
	path = os.path.join(os.path.dirname(__file__), "legacy_custom_fields.json")
	with open(path) as f:
		return json.load(f)["folded"]


# --------------------------------------------------------------------------- before sync
def before_sync(legacy):
	removed_fields, removed_setters = 0, 0
	for entry in _folded():
		parts = entry.split(".")
		if len(parts) == 2:
			dt, fieldname = parts
			for name in frappe.get_all("Custom Field", {"dt": dt, "fieldname": fieldname}, pluck="name"):
				frappe.db.delete("Custom Field", {"name": name})
				removed_fields += 1
		else:
			dt, fieldname, prop = parts[0], parts[1], parts[2].split("=")[0]
			for name in frappe.get_all("Property Setter",
			                           {"doc_type": dt, "field_name": fieldname, "property": prop},
			                           pluck="name"):
				frappe.db.delete("Property Setter", {"name": name})
				removed_setters += 1
	frappe.db.commit()
	frappe.clear_cache()
	print(f"thinkNXG Estate: legacy apps detected {legacy}; "
	      f"{removed_fields} custom fields and {removed_setters} property setters are now standard")


# --------------------------------------------------------------------------- after sync
def after_sync(legacy):
	summary = {
		"voice_handlers_rewritten": rewrite_voice_handlers(),
		"portal_records_linked_to_crm": link_portal_records_to_crm(),
		"access_code_portal": keep_access_code_portal(),
		"legacy_navigation_removed": remove_legacy_navigation(legacy),
		"legacy_scheduled_jobs_removed": remove_legacy_jobs(),
	}
	summary["legacy_apps_detached"] = detach_legacy_apps(legacy)
	summary["legacy_module_defs_removed"] = remove_legacy_module_defs()
	frappe.db.commit()
	return summary


def _rewrite(value):
	for old, new in LEGACY_PREFIXES.items():
		if value and value.startswith(old):
			return new + value[len(old):]
	return value


def rewrite_voice_handlers():
	if not frappe.db.table_exists("Voice Command"):
		return 0
	count = 0
	for row in frappe.get_all("Voice Command", fields=["name", "handler"]):
		new = _rewrite(row.handler)
		if new != row.handler:
			frappe.db.set_value("Voice Command", row.name, "handler", new, update_modified=False)
			count += 1
	return count


def link_portal_records_to_crm():
	"""Legacy /listings visitors were ERPNext Leads; the CRM works on RE Lead. Ensure each
	legacy portal record points at the RE Lead for the same visitor (created if missing)."""
	from thinknxg_estate.core.listing_portal_api.listing_portal import _get_or_create_re_lead

	linked = 0
	for doctype, lead_field in (("Property Enquiry", "linked_lead"), ("Site Visit Booking", "lead"),
	                            ("Saved Search", "lead"), ("Property Wishlist", "lead")):
		rows = frappe.get_all(doctype, filters={lead_field: ["is", "set"], "re_lead": ["is", "not set"]},
		                      fields=["name", lead_field])
		for row in rows:
			re_lead = _get_or_create_re_lead(row[lead_field])
			if re_lead:
				frappe.db.set_value(doctype, row.name, "re_lead", re_lead, update_modified=False)
				linked += 1
	return linked


def keep_access_code_portal():
	"""The token/access-code tenant portal is off by default; keep it on where tenants use it."""
	in_use = frappe.db.sql(
		"""select count(*) from `tabTenant` t join `__Auth` a
		   on a.doctype='Tenant' and a.name=t.name and a.fieldname='portal_access_code'""")[0][0]
	if in_use:
		frappe.db.set_single_value("Property Settings", "enable_access_code_portal", 1)
	return "kept enabled" if in_use else "disabled (no tenant had an access code)"


def remove_legacy_navigation(legacy):
	removed = []
	for name in LEGACY_WORKSPACES:
		if frappe.db.exists("Workspace", name):
			frappe.delete_doc("Workspace", name, force=True, ignore_permissions=True)
			removed.append(f"Workspace:{name}")
	for doctype in ("Workspace Sidebar", "Desktop Icon"):
		if not frappe.db.table_exists(doctype):
			continue
		names = set(frappe.get_all(doctype, filters={"app": ["in", list(legacy)]}, pluck="name"))
		names |= {n for n in LEGACY_SIDEBARS if frappe.db.exists(doctype, n)}
		for name in names:
			frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
			removed.append(f"{doctype}:{name}")
	return removed


def remove_legacy_jobs():
	names = []
	for prefix in ("re_core.", "re_crm.", "re_portal.", "re_voice."):
		names += frappe.get_all("Scheduled Job Type", filters={"method": ["like", f"{prefix}%"]},
		                        pluck="name")
	for name in names:
		frappe.delete_doc("Scheduled Job Type", name, force=True, ignore_permissions=True)
	return len(names)


def detach_legacy_apps(legacy):
	"""Drop the apps from the site's installed list. Never `uninstall-app` them: that deletes
	DocTypes by module and would take the data with it."""
	from frappe.installer import remove_from_installed_apps

	for app in legacy:
		remove_from_installed_apps(app)
	return list(legacy)


def remove_legacy_module_defs():
	removed = []
	for module in LEGACY_MODULES:
		if not frappe.db.exists("Module Def", module):
			continue
		still_used = any(
			frappe.db.exists(doctype, {"module": module})
			for doctype in ("DocType", "Report", "Page", "Print Format", "Number Card",
			                "Dashboard Chart", "Dashboard Chart Source", "Workspace", "Web Form",
			                "Notification", "Custom Field")
			if frappe.db.table_exists(doctype)
		)
		if still_used:
			continue
		# direct delete: Module Def.on_trash rewrites the (legacy) app's modules.txt on disk
		frappe.db.delete("Module Def", {"name": module})
		removed.append(module)
	return removed
