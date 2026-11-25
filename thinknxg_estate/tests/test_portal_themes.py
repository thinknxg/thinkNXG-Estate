"""Integration tests for the property portal theme builder (Portal Theme / Portal Theme Settings).

bench --site TEST_SITE run-tests --app thinknxg_estate --module thinknxg_estate.tests.test_portal_themes
"""

import frappe
from frappe.tests import IntegrationTestCase

from thinknxg_estate.portal import themes
from thinknxg_estate.portal.api import theme_admin


def new_theme(name, template="Modern", **values):
	doc = frappe.get_doc({"doctype": "Portal Theme", "theme_name": name, "template": template, **values})
	return doc.insert()


class TestPortalThemes(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.live_before = frappe.db.get_single_value("Portal Theme Settings", "active_theme")

	def tearDown(self):
		frappe.set_user("Administrator")
		if self.live_before and frappe.db.get_single_value("Portal Theme Settings", "active_theme") != self.live_before:
			theme_admin.publish_as_system(self.live_before)
		for name in frappe.get_all("Portal Theme", filters={"theme_name": ("like", "ZT %")}, pluck="name"):
			frappe.db.set_value("Portal Theme", name, "is_live", 0)
			frappe.delete_doc("Portal Theme", name, force=True)
		themes.clear_cache()

	def test_defaults_seeded_and_one_live(self):
		names = set(frappe.get_all("Portal Theme", pluck="name"))
		self.assertTrue({"Classic Navy", "Modern Light", "Dark Luxury", "Marketplace"} <= names)
		self.assertEqual(frappe.db.count("Portal Theme", {"is_live": 1}), 1)

	def test_new_theme_takes_template_values_and_default_sections(self):
		doc = new_theme("ZT Lux", "Luxury")
		self.assertEqual(doc.tone, "Dark")
		self.assertTrue(doc.sections and doc.sections[0].section_key == "hero")

	def test_empty_field_falls_back_to_template(self):
		doc = new_theme("ZT Fallback", "Modern")
		doc.db_set("primary_color", "")
		t = themes.resolve(frappe.get_doc("Portal Theme", doc.name))
		self.assertEqual(t.primary_color, themes.template_values("Modern")["values"]["primary_color"])

	def test_bad_colour_and_unreadable_contrast_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			new_theme("ZT Bad", primary_color="not-a-colour")
		with self.assertRaises(frappe.ValidationError):
			new_theme("ZT Low", background_color="#ffffff", text_color="#f4f4f4", heading_color="#f4f4f4")

	def test_unsafe_link_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			new_theme("ZT Link", links=[{"link_group": "Header", "label": "x", "url": "javascript:alert(1)", "enabled": 1}])

	def test_custom_css_is_sanitised(self):
		for bad in ("@import url(x.css);", "a{background:url(https://evil.test/x.png)}", "</style><script>", "a{width:expression(1)}"):
			with self.assertRaises(frappe.ValidationError):
				themes.clean_css(bad)
		self.assertIn("color", themes.clean_css("/* hi */ .eb-hero{color:red}"))
		self.assertIn("/img/a.png", themes.clean_css(".x{background:url(/img/a.png)}"))

	def test_css_for_emits_variables_and_layout_attrs(self):
		t = themes.resolve(new_theme("ZT Css", "Marketplace"))
		css = themes.css_for(t)
		self.assertIn("--eb-", css)
		self.assertEqual(themes.layout_attrs(t)["data-template"], "marketplace")

	def test_sections_hero_first_and_deduped(self):
		doc = new_theme("ZT Sec", sections=[
			{"section_key": "featured", "enabled": 1}, {"section_key": "hero", "enabled": 0}, {"section_key": "featured", "enabled": 1}])
		keys = [s.section_key for s in doc.sections]
		self.assertEqual(keys[0], "hero")
		self.assertEqual(keys.count("featured"), 1)
		self.assertEqual(doc.sections[0].enabled, 1)

	def test_publish_revert_and_live_cannot_be_deleted(self):
		a = new_theme("ZT A", "Modern")
		theme_admin.publish(a.name)
		self.assertEqual(frappe.db.get_single_value("Portal Theme Settings", "active_theme"), a.name)
		self.assertEqual(themes.load_active().template, "Modern")
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Portal Theme", a.name)
		# a draft edit is invisible until publish
		frappe.db.set_value("Portal Theme", a.name, "primary_color", "#aa0000")
		themes.clear_cache(a.name)
		self.assertNotEqual(themes.load_active().primary_color, "#aa0000")
		theme_admin.publish(self.live_before)
		theme_admin.revert(self.live_before)
		self.assertEqual(frappe.db.get_single_value("Portal Theme Settings", "active_theme"), self.live_before)

	def test_duplicate_is_a_draft(self):
		copy = theme_admin.duplicate("Modern Light", "ZT Copy")
		self.assertEqual(frappe.db.get_value("Portal Theme", copy, "is_live"), 0)

	def test_preview_only_for_admins(self):
		new_theme("ZT Prev", "Luxury")
		frappe.form_dict["theme_preview"] = "ZT Prev"
		try:
			theme, preview = themes.current_theme()
			self.assertEqual(preview, "ZT Prev")
			frappe.set_user("Guest")
			theme, preview = themes.current_theme()
			self.assertIsNone(preview)
		finally:
			frappe.form_dict.pop("theme_preview", None)

	def test_admin_api_blocked_for_guests(self):
		frappe.set_user("Guest")
		for fn, args in ((theme_admin.gallery, ()), (theme_admin.publish, ("Modern Light",)), (theme_admin.duplicate, ("Modern Light", "ZT X"))):
			with self.assertRaises(frappe.PermissionError):
				fn(*args)
