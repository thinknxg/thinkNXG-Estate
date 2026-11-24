"""Integration tests for thinkNXG Estate.

bench --site TEST_SITE run-tests --app thinknxg_estate --module thinknxg_estate.tests.test_estate_integration

Needs a site with thinkNXG ERP set up (a Company, fiscal year, Item Groups).
"""

import hashlib
from types import SimpleNamespace

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_months, flt, getdate, nowdate

COMPANY = None


def company():
	global COMPANY
	COMPANY = COMPANY or frappe.db.get_value("Company", {}, "name")
	return COMPANY


def make_unit(suffix, rent=6000):
	owner = frappe.get_doc({"doctype": "Property Owner", "owner_name": f"Owner {suffix}",
	                        "company": company()}).insert()
	prop = frappe.get_doc({"doctype": "Property", "property_name": f"Tower {suffix}",
	                       "property_type": "Apartment Building", "ownership_type": "Company",
	                       "country": "Oman", "company": company(), "owner_ref": owner.name,
	                       "city": "Muscat"}).insert()
	unit = frappe.get_doc({"doctype": "Unit", "property": prop.name, "unit_no": f"{suffix}-101",
	                       "unit_type": "2BR", "annual_rent": rent, "status": "Vacant"}).insert()
	return owner, prop, unit


def make_tenant(suffix, mobile, email=None):
	return frappe.get_doc({"doctype": "Tenant", "tenant_name": f"Tenant {suffix}", "mobile": mobile,
	                       "email": email}).insert()


def make_lease(tenant, unit, months=12, rent=1200, deposit=100, frequency="Quarterly", submit=True):
	lease = frappe.get_doc({
		"doctype": "Lease Contract", "tenant": tenant.name, "unit": unit.name,
		"start_date": nowdate(), "end_date": add_months(nowdate(), months),
		"payment_frequency": frequency, "security_deposit_amount": deposit,
		"charges": [{"charge_type": "Rent", "description": "Base Rent", "amount": rent}],
	}).insert()
	if submit:
		lease.submit()
	return lease


class TestLeasingLifecycle(IntegrationTestCase):
	def test_submit_creates_schedule_deposit_and_occupies_unit(self):
		_, _, unit = make_unit("LC1")
		tenant = make_tenant("LC1", "+96890000101")
		lease = make_lease(tenant, unit, rent=1200, deposit=100)
		lease.reload()

		self.assertEqual(lease.status, "Active")
		self.assertEqual(frappe.db.get_value("Unit", unit.name, "status"), "Occupied")
		self.assertEqual(frappe.db.get_value("Unit", unit.name, "current_lease"), lease.name)
		schedule = frappe.get_doc("Rent Schedule", lease.rent_schedule)
		self.assertEqual(len(schedule.installments), 4)
		self.assertAlmostEqual(sum(flt(r.amount) for r in schedule.installments), 1200, places=3)
		self.assertEqual(frappe.db.get_value("Security Deposit", lease.security_deposit, "amount"), 100)

	def test_cancel_releases_unit_and_cancels_open_installments(self):
		_, _, unit = make_unit("LC2")
		tenant = make_tenant("LC2", "+96890000102")
		lease = make_lease(tenant, unit)
		lease.reload()
		lease.cancel()
		self.assertEqual(frappe.db.get_value("Unit", unit.name, "status"), "Vacant")
		statuses = set(frappe.get_all("Rent Installment", {"parent": lease.rent_schedule}, pluck="status"))
		self.assertEqual(statuses, {"Cancelled"})

	def test_second_draft_on_same_unit_is_blocked(self):
		_, _, unit = make_unit("LC3")
		tenant = make_tenant("LC3", "+96890000103")
		make_lease(tenant, unit, submit=False)
		with self.assertRaises(frappe.ValidationError):
			make_lease(tenant, unit, submit=False)

	def test_submitting_a_lease_unpublishes_the_unit_listing(self):
		_, _, unit = make_unit("LC4")
		listing = frappe.get_doc({"doctype": "Listing", "title": "Listing LC4", "unit": unit.name,
		                         "listing_type": "Rent", "headline_price": 6000,
		                         "is_published": 1}).insert()
		tenant = make_tenant("LC4", "+96890000104")
		make_lease(tenant, unit)
		self.assertEqual(frappe.db.get_value("Listing", listing.name, "is_published"), 0)


	def test_pdc_submit_creates_payment_entry(self):
		"""Regression: pdc_bank_sync imported get_payment_entry from the wrong module, so
		submitting any cheque failed on v16."""
		_, _, unit = make_unit("LC5")
		tenant = make_tenant("LC5", "+96890000105")
		lease = make_lease(tenant, unit)
		account = frappe.db.get_value("Account", {"company": company(), "is_group": 0,
		                                          "account_type": ["in", ["Bank", "Cash"]]}, "name")
		pdc = frappe.get_doc({"doctype": "Post Dated Cheque", "tenant": tenant.name,
		                      "lease_contract": lease.name, "cheque_no": "LC5-1", "bank": "Bank Muscat",
		                      "cheque_date": nowdate(), "amount": 300, "company": company(),
		                      "deposit_account": account}).insert()
		pdc.submit()
		pe = frappe.db.get_value("Post Dated Cheque", pdc.name, "payment_entry")
		self.assertTrue(pe)
		self.assertEqual(flt(frappe.db.get_value("Payment Entry", pe, "paid_amount")), 300)


