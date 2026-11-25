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
	def setUp(self):
		frappe.db.set_single_value("Property Settings", "prorate_final_rent", 1)

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

	# ---- helpers for the settlement flow
	def _term(self, lease, end=None, posting=None, charges=None, mop="Cash", reasons="End of Tenancy", **kw):
		end = end or nowdate()
		posting = posting or nowdate()
		s = lease.get_termination_settlement(tenancy_end_date=end, posting_date=posting,
		                                     charges=charges, apply_charge_to_tenant=1 if charges else 0)
		lease.terminate(tenancy_end_date=end, posting_date=posting, charges=charges,
		                apply_charge_to_tenant=1 if charges else 0, mode_of_payment=mop,
		                reasons=reasons, calc_token=s["token"], **kw)
		return s

	def _pay_first(self, lease):
		"""First installment settled outside invoicing, so only the deposit/charges matter."""
		r = _rows(lease)[0]
		frappe.db.set_value("Rent Installment", r.name, {"status": "Paid", "paid_amount": r.amount})

	def _gl(self, je):
		return frappe.get_all("GL Entry", filters={"voucher_type": "Journal Entry", "voucher_no": je, "is_cancelled": 0},
		                      fields=["account", "debit", "credit", "posting_date", "party"])

	def _balanced(self, gl):
		self.assertAlmostEqual(sum(flt(g.debit) for g in gl), sum(flt(g.credit) for g in gl), places=2)

	def _vat_default(self, lease):
		tpl = f"UAE VAT 5% - {frappe.db.get_value('Company', lease.company, 'abbr')}"
		if not frappe.db.exists("Sales Taxes and Charges Template", tpl):
			self.skipTest("no 5% VAT template on this site")
		frappe.db.set_value("Sales Taxes and Charges Template", tpl, "is_default", 1)
		return tpl

	# ---- the dates
	def test_three_dates_stay_separate(self):
		lease = self._lease("TT1", "+96890001201")
		self._pay_first(lease)
		end = add_months(nowdate(), 2)
		self._term(lease, end=end, mop="Cash")
		lease.reload()
		self.assertEqual(lease.status, "Terminated")
		self.assertEqual(getdate(lease.tenancy_end_date), getdate(end))
		self.assertEqual(getdate(lease.end_date), getdate(add_months(nowdate(), 12)))  # schedule end untouched
		self.assertEqual(getdate(lease.termination_posting_date), getdate(nowdate()))

	def test_token_required_and_stale_calculation_refused(self):
		lease = self._lease("TT2", "+96890001202")
		self._pay_first(lease)
		s = lease.get_termination_settlement(tenancy_end_date=nowdate(), posting_date=nowdate())
		with self.assertRaises(frappe.ValidationError):
			lease.terminate(tenancy_end_date=nowdate(), posting_date=nowdate(), mode_of_payment="Cash")  # no token
		# inputs changed after calculating: charges added
		with self.assertRaises(frappe.ValidationError):
			lease.terminate(tenancy_end_date=nowdate(), posting_date=nowdate(), mode_of_payment="Cash",
			                apply_charge_to_tenant=1, charges=[{"description": "Paint", "amount": 10}],
			                calc_token=s["token"])
		self.assertEqual(frappe.db.get_value("Lease Contract", lease.name, "status"), "Active")

	def test_posting_date_is_mandatory(self):
		lease = self._lease("TT3", "+96890001203")
		with self.assertRaises(frappe.ValidationError):
			lease.terminate(tenancy_end_date=nowdate(), calc_token="x", mode_of_payment="Cash")

	# ---- scenarios
	def test_early_termination_deposit_refund_with_charges_payable(self):
		"""Deposit 100, no rent due, charges 30 -> 70 payable to the tenant."""
		lease = self._lease("TT4", "+96890001204")
		self._pay_first(lease)
		charges = [{"description": "Cleaning", "amount": 30, "vat_applicable": 0}]
		s = self._term(lease, charges=charges)
		self.assertEqual(s["result"], ls.PAYABLE)
		self.assertAlmostEqual(s["net_settlement"], 70, places=2)
		lease.reload()
		self.assertEqual(lease.termination_settlement_status, ls.PAYABLE)
		self.assertTrue(lease.termination_journal_entry and lease.termination_charge_invoice)
		gl = self._gl(lease.termination_journal_entry)
		self._balanced(gl)
		cash = frappe.db.get_value("Mode of Payment Account", {"parent": "Cash", "company": lease.company}, "default_account")
		self.assertAlmostEqual(sum(flt(g.credit) for g in gl if g.account == cash), 70, places=2)
		self.assertAlmostEqual(sum(flt(g.debit) for g in gl if g.account.startswith("Tenant Security Deposits")), 100, places=2)
		self.assertAlmostEqual(flt(frappe.db.get_value("Sales Invoice", lease.termination_charge_invoice, "outstanding_amount")), 0, places=2)
		dep = frappe.db.get_value("Security Deposit", lease.security_deposit, ["status", "deduction_amount", "refunded_amount"], as_dict=True)
		self.assertEqual((flt(dep.deduction_amount), flt(dep.refunded_amount)), (30, 70))
		self.assertEqual(ls.deposit_balance(lease.security_deposit), 0)

	def test_rent_exceeds_deposit_is_receivable(self):
		frappe.db.set_single_value("Property Settings", "prorate_final_rent", 0)
		lease = self._lease("TT5", "+96890001205")
		s = lease.get_termination_settlement(tenancy_end_date=nowdate(), posting_date=nowdate())
		self.assertEqual(s["result"], ls.RECEIVABLE)
		self.assertLess(s["net_settlement"], 0)
		lease.terminate(tenancy_end_date=nowdate(), posting_date=nowdate(), mode_of_payment="Cash",
		                calc_token=s["token"], reasons="Tenancy Breach")
		lease.reload()
		gl = self._gl(lease.termination_journal_entry)
		self._balanced(gl)
		cash = frappe.db.get_value("Mode of Payment Account", {"parent": "Cash", "company": lease.company}, "default_account")
		self.assertAlmostEqual(sum(flt(g.debit) for g in gl if g.account == cash), -s["net_settlement"], places=2)
		inv = frappe.db.get_value("Rent Installment", _rows(lease)[0].name, "sales_invoice")
		self.assertTrue(inv)
		self.assertAlmostEqual(flt(frappe.db.get_value("Sales Invoice", inv, "outstanding_amount")), 0, places=2)

	def test_final_period_is_prorated_with_a_credit_note(self):
		lease = self._lease("TT6", "+96890001206")
		end = add_months(nowdate(), 1)  # inside the first quarterly period
		s = lease.get_termination_settlement(tenancy_end_date=end, posting_date=nowdate())
		adj = [a for a in s["adjustments"] if a["kind"] == "prorata"]
		self.assertEqual(len(adj), 1)
		a = adj[0]
		self.assertAlmostEqual(a["credit_net"] + 300.0 * (a["period_days"] - a["unused_days"]) / a["period_days"], 300.0, delta=0.02)
		self.assertGreater(a["unused_days"], 0)
		lease.terminate(tenancy_end_date=end, posting_date=nowdate(), mode_of_payment="Cash", calc_token=s["token"])
		cns = frappe.get_all("Sales Invoice", filters={"is_return": 1, "return_against": a["sales_invoice"] or "x"}) if a["sales_invoice"] else []
		lease.reload()
		posted = json.loads(lease.termination_settlement)["posted"]
		self.assertEqual(len(posted["credit_notes"]), 1)
		cn = frappe.db.get_value("Sales Invoice", posted["credit_notes"][0], ["docstatus", "grand_total"], as_dict=True)
		self.assertEqual(cn.docstatus, 1)
		self.assertAlmostEqual(-flt(cn.grand_total), a["credit_gross"], delta=1.0)

	def test_vat_applicable_and_not_applicable(self):
		lease = self._lease("TT7", "+96890001207")
		self._pay_first(lease)
		self._vat_default(lease)
		cfg = ls.vat_config(lease)
		charges = [{"description": "Repair", "amount": 100, "vat_applicable": 1},
		           {"description": "Key", "amount": 20, "vat_applicable": 0}]
		s = lease.get_termination_settlement(tenancy_end_date=nowdate(), posting_date=nowdate(),
		                                     charges=charges, apply_charge_to_tenant=1)
		self.assertAlmostEqual(s["charges_vat"], 100 * cfg["rate"] / 100, places=2)
		self.assertAlmostEqual(s["charges_total"], 120 + s["charges_vat"], places=2)
		self.assertEqual([c["vat_amount"] for c in s["charges"]][1], 0)
		lease.terminate(tenancy_end_date=nowdate(), posting_date=nowdate(), mode_of_payment="Cash",
		                charges=charges, apply_charge_to_tenant=1, calc_token=s["token"])
		lease.reload()
		si = frappe.get_doc("Sales Invoice", lease.termination_charge_invoice)
		self.assertAlmostEqual(flt(si.total_taxes_and_charges), s["charges_vat"], places=2)
		self.assertAlmostEqual(flt(si.grand_total), s["charges_total"], places=2)
		vat_gl = frappe.get_all("GL Entry", filters={"voucher_no": si.name, "account": cfg["account_head"], "is_cancelled": 0},
		                        fields=["credit"])
		self.assertAlmostEqual(sum(flt(g.credit) for g in vat_gl), s["charges_vat"], places=2)

	def test_vat_without_configuration_is_refused(self):
		lease = self._lease("TT8", "+96890001208")
		with self.assertRaises(frappe.ValidationError):
			ls.normalise_charges(frappe._dict(company="No Such Company", tenant=lease.tenant, name=lease.name),
			                     [{"description": "X", "amount": 5, "vat_applicable": 1}], 1)

	def test_charge_validation(self):
		lease = self._lease("TT9", "+96890001209")
		for bad in ([{"description": "", "amount": 5}], [{"description": "A", "amount": -1}],
		            [{"description": "A", "amount": 5}, {"description": "a", "amount": 5}]):
			with self.assertRaises(frappe.ValidationError):
				ls.normalise_charges(lease, bad, 1)
		self.assertEqual(ls.normalise_charges(lease, [{"description": "A", "amount": 5}], 0)["total"], 0)

	def test_zero_settlement_creates_no_cash_entry(self):
		lease = self._lease("TT10", "+96890001210")
		self._pay_first(lease)
		frappe.db.set_value("Security Deposit", lease.security_deposit, "deduction_amount", 100)
		s = lease.get_termination_settlement(tenancy_end_date=nowdate(), posting_date=nowdate())
		self.assertEqual(s["result"], ls.SETTLED)
		lease.terminate(tenancy_end_date=nowdate(), posting_date=nowdate(), calc_token=s["token"])  # no Mode of Payment
		lease.reload()
		self.assertEqual(lease.termination_settlement_status, ls.SETTLED)
		self.assertFalse(lease.termination_journal_entry)

	def test_no_security_deposit(self):
		lease = self._lease("TT11", "+96890001211")
		self._pay_first(lease)
		lease.db_set("security_deposit", None)
		charges = [{"description": "Cleaning", "amount": 40}]
		s = lease.get_termination_settlement(tenancy_end_date=nowdate(), posting_date=nowdate(),
		                                     charges=charges, apply_charge_to_tenant=1)
		self.assertEqual(s["deposit_balance"], 0)
		self.assertEqual(s["result"], ls.RECEIVABLE)
		with self.assertRaises(frappe.ValidationError):  # cash moves, so a Mode of Payment is required
			lease.terminate(tenancy_end_date=nowdate(), posting_date=nowdate(), charges=charges,
			                apply_charge_to_tenant=1, calc_token=s["token"])
		lease.terminate(tenancy_end_date=nowdate(), posting_date=nowdate(), charges=charges,
		                apply_charge_to_tenant=1, calc_token=s["token"], mode_of_payment="Cash")
		self._balanced(self._gl(lease.reload().termination_journal_entry))

	def test_different_posting_date(self):
		lease = self._lease("TT12", "+96890001212")
		self._pay_first(lease)
		posting = frappe.utils.add_days(nowdate(), -5)
		self._term(lease, posting=posting, charges=[{"description": "Cleaning", "amount": 10}])
		lease.reload()
		self.assertEqual(getdate(lease.tenancy_end_date), getdate(nowdate()))
		self.assertEqual(getdate(lease.termination_posting_date), getdate(posting))
		self.assertEqual({getdate(g.posting_date) for g in self._gl(lease.termination_journal_entry)}, {getdate(posting)})

	def test_posting_date_outside_fiscal_year_refused(self):
		lease = self._lease("TT13", "+96890001213")
		with self.assertRaises(Exception):
			ls.validate_posting_date(lease.company, "1990-01-01")

	def test_duplicate_submission_is_refused(self):
		lease = self._lease("TT14", "+96890001214")
		self._pay_first(lease)
		s = self._term(lease)
		with self.assertRaises(frappe.ValidationError):
			lease.terminate(tenancy_end_date=nowdate(), posting_date=nowdate(), mode_of_payment="Cash",
			                calc_token=s["token"])
		self.assertEqual(frappe.db.count("Journal Entry", {"user_remark": ["like", f"%{lease.name}%"], "docstatus": 1}), 1)

	def test_failed_accounting_leaves_no_partial_termination(self):
		from unittest.mock import patch

		lease = self._lease("TT15", "+96890001215")
		self._pay_first(lease)
		charges = [{"description": "Cleaning", "amount": 10}]
		s = lease.get_termination_settlement(tenancy_end_date=nowdate(), posting_date=nowdate(),
		                                     charges=charges, apply_charge_to_tenant=1)
		with patch("thinknxg_estate.core.security_deposit_accounting._get_liability_account",
		           side_effect=frappe.ValidationError("boom")):
			with self.assertRaises(frappe.ValidationError):
				lease.terminate(tenancy_end_date=nowdate(), posting_date=nowdate(), charges=charges,
				                apply_charge_to_tenant=1, mode_of_payment="Cash", calc_token=s["token"])
		self.assertEqual(frappe.db.get_value("Lease Contract", lease.name, "status"), "Active")
		self.assertFalse(frappe.db.exists("Sales Invoice", {"remarks": ["like", f"%{lease.name}%"], "docstatus": 1,
		                                                    "is_return": 0, "grand_total": 10}))
		self.assertEqual(ls.deposit_balance(lease.security_deposit), 100)

	def test_historical_terminated_lease_is_untouched(self):
		lease = self._lease("TT16", "+96890001216")
		lease.db_set("status", "Terminated")
		before = frappe.db.get_value("Lease Contract", lease.name, ["tenancy_end_date", "termination_settlement", "end_date"])
		with self.assertRaises(frappe.ValidationError):
			lease.terminate(tenancy_end_date=nowdate(), posting_date=nowdate(), calc_token="x")
		with self.assertRaises(frappe.ValidationError):
			lease.reverse_termination(reason="x")  # nothing was posted for it
		self.assertEqual(frappe.db.get_value("Lease Contract", lease.name, ["tenancy_end_date", "termination_settlement", "end_date"]), before)

	def test_rent_invoiced_beyond_end_date_is_credited_automatically(self):
		lease = self._lease("TT17", "+96890001217")
		self._pay_first(lease)
		rows = _rows(lease)
		late = rows[2]
		invoice = self._invoice(lease, late)
		end = add_months(nowdate(), 4)
		posting = nowdate()
		s = self._term(lease, end=end, posting=posting)
		self.assertEqual([a["sales_invoice"] for a in s["advance_invoices"]], [invoice])
		lease.reload()
		cn = frappe.get_all("Sales Invoice", filters={"return_against": invoice, "docstatus": 1},
		                    fields=["name", "posting_date", "grand_total", "is_return"])
		self.assertEqual(len(cn), 1)
		self.assertEqual(getdate(cn[0].posting_date), getdate(posting))
		self.assertAlmostEqual(flt(cn[0].grand_total), -flt(frappe.db.get_value("Sales Invoice", invoice, "grand_total")), places=2)
		self.assertEqual(frappe.db.get_value("Rent Installment", late.name, "status"), "Cancelled")
		self.assertIn(cn[0].name, json.loads(lease.termination_settlement)["posted"]["credit_notes"])  # plus the pro-rata credit for the final period

	def test_reversal_restores_the_lease_and_cancels_entries(self):
		lease = self._lease("TT18", "+96890001218")
		self._pay_first(lease)
		self._term(lease, charges=[{"description": "Cleaning", "amount": 30}])
		lease.reload()
		je, inv = lease.termination_journal_entry, lease.termination_charge_invoice
		lease.reverse_termination(reason="Entered in error")
		lease.reload()
		self.assertEqual(lease.status, "Active")
		self.assertFalse(lease.termination_journal_entry)
		self.assertEqual(frappe.db.get_value("Journal Entry", je, "docstatus"), 2)
		self.assertEqual(frappe.db.get_value("Sales Invoice", inv, "docstatus"), 2)
		self.assertEqual(ls.deposit_balance(lease.security_deposit), 100)
		self.assertEqual(frappe.db.get_value("Unit", lease.unit, "current_lease"), lease.name)

	def test_outstanding_counts_invoiced_and_partially_paid_balances(self):
		lease = self._lease("TT19", "+96890001219")
		rows = _rows(lease)
		si = self._invoice(lease, rows[0])
		frappe.db.set_value("Sales Invoice", si, "outstanding_amount", 120)  # partly paid
		end = add_months(nowdate(), 4)
		inv2 = self._invoice(lease, rows[1])
		frappe.db.set_single_value("Property Settings", "prorate_final_rent", 0)
		self.assertAlmostEqual(lease.get_outstanding_rent(end),
		                       120 + flt(frappe.db.get_value("Sales Invoice", inv2, "outstanding_amount")), places=2)

	def test_settlement_uses_deposit_balance_not_original_amount(self):
		lease = self._lease("TT20", "+96890001220")
		frappe.db.set_value("Security Deposit", lease.security_deposit, "deduction_amount", 30)
		st = ls.compute_settlement(lease, nowdate())
		self.assertEqual(st["deposit_amount"], 100)
		self.assertEqual(st["deposit_balance"], 70)
		self.assertAlmostEqual(st["net_settlement"], 70 - st["rent_outstanding"], places=3)

	def test_deposit_refund_pays_out_the_balance_only(self):
		lease = self._lease("TT21", "+96890001221")
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
