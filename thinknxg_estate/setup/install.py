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