class TestPortalToCRM(IntegrationTestCase):
	"""Every portal enquiry must reach the CRM as one RE Lead per person."""

	def setUp(self):
		frappe.set_user("Guest")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_guest_unit_enquiry_keeps_contact_and_creates_lead(self):
		frappe.set_user("Administrator")
		_, _, unit = make_unit("PC1")
		frappe.set_user("Guest")
		from thinknxg_estate.core.listing_portal_api.listing_portal import submit_enquiry

		out = submit_enquiry(unit.name, name="Salim Visitor", phone="+96891110001", message="Is it free?")
		frappe.set_user("Administrator")
		enq = frappe.get_doc("Property Enquiry", out["name"])
		self.assertEqual(enq.full_name, "Salim Visitor")
		self.assertEqual(enq.mobile, "+96891110001")
		self.assertTrue(enq.re_lead)
		self.assertEqual(frappe.db.get_value("RE Lead", enq.re_lead, "mobile"), "+96891110001")

		# a repeat enquiry from the same number reuses the same lead
		frappe.set_user("Guest")
		again = submit_enquiry(unit.name, name="Salim Visitor", phone="+96891110001", message="Again")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Property Enquiry", again["name"], "re_lead"), enq.re_lead)

	def test_guest_enquiry_without_contact_is_refused(self):
		frappe.set_user("Administrator")
		_, _, unit = make_unit("PC2")
		frappe.set_user("Guest")
		from thinknxg_estate.core.listing_portal_api.listing_portal import submit_enquiry

		with self.assertRaises(frappe.ValidationError):
			submit_enquiry(unit.name, name="", phone="", message="hello")

	def test_listing_inquiry_creates_lead(self):
		from thinknxg_estate.portal.api.listings import submit_inquiry

		out = submit_inquiry(full_name="Aisha Buyer", mobile="+96891110002", message="Viewing please")
		frappe.set_user("Administrator")
		inquiry = frappe.get_doc("Listing Inquiry", out["inquiry"])
		self.assertEqual(inquiry.status, "Converted")
		self.assertEqual(frappe.db.get_value("RE Lead", inquiry.re_lead, "full_name"), "Aisha Buyer")

	def test_legacy_inquiry_endpoint_also_creates_lead(self):
		from thinknxg_estate.portal.api.inquiries import create

		out = create(full_name="Old Form User", mobile="+96891110003")
		frappe.set_user("Administrator")
		self.assertTrue(frappe.db.get_value("Listing Inquiry", out["reference"], "re_lead"))

	def test_email_only_portal_visitor_reaches_crm(self):
		frappe.set_user("Administrator")
		from thinknxg_estate.core.listing_portal_api.listing_portal import _get_or_create_re_lead

		lead = frappe.get_doc({"doctype": "Lead", "lead_name": "Web Visitor",
		                       "email_id": "web.visitor.pc5@example.com"}).insert()
		re_lead = _get_or_create_re_lead(lead.name)
		self.assertTrue(re_lead, "bridge must not depend on a mobile number")
		self.assertEqual(frappe.db.get_value("RE Lead", re_lead, "email"), "web.visitor.pc5@example.com")
		self.assertEqual(_get_or_create_re_lead(lead.name), re_lead)


