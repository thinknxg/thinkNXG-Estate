"""Integration tests for Phases 3-8: owner portal, viewing requests, search, CRM, comms, reports, roles.

bench --site TEST_SITE run-tests --app thinknxg_estate --module thinknxg_estate.tests.test_estate_portal_crm
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from thinknxg_estate.tests.test_estate_integration import company, make_lease, make_tenant


def make_owner(suffix, portal=True):
	owner = frappe.get_doc({"doctype": "Property Owner", "owner_name": f"Owner {suffix}", "company": company(),
	                        "email": f"owner.{suffix.lower()}@example.com", "enable_portal": 1 if portal else 0}).insert()
	return owner.reload()


def make_owned_unit(owner, suffix, rent=6000, city="Muscat"):
	prop = frappe.get_doc({"doctype": "Property", "property_name": f"Building {suffix}",
	                       "property_type": "Apartment Building", "ownership_type": "Landlord",
	                       "country": "Oman", "company": company(), "owner_ref": owner.name,
	                       "city": city}).insert()
	unit = frappe.get_doc({"doctype": "Unit", "property": prop.name, "unit_no": f"{suffix}-1",
	                       "unit_type": "2BR", "status": "Vacant", "bedrooms": 2, "bathrooms": 2,
	                       "area_sqm": 120,
	                       # annual rent is derived from the unit's Rent charge rows
	                       "charges": [{"charge_type": "Rent", "description": "Rent", "amount": rent,
	                                    "frequency": "Annual"}]}).insert()
	return prop, unit


class TestOwnerPortal(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_owner_sees_only_own_portfolio(self):
		from thinknxg_estate.portal.api.owner import dashboard

		owner_a, owner_b = make_owner("OPA"), make_owner("OPB")
		self.assertTrue(owner_a.portal_user)
		self.assertIn("Property Owner", frappe.get_roles(owner_a.portal_user))
		_, unit_a = make_owned_unit(owner_a, "OPA")
		_, unit_b = make_owned_unit(owner_b, "OPB")
		lease = make_lease(make_tenant("OPA", "+96890000301"), unit_a, rent=1200)

		frappe.set_user(owner_a.portal_user)
		data = dashboard()
		self.assertEqual(data["property_count"], 1)
		self.assertEqual([u.name for u in data["units"]], [unit_a.name])
		self.assertEqual([l.name for l in data["leases"]], [lease.name])
		self.assertEqual(data["occupancy_rate"], 100.0)
		self.assertNotIn(unit_b.name, str(data))

	def test_statement_of_another_owner_is_refused(self):
		from thinknxg_estate.portal.api.owner import statement

		owner_a, owner_b = make_owner("OPC"), make_owner("OPD")
		st = frappe.get_doc({"doctype": "Owner Statement", "property_owner": owner_b.name, "company": company(),
		                     "period_from": add_days(nowdate(), -30), "period_to": nowdate()})
		st.insert(ignore_permissions=True)
		frappe.set_user(owner_a.portal_user)
		with self.assertRaises(frappe.PermissionError):
			statement(st.name)

	def test_tenant_and_staff_are_not_owners(self):
		from thinknxg_estate.portal.api.owner import dashboard

		with self.assertRaises(frappe.PermissionError):
			dashboard()  # Administrator has no owner profile


class TestListingViewing(IntegrationTestCase):
	def _listing(self, suffix):
		owner = make_owner(suffix, portal=False)
		_, unit = make_owned_unit(owner, suffix)
		return frappe.get_doc({"doctype": "Listing", "title": f"Listing {suffix}", "unit": unit.name,
		                       "listing_type": "Rent", "headline_price": 6000, "is_published": 1,
		                       "city": "Muscat"}).insert(), unit

	def test_viewing_request_creates_visit_booking_for_crm_lead(self):
		from thinknxg_estate.portal.api.listings import submit_inquiry

		listing, unit = self._listing("LV1")
		frappe.set_user("Guest")
		out = submit_inquiry(full_name="Viewing Visitor", mobile="+96891110031", listing=listing.name,
		                     inquiry_type="Viewing", preferred_date=add_days(nowdate(), 2),
		                     preferred_time_slot="10:00 - 12:00")
		frappe.set_user("Administrator")
		inquiry = frappe.get_doc("Listing Inquiry", out["inquiry"])
		self.assertEqual(inquiry.inquiry_type, "Viewing")
		booking = frappe.get_doc("Site Visit Booking", inquiry.site_visit_booking)
		self.assertEqual(booking.unit, unit.name)
		self.assertEqual(booking.re_lead, inquiry.re_lead)

	def test_viewing_needs_a_valid_future_slot(self):
		from thinknxg_estate.portal.api.listings import submit_inquiry

		frappe.set_user("Guest")
		for date, slot in ((add_days(nowdate(), -1), "10:00 - 12:00"), (add_days(nowdate(), 2), "03:00"),
		                   (add_days(nowdate(), 200), "10:00 - 12:00")):
			with self.assertRaises(frappe.ValidationError):
				submit_inquiry(full_name="X", mobile="+96891110032", inquiry_type="Viewing",
				               preferred_date=date, preferred_time_slot=slot)
		frappe.set_user("Administrator")

	def test_search_filters_and_sort(self):
		from thinknxg_estate.portal.api.listings import search

		listing, _ = self._listing("LV2")
		found = {r["name"] for r in search(city="Muscat", bathrooms=2, min_area=100, page_size=30)["results"]}
		self.assertIn(listing.name, found)
		none = {r["name"] for r in search(city="Muscat", min_area=500, page_size=30)["results"]}
		self.assertNotIn(listing.name, none)
		prices = [r["headline_price"] for r in search(sort="price_asc", page_size=30)["results"]]
		self.assertEqual(prices, sorted(prices))


def make_agent(suffix, roles=("RE Sales Agent",)):
	email = f"agent.{suffix.lower()}@example.com"
	if not frappe.db.exists("User", email):
		user = frappe.get_doc({"doctype": "User", "email": email, "first_name": f"Agent {suffix}",
		                       "user_type": "System User", "send_welcome_email": 0}).insert()
		user.add_roles(*roles)
	return frappe.get_doc({"doctype": "RE Agent", "agent_name": f"Agent {suffix}", "user": email,
	                       "is_active": 1, "commission_type": "Flat", "flat_amount": 100}).insert()


class TestCRMMatchingAndOwnership(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_matching_scores_and_explains(self):
		from thinknxg_estate.crm.matching import match_units

		owner = make_owner("MT1", portal=False)
		_, good = make_owned_unit(owner, "MT1-good", rent=6000, city="Seeb")
		_, pricey = make_owned_unit(owner, "MT1-pricey", rent=20000, city="Seeb")
		lead = frappe.get_doc({"doctype": "RE Lead", "full_name": "Matcher", "mobile": "+96891110041",
		                       "interest_type": "Rent", "preferred_property_type": "Apartment",
		                       "preferred_location": "Seeb", "budget_max": 6500, "bedrooms_required": 2}).insert()
		matches = {m["unit"]: m for m in match_units(lead.name, limit=50)}
		self.assertIn(good.name, matches)
		self.assertNotIn(pricey.name, matches, "units far above budget are excluded")
		self.assertGreaterEqual(matches[good.name]["score"], 80)
		self.assertIn("within budget", matches[good.name]["reasons"])

	def test_occupied_unit_matches_when_lease_ends_before_move_in(self):
		from thinknxg_estate.crm.matching import match_units

		owner = make_owner("MT2", portal=False)
		_, unit = make_owned_unit(owner, "MT2", rent=6000, city="Bausher")
		make_lease(make_tenant("MT2", "+96890000401"), unit, months=3)
		base = {"doctype": "RE Lead", "full_name": "Later Mover", "mobile": "+96891110042",
		        "preferred_location": "Bausher", "budget_max": 7000}
		soon = frappe.get_doc(dict(base, possession_date=add_days(nowdate(), 30))).insert()
		later = frappe.get_doc(dict(base, mobile="+96891110043", possession_date=add_days(nowdate(), 150))).insert()
		self.assertNotIn(unit.name, {m["unit"] for m in match_units(soon.name, limit=50)})
		self.assertIn(unit.name, {m["unit"] for m in match_units(later.name, limit=50)})

	def test_qualifying_a_lead_records_recommendations(self):
		owner = make_owner("MT3", portal=False)
		make_owned_unit(owner, "MT3", rent=5000, city="Ghubrah")
		lead = frappe.get_doc({"doctype": "RE Lead", "full_name": "Qualified One", "mobile": "+96891110044",
		                       "preferred_location": "Ghubrah", "budget_max": 5500}).insert()
		lead.status = "Qualified"
		lead.save()
		comments = frappe.get_all("Comment", {"reference_doctype": "RE Lead", "reference_name": lead.name},
		                          pluck="content")
		self.assertTrue(any("Recommended properties" in (c or "") for c in comments))

	def test_sales_agents_see_only_their_leads(self):
		mine, other = make_agent("OWN1"), make_agent("OWN2")
		frappe.db.set_single_value("RE CRM Settings", "agents_see_own_records", 1)
		lead_mine = frappe.get_doc({"doctype": "RE Lead", "full_name": "Mine", "mobile": "+96891110051",
		                            "assigned_agent": mine.name}).insert()
		lead_other = frappe.get_doc({"doctype": "RE Lead", "full_name": "Other", "mobile": "+96891110052",
		                             "assigned_agent": other.name}).insert()
		frappe.set_user(mine.user)
		visible = frappe.get_list("RE Lead", pluck="name", limit=1000)
		self.assertIn(lead_mine.name, visible)
		self.assertNotIn(lead_other.name, visible)
		self.assertFalse(frappe.has_permission("RE Lead", "read", doc=lead_other.name))
		frappe.set_user("Administrator")
		frappe.db.set_single_value("RE CRM Settings", "agents_see_own_records", 0)
		frappe.set_user(mine.user)
		self.assertIn(lead_other.name, frappe.get_list("RE Lead", pluck="name", limit=1000))
		frappe.set_user("Administrator")
		frappe.db.set_single_value("RE CRM Settings", "agents_see_own_records", 1)


class TestCommunications(IntegrationTestCase):
	def setUp(self):
		frappe.db.set_single_value("WhatsApp Settings", "enabled", 1)

	def tearDown(self):
		frappe.db.set_single_value("WhatsApp Settings", "enabled", 0)

	def test_outside_window_without_template_is_skipped_with_reason(self):
		from thinknxg_estate.channels.whatsapp import send_text

		log = frappe.get_doc("WhatsApp Message Log", send_text("+96891119999", "hello", purpose="Follow Up"))
		self.assertEqual(log.status, "Skipped")
		self.assertIn("Follow Up", log.response)

	def test_inside_window_or_with_template_is_queued(self):
		from frappe.utils import add_to_date, now_datetime

		from thinknxg_estate.channels.whatsapp import send_text

		frappe.get_doc({"doctype": "Conversation Session", "phone_number": "96891118888",
		                "window_expires_at": add_to_date(now_datetime(), hours=5)}).insert(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("WhatsApp Message Log", send_text("+96891118888", "hi"), "status"),
		                 "Queued")
		frappe.get_doc({"doctype": "WhatsApp Template", "template_name": "rent_reminder_test",
		                "language_code": "en", "purpose": "Rent Reminder",
		                "approval_status": "Approved"}).insert(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("WhatsApp Message Log",
		                                     send_text("+96891117777", "due", purpose="Rent Reminder",
		                                               variables=["A", "1", "2"]), "status"), "Queued")

	def test_lead_timeline_collects_enquiries_messages_and_notes(self):
		from thinknxg_estate.channels.timeline import get_timeline
		from thinknxg_estate.channels.whatsapp import send_text
		from thinknxg_estate.portal.api.listings import submit_inquiry

		out = submit_inquiry(full_name="Timeline Person", mobile="+96891116666", message="Is parking included?")
		lead = frappe.db.get_value("Listing Inquiry", out["inquiry"], "re_lead")
		send_text("+96891116666", "Welcome!", reference_doctype="RE Lead", reference_name=lead)
		frappe.get_doc("RE Lead", lead).add_comment("Comment", "Called, wants a viewing")
		channels = {i["channel"] for i in get_timeline("RE Lead", lead)}
		self.assertTrue({"Enquiry", "WhatsApp", "Note"} <= channels, channels)


class TestReports(IntegrationTestCase):
	def test_financial_reports_match_source_records(self):
		from frappe.desk.query_report import run

		owner = make_owner("RP1", portal=False)
		prop, unit = make_owned_unit(owner, "RP1", rent=4800)
		lease = make_lease(make_tenant("RP1", "+96890000501"), unit, rent=1200, deposit=250, frequency="Quarterly")
		lease.reload()
		frappe.db.set_value("Security Deposit", lease.security_deposit, "status", "Held")
		year = frappe.utils.getdate().year
		window = {"from_date": f"{year - 1}-01-01", "to_date": f"{year + 2}-12-31"}

		prof = {r["property"]: r for r in run("Property Profitability", filters=dict(window, property=prop.name))["result"]
		        if isinstance(r, dict) and r.get("property")}
		self.assertAlmostEqual(prof[prop.name]["rent_billed"], 1200, places=2)
		self.assertEqual(prof[prop.name]["rent_collected"], 0)

		deposits = {r["deposit"]: r for r in run("Deposit Register", filters={})["result"]
		            if isinstance(r, dict) and r.get("deposit")}
		self.assertEqual(deposits[lease.security_deposit]["held"], 250)

		reg = {r["property"]: r for r in run("Property Register", filters={})["result"]
		       if isinstance(r, dict) and r.get("property")}
		self.assertEqual((reg[prop.name]["units"], reg[prop.name]["occupied"], reg[prop.name]["occupancy"]), (1, 1, 100.0))

		avail = {r["unit"] for r in run("Unit Availability", filters={"available_by": f"{year + 3}-12-31"})["result"]
		         if isinstance(r, dict) and r.get("unit")}
		self.assertIn(unit.name, avail, "an occupied unit whose lease ends before the date is available")
		avail_now = {r["unit"] for r in run("Unit Availability", filters={})["result"]
		             if isinstance(r, dict) and r.get("unit")}
		self.assertNotIn(unit.name, avail_now)


class TestDashboard(IntegrationTestCase):
	def test_overview_kpis_follow_records_and_filters(self):
		from thinknxg_estate.core.dashboard import get_overview

		owner = make_owner("DB1", portal=False)
		prop, unit = make_owned_unit(owner, "DB1", rent=3600, city="Sohar")
		make_lease(make_tenant("DB1", "+96890000601"), unit, rent=1200, frequency="Monthly")
		scoped = get_overview(property=prop.name)
		k = scoped["kpis"]
		self.assertEqual((k["total_properties"], k["total_units"], k["occupied_units"], k["active_leases"]),
		                 (1, 1, 1, 1))
		self.assertEqual(k["occupancy_rate"], 100.0)
		self.assertAlmostEqual(k["monthly_rent_billed"], 100, places=2)  # 1,200 over 12 monthly installments
		by_city = get_overview(city="Sohar")["kpis"]
		self.assertGreaterEqual(by_city["total_units"], 1)
		everything = get_overview()["kpis"]
		self.assertGreaterEqual(everything["total_units"], k["total_units"])
		self.assertTrue(scoped["charts"]["occupancy_by_property"])


def make_user(email, *roles):
	if not frappe.db.exists("User", email):
		user = frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0],
		                       "user_type": "System User", "send_welcome_email": 0}).insert()
		user.add_roles(*roles)
	return email


class TestRoleMatrix(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_broker_follows_ownership_and_is_kept_out_of_the_console(self):
		from thinknxg_estate.core import api as core_api

		broker = make_agent("BRK1", roles=("Broker",))
		other = make_agent("BRK2")
		frappe.db.set_single_value("RE CRM Settings", "agents_see_own_records", 1)
		mine = frappe.get_doc({"doctype": "RE Lead", "full_name": "Broker lead", "mobile": "+96891110061",
		                       "assigned_agent": broker.name}).insert()
		theirs = frappe.get_doc({"doctype": "RE Lead", "full_name": "Other lead", "mobile": "+96891110062",
		                         "assigned_agent": other.name}).insert()
		frappe.set_user(broker.user)
		visible = frappe.get_list("RE Lead", pluck="name", limit=1000)
		self.assertIn(mine.name, visible)
		self.assertNotIn(theirs.name, visible)
		with self.assertRaises(frappe.PermissionError):
			core_api.get_dashboard_stats()

	def test_receptionist_captures_leads_but_has_no_console_or_finance(self):
		from thinknxg_estate.crm import api as crm_api

		frappe.set_user(make_user("front.desk@example.com", "Receptionist"))
		lead = frappe.get_doc({"doctype": "RE Lead", "full_name": "Walk-in", "mobile": "+96891110063"}).insert()
		self.assertTrue(lead.name)
		self.assertFalse(frappe.has_permission("Post Dated Cheque", "read"))
		self.assertFalse(frappe.has_permission("Lease Contract", "create"))
		with self.assertRaises(frappe.PermissionError):
			crm_api.get_leads_list()

	def test_technician_updates_jobs_but_cannot_submit_or_see_leases(self):
		frappe.set_user(make_user("tech.one@example.com", "Maintenance Technician"))
		self.assertTrue(frappe.has_permission("Maintenance Job", "write"))
		self.assertFalse(frappe.has_permission("Maintenance Job", "submit"))
		self.assertFalse(frappe.has_permission("Lease Contract", "read"))
		self.assertFalse(frappe.has_permission("RE Lead", "read"))

	def test_sales_agent_can_match_but_not_use_console(self):
		from thinknxg_estate.core import api as core_api
		from thinknxg_estate.crm.matching import get_matching_units

		agent = make_agent("MAT1")
		lead = frappe.get_doc({"doctype": "RE Lead", "full_name": "Agent lead", "mobile": "+96891110064",
		                       "assigned_agent": agent.name, "budget_max": 9000}).insert()
		frappe.set_user(agent.user)
		self.assertIsInstance(get_matching_units(lead.name), list)
		with self.assertRaises(frappe.PermissionError):
			core_api.get_units_list()

	def test_owner_statement_is_readable_by_finance_roles(self):
		frappe.set_user(make_user("acct.one@example.com", "Accounts User"))
		self.assertTrue(frappe.has_permission("Owner Statement", "read"))
		self.assertTrue(frappe.has_permission("Owner Statement", "submit"))
