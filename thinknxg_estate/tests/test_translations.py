"""Arabic translation coverage and right-to-left rendering.

bench --site TEST_SITE run-tests --app thinknxg_estate --module thinknxg_estate.tests.test_translations
"""

import os
import re

import frappe
from frappe.tests import IntegrationTestCase

LOCALE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "locale")
PLACEHOLDERS = (r"\{\d*\}", r"\{[a-z_]+\}", r"<[^>]+>")


def _catalog(name, locale=None):
	from babel.messages.pofile import read_po

	with open(os.path.join(LOCALE, name), "rb") as handle:
		return read_po(handle, locale=locale)


def _other_apps_arabic():
	from babel.messages.pofile import read_po

	known = set()
	for app in ("frappe", "erpnext"):
		path = frappe.get_app_path(app, "locale", "ar.po")
		if os.path.exists(path):
			with open(path, "rb") as handle:
				for m in read_po(handle, locale="ar"):
					if m.id and m.string and not m.context:
						known.add(m.id if isinstance(m.id, str) else m.id[0])
	return known


class TestArabic(IntegrationTestCase):
	def test_every_string_has_arabic(self):
		"""Each string in main.pot is translated here or by Frappe/ERPNext. Run
		`bench generate-pot-file` and `bench update-po-files` after adding strings, then translate."""
		pot = [m for m in _catalog("main.pot") if m.id]
		ar = {(m.context, m.id): m.string for m in _catalog("ar.po", "ar") if m.id}
		known = _other_apps_arabic()
		missing = [m.id for m in pot if not ar.get((m.context, m.id)) and (m.context or m.id not in known)]
		self.assertEqual(missing, [], f"{len(missing)} strings have no Arabic translation")

	def test_placeholders_and_markup_survive(self):
		for m in _catalog("ar.po", "ar"):
			if not (m.id and m.string) or not isinstance(m.id, str):
				continue
			for pattern in PLACEHOLDERS:
				self.assertEqual(sorted(re.findall(pattern, m.id)), sorted(re.findall(pattern, m.string)),
				                 f"{pattern} differs in {m.id!r}")

	def test_runtime_lookup(self):
		frappe.local.lang = "ar"
		try:
			self.assertEqual(frappe._("Lease Contract"), "عقد إيجار")
			self.assertEqual(frappe._("{0} properties found").format(3), "تم العثور على 3 عقار")
			self.assertEqual(frappe._("Property", context="Lease Contract"), "العقار")
			self.assertEqual(frappe._("Due Date"), "تاريخ الاستحقاق")
		finally:
			frappe.local.lang = "en"

	def test_console_is_right_to_left_in_arabic(self):
		import importlib.util

		path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "www", "re-portal", "index.py")
		spec = importlib.util.spec_from_file_location("re_portal_page", path)
		page = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(page)
		table = page.console_translations("ar")
		self.assertEqual(table.get("Lease Contracts"), "عقود الإيجار")
		self.assertEqual(table.get("{0}% VAT"), "ضريبة القيمة المضافة {0}%")
		self.assertEqual(page.console_translations("en"), {})
		self.assertIn("ar", page.RTL_LANGUAGES)
