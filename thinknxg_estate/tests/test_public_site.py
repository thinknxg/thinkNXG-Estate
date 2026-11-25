"""Integration tests for the merged public site (/properties): listing sync rules, whole-property
listings, map points, visitor wishlist and saved-search alerts, compare, redirects.

bench --site TEST_SITE run-tests --app thinknxg_estate --module thinknxg_estate.tests.test_public_site
"""

import frappe
from frappe.tests import IntegrationTestCase

from thinknxg_estate.tests.test_estate_integration import company
from thinknxg_estate.tests.test_estate_portal_crm import make_owned_unit, make_owner


def make_villa(suffix, rent=24000, live=True, lat=23.6, lng=58.5):
	prop = frappe.get_doc({
		"doctype": "Property", "property_name": f"Villa {suffix}", "property_type": "Villa",
		"ownership_type": "Landlord", "country": "Oman", "company": company(), "city": "Muscat",
		"area": "Qurum", "bedrooms": 4, "bathrooms": 3, "area_sqm": 350,
		# annual rent is derived from the property's Rent charge rows
		"charges": [{"charge_type": "Rent", "description": "Rent", "amount": rent, "frequency": "Annual"}],
		"published_to_portal": 1, "latitude": lat, "longitude": lng}).insert()
	if live:
		prop.is_live = 1
		prop.save()
	return prop


def make_visitor(email):
	"""A website visitor as /properties/account creates one: a Website User linked to a portal Lead."""
	if frappe.db.exists("User", email):
		return email
	lead = frappe.get_doc({"doctype": "Lead", "lead_name": "Visitor", "email_id": email,
	                      "mobile_no": "+96890001111"}).insert(ignore_permissions=True)
	frappe.get_doc({"doctype": "User", "email": email, "first_name": "Visitor", "user_type": "Website User",
	                "send_welcome_email": 0, "portal_lead": lead.name}).insert(ignore_permissions=True)
	return email


def published(filters):
	return frappe.db.get_value("Listing", {**filters, "is_published": 1})


class TestListingSync(IntegrationTestCase):
	def test_whole_property_gets_its_own_listing(self):
		villa = make_villa("PS1")
		name = published({"property_ref": villa.name, "unit": ["is", "not set"]})
		self.assertTrue(name, "a live villa with no units should be listed")
		listing = frappe.get_doc("Listing", name)
		self.assertEqual((listing.bedrooms, listing.unit_type, listing.city), (4, "Villa", "Muscat"))

		frappe.get_doc({"doctype": "Unit", "property": villa.name, "unit_no": "PS1-A", "unit_type": "2BR",
		                "status": "Vacant"}).insert()
		self.assertFalse(published({"property_ref": villa.name, "unit": ["is", "not set"]}),
		                 "adding units ends the whole-property listing")

	def test_unit_needs_website_flag(self):
		owner = make_owner("PS2", portal=False)
		prop, unit = make_owned_unit(owner, "PS2")
		prop.is_live = 1
		prop.save()
		self.assertFalse(published({"unit": unit.name}), "not shown until the unit is flagged for the website")
		unit.reload()
		unit.published_to_portal = 1
		unit.save()
		self.assertTrue(published({"unit": unit.name}))

	def test_manual_publish_sets_website_flag(self):
		owner = make_owner("PS3", portal=False)
		_, unit = make_owned_unit(owner, "PS3")
		frappe.get_doc({"doctype": "Listing", "title": "Manual PS3", "unit": unit.name, "listing_type": "Rent",
		                "headline_price": 6000, "is_published": 1}).insert()
		self.assertEqual(frappe.db.get_value("Unit", unit.name, "published_to_portal"), 1,
		                 "a hand-published listing must survive the nightly sync")

	def test_listing_needs_unit_or_property(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "Listing", "title": "Nothing", "listing_type": "Rent",
			                "headline_price": 1}).insert()

	def test_same_title_gets_unique_name_and_route(self):
		a = published({"property_ref": make_villa("Twin").name})
		b = published({"property_ref": make_villa("Twin").name})
		self.assertTrue(a and b and a != b)
		self.assertNotEqual(frappe.db.get_value("Listing", a, "route"), frappe.db.get_value("Listing", b, "route"))

	def test_property_with_units_cannot_be_listed_whole(self):
		owner = make_owner("PS4", portal=False)
		prop, _ = make_owned_unit(owner, "PS4")
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "Listing", "title": "Whole PS4", "property_ref": prop.name,
			                "listing_type": "Rent", "headline_price": 1, "is_published": 1}).insert()