class TestTenantSecurity(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.set_single_value("Property Settings", "enable_access_code_portal", 0)
		frappe.db.set_single_value("Property Settings", "allow_tenant_self_termination", 0)

	def _tenant_with_code(self, suffix, mobile, code="735193"):
		tenant = make_tenant(suffix, mobile)
		tenant.portal_access_code = code
		tenant.save()
		return tenant

	def test_access_code_portal_is_off_by_default(self):
		from thinknxg_estate.core.tenant_portal_api import tenant_portal_login

		self._tenant_with_code("SEC1", "+96890000201")
		frappe.db.set_single_value("Property Settings", "enable_access_code_portal", 0)
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			tenant_portal_login("+96890000201", "735193")

	def test_access_code_login_stores_only_a_token_hash(self):
		from thinknxg_estate.core import tenant_portal_api as api

		tenant = self._tenant_with_code("SEC2", "+96890000202")
		frappe.db.set_value("Tenant", tenant.name, "enable_portal", 1)
		frappe.db.set_single_value("Property Settings", "enable_access_code_portal", 1)
		frappe.set_user("Guest")
		with self.assertRaises(frappe.AuthenticationError):
			api.tenant_portal_login("+96890000202", "000000")
		out = api.tenant_portal_login("+96890000202", "735193")
		frappe.set_user("Administrator")
		stored = frappe.get_all("Tenant Portal Session", {"tenant": tenant.name}, pluck="token")
		self.assertNotIn(out["token"], stored)
		self.assertIn(hashlib.sha256(out["token"].encode()).hexdigest(), stored)
		frappe.set_user("Guest")
		self.assertEqual(api.resolve_tenant_from_token(out["token"]), tenant.name)
		with self.assertRaises(frappe.AuthenticationError):
			api.resolve_tenant_from_token(stored[0])  # the stored hash is not a usable token

	def test_tenant_cannot_record_own_payment(self):
		from thinknxg_estate.core import tenant_portal_api as api

		tenant = self._tenant_with_code("SEC3", "+96890000203")
		frappe.db.set_value("Tenant", tenant.name, "enable_portal", 1)
		frappe.db.set_single_value("Property Settings", "enable_access_code_portal", 1)
		frappe.set_user("Guest")
		token = api.tenant_portal_login("+96890000203", "735193")["token"]
		with self.assertRaises(frappe.PermissionError):
			api.tenant_portal_pay_installment(token, "any", 10)

	def _portal_tenant(self, suffix, mobile):
		email = f"tenant.{suffix.lower()}@example.com"
		tenant = make_tenant(suffix, mobile, email=email)
		tenant.enable_portal = 1
		tenant.save()
		_, _, unit = make_unit(suffix)
		lease = make_lease(tenant, unit)
		return tenant, lease, email

	def test_tenant_termination_is_a_request_by_default(self):
		from thinknxg_estate.portal.api.tenant import terminate_lease

		tenant, lease, user = self._portal_tenant("SEC4", "+96890000204")
		frappe.set_user(user)
		out = terminate_lease(termination_date=nowdate(), reasons="End of Tenancy")
		frappe.set_user("Administrator")
		self.assertEqual(out["status"], "Requested")
		self.assertEqual(frappe.db.get_value("Lease Contract", lease.name, "status"), "Active")
		self.assertTrue(frappe.db.exists("ToDo", {"reference_type": "Lease Contract",
		                                          "reference_name": lease.name}))

	def test_tenant_only_sees_own_leases(self):
		tenant_a, lease_a, user_a = self._portal_tenant("SEC5", "+96890000205")
		_, lease_b, _ = self._portal_tenant("SEC6", "+96890000206")
		frappe.set_user(user_a)
		visible = frappe.get_list("Lease Contract", pluck="name")
		self.assertIn(lease_a.name, visible)
		self.assertNotIn(lease_b.name, visible)
		self.assertFalse(frappe.has_permission("Lease Contract", "read", doc=lease_b.name))


	def test_tenant_cannot_run_finance_actions_on_own_documents(self):
		"""run_doc_method only checks read permission; state changes must check more."""
		tenant, lease, user = self._portal_tenant("SEC7", "+96890000207")
		pdc = frappe.get_doc({"doctype": "Post Dated Cheque", "tenant": tenant.name,
		                      "lease_contract": lease.name, "cheque_no": "SEC7-1", "bank": "Bank Muscat",
		                      "cheque_date": nowdate(), "amount": 300}).insert()
		deposit = lease.reload().security_deposit
		frappe.set_user(user)
		own_pdc = frappe.get_doc("Post Dated Cheque", pdc.name)  # reading is allowed
		for action in (own_pdc.mark_deposited, own_pdc.mark_cleared, own_pdc.mark_bounced):
			with self.assertRaises(frappe.PermissionError):
				action()
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Security Deposit", deposit).refund()
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Lease Contract", lease.name).terminate(termination_date=nowdate(),
			                                                       outstanding_rent=0)

	def test_website_users_cannot_call_staff_apis(self):
		from thinknxg_estate.core import api as core_api
		from thinknxg_estate.crm import api as crm_api

		_, _, user = self._portal_tenant("SEC8", "+96890000208")
		frappe.set_user(user)
		for fn in (core_api.get_dashboard_stats, core_api.get_tenants_list, crm_api.get_deals_list):
			with self.assertRaises(frappe.PermissionError):
				fn()
		frappe.set_user("Administrator")
		self.assertIn("total_properties", core_api.get_dashboard_stats())


