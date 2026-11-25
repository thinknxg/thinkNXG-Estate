"""Install / migrate entry points for thinkNXG Estate.

Fresh site:   seeds master data (rent item, amenities, lead sources, deal pipeline board,
              voice commands and locale profiles).
Legacy site:  a site already running re_core / re_crm / re_portal / re_voice is upgraded in
              place, without moving or copying business data; see migrate_legacy.py.
"""

import frappe

from thinknxg_estate.setup import migrate_legacy


def before_install():
	legacy = migrate_legacy.installed_legacy_apps()
	if legacy:
		migrate_legacy.before_sync(legacy)


def after_install():
	from thinknxg_estate.core import install as core_install
	from thinknxg_estate.crm import install as crm_install
	from thinknxg_estate.voice import install as voice_install

	core_install.after_install()
	crm_install.after_install()
	voice_install.after_install()


def after_sync():
	"""Runs after fixtures (roles, sidebar, desktop icon) are in place."""
	legacy = migrate_legacy.installed_legacy_apps()
	if legacy:
		summary = migrate_legacy.after_sync(legacy)
		print("thinkNXG Estate legacy migration:")
		for key, value in summary.items():
			print(f"  {key}: {value}")


def after_migrate():
	from thinknxg_estate.core.install import ensure_rent_item
	from thinknxg_estate.core.naming import sync_naming_counters

	ensure_rent_item()
	sync_naming_counters()
	ensure_default_themes()


def ensure_default_themes():
	"""One theme per built-in template, so the admin has something to preview straight away; the
	Classic one is published when nothing is live yet, which keeps the site looking as it did."""
	from thinknxg_estate.portal import themes

	if not frappe.db.exists("DocType", "Portal Theme"):
		return
	for name, tpl in themes.TEMPLATES.items():
		if not frappe.db.exists("Portal Theme", tpl["label"]):
			frappe.get_doc({"doctype": "Portal Theme", "theme_name": tpl["label"], "template": name,
			                "description": tpl["description"]}).insert(ignore_permissions=True)
	if not themes.active_theme_name():
		from thinknxg_estate.portal.api import theme_admin

		frappe.flags.in_install = True
		try:
			theme_admin.publish_as_system(themes.TEMPLATES["Classic"]["label"])
		finally:
			frappe.flags.in_install = False
