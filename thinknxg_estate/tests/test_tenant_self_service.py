"""Tests for the /tenant-self-service API: identity, ownership and financial integrity.

Uses the demo dataset (thinknxg_estate.demo) when it is installed and skips otherwise.

bench --site SITE run-tests --app thinknxg_estate --module thinknxg_estate.tests.test_tenant_self_service
"""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt

from thinknxg_estate.core import tenant_self_service as tss

API = "thinknxg_estate.core.tenant_self_service._tenant"


def _tenants_with_invoices(limit=2):
	"""Tenants that own at least one submitted rent invoice, plus that invoice."""
	found = []
	for name in frappe.get_all("Tenant", filters={"disabled": 0}, pluck="name", limit=60):
		for lease in tss._leases(name):
			for inst in tss._installments(lease):
				if inst.sales_invoice and frappe.db.get_value("Sales Invoice", inst.sales_invoice, "docstatus") == 1:
					found.append((name, inst.sales_invoice, lease.name))
					break
			else:
				continue
			break
		if len(found) >= limit:
			break
	return found


class TestTenantSelfService(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.pair = _tenants_with_invoices()

	def setUp(self):
		if len(self.pair) < 2:
			self.skipTest("demo dataset not installed")
		self.a, self.b = self.pair[0], self.pair[1]

	# --- identity ---------------------------------------------------------------------
	def test_guest_is_rejected(self):
		frappe.set_user("Guest")
		try:
			with patch("frappe.get_request_header", return_value=None), self.assertRaises(frappe.AuthenticationError):
				tss.overview()
		finally:
			frappe.set_user("Administrator")

	# --- ownership --------------------------------------------------------------------
	def test_invoice_ownership(self):
		self.assertTrue(tss._own_invoice(self.a[0], self.a[1]))
		self.assertFalse(tss._own_invoice(self.a[0], self.b[1]))
		self.assertFalse(tss._own_invoice(self.b[0], self.a[1]))

	def test_foreign_lease_parameter_is_denied(self):
		with patch(API, return_value=self.a[0]):
			with self.assertRaises(frappe.PermissionError):
				tss.overview(lease=self.b[2])
			with self.assertRaises(frappe.PermissionError):
				tss.payments(lease=self.b[2])

	def test_download_rejects_foreign_records(self):
		with patch(API, return_value=self.a[0]):
			for kind, ref in (("invoice", self.b[1]), ("receipt", self.b[1]), ("file", "/etc/passwd"),
			                  ("file", "/private/files/../../sites/common_site_config.json"),
			                  ("bogus", "x")):
				with self.assertRaises(frappe.PermissionError, msg=f"{kind}:{ref}"):
					tss.download(kind, ref)

	def test_files_allow_list_excludes_other_tenants(self):
		mine, theirs = tss._own_files(self.a[0]), tss._own_files(self.b[0])
		self.assertFalse({u for u in mine & theirs if u.startswith("/private")})

	def test_service_request_isolation(self):
		with patch(API, return_value=self.b[0]):
			name = tss.create_service_request("Parking Request", "Extra bay", "Please")["name"]
		try:
			with patch(API, return_value=self.a[0]):
				with self.assertRaises(frappe.PermissionError):
					tss.reply_service_request(name, "hello")
				with self.assertRaises(frappe.PermissionError):
					tss.cancel_service_request(name)
			self.assertEqual(frappe.db.get_value("Tenant Service Request", name, "tenant"), self.b[0])
		finally:
			frappe.delete_doc("Tenant Service Request", name, force=True)

	# --- financial integrity ----------------------------------------------------------
	def test_summary_adds_up(self):
		with patch(API, return_value=self.a[0]):
			pay = tss.payments()
		sm = pay["summary"]
		live = [i for i in pay["installments"] if i["status"] != "Cancelled"]
		self.assertAlmostEqual(flt(sm["paid"]), sum(flt(i["paid_amount"]) for i in live), places=2)
		self.assertAlmostEqual(flt(sm["total"]), sum(flt(i["amount"]) for i in live), places=2)
		self.assertGreaterEqual(flt(sm["outstanding_due"]), flt(sm["overdue"]))

	def test_no_client_side_payment_endpoint(self):
		for fn in ("mark_paid", "pay", "confirm_payment", "mark_invoice_paid"):
			self.assertFalse(hasattr(tss, fn), fn)
