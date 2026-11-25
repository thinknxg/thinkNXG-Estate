"""Lease termination: Schedule End Date / Tenancy End Date / Posting Date, settlement maths,
credit notes for rent invoiced beyond the Tenancy End Date, and the deposit balance.

bench --site SITE run-tests --app thinknxg_estate --module thinknxg_estate.tests.test_lease_termination_settlement
"""

import json

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_months, flt, getdate, nowdate

from thinknxg_estate.core import lease_settlement as ls
from thinknxg_estate.tests.test_estate_integration import make_lease, make_tenant, make_unit


def _rows(lease):
	return frappe.get_all("Rent Installment", filters={"parent": lease.rent_schedule},
	                      fields=["name", "installment_no", "due_date", "amount", "status", "sales_invoice"],
	                      order_by="installment_no asc")


class TestLeaseTerminationSettlement(IntegrationTestCase):
	def _lease(self, tag, mobile, **kw):
		_, _, unit = make_unit(tag)
		tenant = make_tenant(tag, mobile)
		lease = make_lease(tenant, unit, rent=1200, deposit=100, **kw)
		lease.reload()
		# the test company may not trade in the site's default currency
		company = frappe.db.get_value("Company", lease.company, ["default_currency", "default_receivable_account"], as_dict=True)
		customer = frappe.db.get_value("Tenant", tenant.name, "customer")
		if customer:
			frappe.db.set_value("Customer", customer, "default_currency", company.default_currency)
		self._hold_deposit(lease)
		self._price_list_in(customer, company.default_currency)
		return lease

	def _price_list_in(self, customer, currency):
		"""Invoice in the company's currency: the default selling list may be in another one."""
		pl = frappe.db.get_value("Price List", {"currency": currency, "selling": 1, "enabled": 1}, "name")
		if pl:
			frappe.db.set_single_value("Selling Settings", "selling_price_list", pl)  # rolled back with the test
		if customer and pl:
			frappe.db.set_value("Customer", customer, "default_price_list", pl)

	def _hold_deposit(self, lease):
		"""A deposit only counts as held once it has been received (submitted)."""
		# Marked held directly: the submit hook needs the deposit ledger accounts, which
		# are not what is under test here.
		frappe.db.set_value("Security Deposit", lease.security_deposit, {"docstatus": 1, "status": "Held"})

	def _invoice(self, lease, row):
		"""Raise the advance rent invoice the scheduler would raise, in the company's currency."""
		from thinknxg_estate.core.install import ensure_rent_item

		item = frappe.db.get_single_value("Property Settings", "rent_item") or ensure_rent_item()
		company = frappe.db.get_value("Company", lease.company, ["default_currency"], as_dict=True)
		pl = frappe.db.get_value("Price List", {"currency": company.default_currency, "selling": 1, "enabled": 1})
		si = frappe.get_doc({
			"doctype": "Sales Invoice", "company": lease.company,
			"customer": frappe.db.get_value("Tenant", lease.tenant, "customer"),
			"currency": company.default_currency, "conversion_rate": 1,
			"selling_price_list": pl, "price_list_currency": company.default_currency, "plc_conversion_rate": 1,
			"due_date": row.due_date,
			"items": [{"item_code": item, "qty": 1, "rate": flt(row.amount)}],
		}).insert(ignore_permissions=True)
		si.submit()
		frappe.db.set_value("Rent Installment", row.name, {"sales_invoice": si.name, "status": "Invoiced"})
		return si.name

	def test_three_dates_stay_separate(self):
		lease = self._lease("TS1", "+96890001101")
		end = add_months(nowdate(), 2)
		lease.terminate(tenancy_end_date=end, outstanding_rent=ls.compute_settlement(lease, end)["rent_outstanding"])
		lease.reload()
		self.assertEqual(lease.status, "Terminated")
		self.assertEqual(getdate(lease.tenancy_end_date), getdate(end))
		self.assertEqual(getdate(lease.end_date), getdate(add_months(nowdate(), 12)))  # schedule end untouched
		self.assertIsNone(lease.termination_posting_date)  # no ledger entry, no posting date invented

	def test_legacy_termination_date_is_the_tenancy_end_date(self):
		lease = self._lease("TS2", "+96890001102")
		lease.terminate(termination_date=nowdate(), outstanding_rent=ls.compute_settlement(lease, nowdate())["rent_outstanding"])
		self.assertEqual(getdate(lease.reload().tenancy_end_date), getdate(nowdate()))

	def test_outstanding_counts_invoiced_and_partially_paid_balances(self):
		lease = self._lease("TS3", "+96890001103")
		rows = _rows(lease)
		frappe.db.set_value("Rent Installment", rows[0].name, "status", "Invoiced")
		frappe.db.set_value("Rent Installment", rows[1].name,
		                    {"status": "Partially Paid", "paid_amount": 100, "outstanding_amount": 200})
		end = add_months(nowdate(), 4)  # installments 1 and 2 fall due before this
		due = [r for r in rows if getdate(r.due_date) <= getdate(end)]
		self.assertEqual(len(due), 2)
		self.assertAlmostEqual(lease.get_outstanding_rent(end), 300 + 200, places=3)

	def test_wrong_outstanding_is_rejected(self):
		lease = self._lease("TS4", "+96890001104")
		with self.assertRaises(frappe.ValidationError):
			lease.terminate(tenancy_end_date=nowdate(), outstanding_rent=1)

	def test_rent_invoiced_beyond_end_date_needs_credit_note(self):
		lease = self._lease("TS5", "+96890001105")
		rows = _rows(lease)
		late = rows[2]  # due ~6 months out
		invoice = self._invoice(lease, late)
		self.assertTrue(invoice)
		end = add_months(nowdate(), 4)
		st = ls.compute_settlement(lease, end)
		self.assertEqual([a["sales_invoice"] for a in st["advance_invoices"]], [invoice])
		out = st["rent_outstanding"]

		# 1. never silently reduced: terminating without credit notes is refused and changes nothing
		with self.assertRaises(frappe.ValidationError):
			lease.terminate(tenancy_end_date=end, outstanding_rent=out)
		self.assertEqual(frappe.db.get_value("Lease Contract", lease.name, "status"), "Active")
		# 2. credit notes need an explicit Posting Date
		with self.assertRaises(frappe.ValidationError):
			lease.terminate(tenancy_end_date=end, outstanding_rent=out, issue_credit_notes=1)

		# 3. with consent and a Posting Date the original invoice is reversed on that date
		posting = nowdate()
		lease.terminate(tenancy_end_date=end, outstanding_rent=out, issue_credit_notes=1, posting_date=posting)
		lease.reload()
		self.assertEqual(lease.status, "Terminated")
		self.assertEqual(getdate(lease.termination_posting_date), getdate(posting))
		cn = frappe.get_all("Sales Invoice", filters={"return_against": invoice, "docstatus": 1},
		                    fields=["name", "posting_date", "grand_total", "is_return"])
		self.assertEqual(len(cn), 1)
		self.assertTrue(cn[0].is_return)
		self.assertEqual(getdate(cn[0].posting_date), getdate(posting))
		original = frappe.db.get_value("Sales Invoice", invoice, "grand_total")
		self.assertAlmostEqual(flt(cn[0].grand_total), -flt(original), places=2)
		self.assertEqual(frappe.db.get_value("Rent Installment", late.name, "status"), "Cancelled")
		gl = frappe.get_all("GL Entry", filters={"voucher_type": "Sales Invoice", "voucher_no": cn[0].name, "is_cancelled": 0},
		                    fields=["posting_date", "debit", "credit"])
		self.assertTrue(gl)
		self.assertEqual({getdate(g.posting_date) for g in gl}, {getdate(posting)})
		self.assertAlmostEqual(sum(flt(g.debit) for g in gl), sum(flt(g.credit) for g in gl), places=2)
		snap = json.loads(lease.termination_settlement)
		self.assertEqual(snap["credit_notes"], [cn[0].name])

	def test_settlement_uses_deposit_balance_not_original_amount(self):
		lease = self._lease("TS6", "+96890001106")
		frappe.db.set_value("Security Deposit", lease.security_deposit, "deduction_amount", 30)
		st = ls.compute_settlement(lease, nowdate())
		self.assertEqual(st["deposit_amount"], 100)
		self.assertEqual(st["deposit_balance"], 70)
		self.assertAlmostEqual(st["net_settlement"], 70 - st["rent_outstanding"], places=3)

	def test_deposit_refund_pays_out_the_balance_only(self):
		lease = self._lease("TS7", "+96890001107")
		dep = frappe.get_doc("Security Deposit", lease.security_deposit)
		frappe.db.set_value("Security Deposit", dep.name, "deduction_amount", 30)
		dep.reload()
		with self.assertRaises(frappe.ValidationError):
			dep.refund(deduction_amount=80, posting_date=nowdate())  # more than the 70 still held
		dep.refund(deduction_amount=10, deduction_reason="Wall repair", posting_date=nowdate())
		dep.reload()
		self.assertEqual(flt(dep.deduction_amount), 40)
		self.assertEqual(flt(dep.refunded_amount), 60)
		self.assertEqual(ls.deposit_balance(dep.name), 0)
