import frappe


def execute():
	frappe.reload_doc("estate_portal", "doctype", "portal_theme_section")
	frappe.reload_doc("estate_portal", "doctype", "portal_theme_link")
	frappe.reload_doc("estate_portal", "doctype", "portal_theme")
	frappe.reload_doc("estate_portal", "doctype", "portal_theme_settings")
	from thinknxg_estate.setup.install import ensure_default_themes

	ensure_default_themes()