class TestSearchAndMap(IntegrationTestCase):
	def test_map_points_follow_search_filters(self):
		from thinknxg_estate.portal.api.listings import map_points

		villa = make_villa("PS5", rent=99000)
		points = map_points(min_price=98000, max_price=100000)["points"]
		mine = [p for p in points if p["title"] == "Villa PS5"]
		self.assertEqual(len(mine), 1)
		self.assertAlmostEqual(mine[0]["lat"], 23.6)
		self.assertFalse([p for p in map_points(min_price=200000)["points"] if p["title"] == "Villa PS5"])
		self.assertNotIn("property_ref", mine[0], "internal property ids stay off the public map")
		frappe.db.set_value("Property", villa.name, {"latitude": 0, "longitude": 0})
		self.assertFalse([p for p in map_points(min_price=98000, max_price=100000)["points"]
		                  if p["title"] == "Villa PS5"], "listings without coordinates are left off the map")

	def test_search_returns_coordinates_and_hides_unpublished(self):
		from thinknxg_estate.portal.api.listings import search

		make_villa("PS6", rent=77001)
		rows = search(min_price=77000, max_price=77002)["results"]
		self.assertEqual([r["title"] for r in rows], ["Villa PS6"])
		self.assertIsNotNone(rows[0]["latitude"])
		make_villa("PS7", rent=77001, live=False)
		self.assertEqual(len(search(min_price=77000, max_price=77002)["results"]), 1)

	def test_compare_keeps_order_and_caps_at_three(self):
		from thinknxg_estate.portal.api.listings import compare_rows

		names = [published({"property_ref": make_villa(f"PC{i}").name}) for i in range(4)]
		rows = compare_rows([names[2], names[0], names[1], names[3]])
		self.assertEqual([r.name for r in rows], [names[2], names[0], names[1]])