class TestCompatibilityAndCRM(IntegrationTestCase):
	def test_legacy_api_paths_resolve_to_whitelisted_functions(self):
		overrides = frappe.get_hooks("override_whitelisted_methods")
		self.assertIn("re_core.re_core.api.get_dashboard_stats", overrides)
		for old, targets in overrides.items():
			if not old.startswith(("re_core.", "re_crm.", "re_portal.", "re_voice.")):
				continue
			fn = frappe.get_attr(targets[-1])
			self.assertIn(fn, frappe.whitelisted, old)

	def test_voice_command_handlers_resolve(self):
		for handler in frappe.get_all("Voice Command", pluck="handler"):
			self.assertTrue(handler.startswith("thinknxg_estate."), handler)
			frappe.get_attr(handler)

	def test_commission_plans(self):
		from thinknxg_estate.estate_crm.doctype.re_deal.re_deal import compute_commission

		self.assertEqual(compute_commission(SimpleNamespace(commission_type="Flat", flat_amount=250), 9000), 250)
		self.assertEqual(compute_commission(SimpleNamespace(commission_type="Percent", percent=2.5), 12000), 300)
		slabs = [SimpleNamespace(from_amount=0, to_amount=5000, percent=1),
		         SimpleNamespace(from_amount=5000.001, to_amount=99999, percent=2)]
		agent = SimpleNamespace(commission_type="Tiered", slabs=slabs)
		self.assertEqual(compute_commission(agent, 4000), 40)
		self.assertEqual(compute_commission(agent, 10000), 200)

	def test_lead_needs_mobile_or_email(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "RE Lead", "full_name": "Nobody"}).insert()
		lead = frappe.get_doc({"doctype": "RE Lead", "full_name": "Email Only",
		                       "email": "email.only@example.com"}).insert()
		self.assertTrue(lead.name)