class TestVisitor(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_wishlist_by_listing_for_whole_property(self):
		from thinknxg_estate.portal.api.visitor import saved_listing_names, toggle_wishlist

		listing = published({"property_ref": make_villa("PV1").name})
		frappe.set_user(make_visitor("pv1@example.com"))
		self.assertTrue(toggle_wishlist(listing)["saved"])
		self.assertIn(listing, saved_listing_names())
		self.assertFalse(toggle_wishlist(listing)["saved"])
		self.assertNotIn(listing, saved_listing_names())

	def test_guest_cannot_save(self):
		from thinknxg_estate.portal.api.visitor import saved_listing_names

		frappe.set_user("Guest")
		self.assertEqual(saved_listing_names(), set())

	def test_standard_signup_user_gets_a_lead_on_first_use(self):
		from thinknxg_estate.portal.api.visitor import toggle_wishlist

		listing = published({"property_ref": make_villa("PV2").name})
		user = frappe.get_doc({"doctype": "User", "email": "pv2@example.com", "first_name": "PV2",
		                       "user_type": "Website User"}).insert(ignore_permissions=True)
		frappe.set_user(user.name)
		self.assertTrue(toggle_wishlist(listing)["saved"])
		self.assertTrue(frappe.db.get_value("User", user.name, "portal_lead"))

	def test_saved_search_alert_uses_listings(self):
		from thinknxg_estate.core.listing_portal_api.listing_portal import check_saved_searches
		from thinknxg_estate.portal.api.visitor import save_search

		frappe.set_user(make_visitor("pv3@example.com"))
		saved = save_search(city="Muscat", unit_type="Villa", min_price=55554, max_price=55556)
		frappe.set_user("Administrator")
		frappe.db.set_value("Saved Search", saved["name"], "last_checked", "2000-01-01 00:00:00")
		make_villa("PV3", rent=55555)
		lead = frappe.db.get_value("User", "pv3@example.com", "portal_lead")
		before = frappe.db.count("Notification Log", {"subject": ["like", "%saved search%"]})
		from unittest.mock import patch

		with patch.object(frappe.db, "commit"):  # the job commits; keep the test rolled back
			check_saved_searches()
		self.assertGreater(frappe.db.count("Notification Log", {"subject": ["like", "%saved search%"]}), before)
		self.assertTrue(lead)

	def test_save_search_needs_a_filter(self):
		from thinknxg_estate.portal.api.visitor import save_search

		frappe.set_user(make_visitor("pv4@example.com"))
		with self.assertRaises(frappe.ValidationError):
			save_search()

	def test_viewing_request_for_whole_property(self):
		from thinknxg_estate.portal.api.listings import submit_inquiry

		villa = make_villa("PV5")
		listing = published({"property_ref": villa.name})
		frappe.set_user(make_visitor("pv5@example.com"))
		submit_inquiry("Visitor", "+96890005555", listing=listing, inquiry_type="Viewing",
		               preferred_date=frappe.utils.add_days(frappe.utils.nowdate(), 2),
		               preferred_time_slot="10:00 - 12:00")
		frappe.set_user("Administrator")
		booking = frappe.get_all("Site Visit Booking", filters={"property": villa.name},
		                         fields=["unit", "lead", "status"])
		self.assertEqual(len(booking), 1)
		self.assertFalse(booking[0].unit)
		self.assertEqual(booking[0].lead, frappe.db.get_value("User", "pv5@example.com", "portal_lead"))


class TestRedirect(IntegrationTestCase):
	def test_old_listings_url_redirects(self):
		redirects = frappe.get_hooks("website_redirects")
		self.assertIn({"source": "/listings", "target": "/properties"}, redirects)


class TestRedesignedSearch(IntegrationTestCase):
	"""Backend filters, rendered results, suggestions and saved-search params behind the new /properties."""

	def _listing(self, villa):
		return published({"property_ref": villa.name, "unit": ["is", "not set"]})

	def test_filters_facets_and_bounds(self):
		from thinknxg_estate.portal.api.listings import listing_query

		villa = make_villa("RS1", lat=23.6, lng=58.5)
		name = self._listing(villa)

		def found(**kw):
			return name in frappe.get_all("Listing", pluck="name", limit_page_length=0, **listing_query(**kw))

		self.assertEqual(frappe.db.get_value("Listing", name, ["usage", "development_status"]),
		                 (villa.usage, "Ready"))
		self.assertTrue(found(category="villas"))
		self.assertTrue(found(unit_type="Villa,Studio", city="Muscat"))
		self.assertTrue(found(q="Villa RS1"))
		self.assertFalse(found(q="no-such-place-anywhere"))
		self.assertTrue(found(north=24, south=23, east=59, west=58))
		self.assertFalse(found(north=1, south=0, east=1, west=0), "a 0,0 box must not match unlocated properties")
		self.assertFalse(found(bedrooms=5))
		self.assertTrue(found(bedrooms=4, bathrooms=3))

	def test_amenity_filter_needs_all_selected(self):
		from thinknxg_estate.portal.api.listings import listing_query

		villa = make_villa("RS2")
		name = self._listing(villa)
		amenity = frappe.get_all("Amenity", pluck="name", limit=2)
		if len(amenity) < 2:
			self.skipTest("needs two Amenity records")
		villa.append("amenities", {"amenity": amenity[0]})
		villa.save()
		query = lambda a: name in frappe.get_all("Listing", pluck="name", limit_page_length=0, **listing_query(amenity=a))
		self.assertTrue(query(amenity[0]))
		self.assertFalse(query(",".join(amenity)))

	def test_results_html_and_chips(self):
		from thinknxg_estate.portal.api import catalog

		make_villa("RS3")
		out = catalog.search_results(page=1, layout="list", city="Muscat", bedrooms="3")
		self.assertGreater(out["total"], 0)
		self.assertIn("<article", out["html"])
		self.assertEqual({c["key"] for c in out["chips"]}, {"city", "bedrooms"})
		empty = catalog.search_results(page=1, layout="grid", q="zzz-nothing-matches")
		self.assertEqual(empty["total"], 0)
		self.assertNotIn("<article", empty["html"])

	def test_suggest_and_parse_args(self):
		from thinknxg_estate.portal.api import catalog

		make_villa("RS4")
		items = catalog.suggest("mus")["items"]
		self.assertTrue(any(i["type"] == "city" and i["value"] == "Muscat" for i in items))
		self.assertEqual(catalog.suggest("")["items"], [])
		args = catalog.parse_args({"city": "Muscat", "featured": "0", "south": "0", "north": "1", "junk": "x"})
		self.assertEqual(args, {"city": "Muscat", "south": "0", "north": "1"})

	def test_saved_search_keeps_full_params(self):
		import json

		from thinknxg_estate.portal.api import visitor
		from thinknxg_estate.portal.api.listings import listing_query

		email = make_visitor("redesign.visitor@example.com")
		frappe.set_user(email)
		try:
			out = visitor.save_search(params=json.dumps({"city": "Muscat", "category": "villas", "evil": "1"}))
			saved = frappe.get_doc("Saved Search", out["name"] if isinstance(out, dict) and "name" in out else out)
			params = json.loads(saved.search_params)
			self.assertEqual(params, {"city": "Muscat", "category": "villas"})
			self.assertTrue(listing_query(**params)["filters"])
		finally:
			frappe.set_user("Administrator")

	def test_language_switch_accepts_only_supported_languages(self):
		from thinknxg_estate.portal.api import visitor

		with self.assertRaises(frappe.ValidationError):
			visitor.set_language("xx")

	def test_facet_refresh_follows_the_property(self):
		from thinknxg_estate.portal.sync import refresh_listing_facets

		villa = make_villa("RS5")
		name = self._listing(villa)
		frappe.db.set_value("Listing", name, {"usage": "Commercial", "development_status": "Under Development"})
		refresh_listing_facets(villa.name)
		self.assertEqual(frappe.db.get_value("Listing", name, ["usage", "development_status"]),
		                 (villa.usage, "Ready"))
