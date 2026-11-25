"""Final settlement and accounting for lease termination.

Three dates are kept apart on purpose:

* Schedule End Date - the contractual end (``Lease Contract.end_date``). Never changed here.
* Tenancy End Date  - the actual end; decides which rent is owed and which is not.
* Posting Date      - the date the settlement entries enter the General Ledger.

Source of truth is the ledger documents themselves, never installment totals:

* rent owed        = outstanding amount of the live Sales Invoices (VAT included, net of
                     payments, allocations and credit notes). Installments due on/before the
                     Tenancy End Date that were not invoiced yet are invoiced first.
* rent not owed    = invoices for periods after the Tenancy End Date are reversed with credit
                     notes; the part of the final period after the end date is credited pro rata
                     (Property Settings > Prorate Final Rent on Termination).
* tenant charges   = one Sales Invoice (VAT from the company's Sales Taxes template).
* deposit          = the balance actually still held on the Security Deposit.

The settlement Journal Entry then moves the deposit liability against those receivables, and the
remaining difference goes through the Mode of Payment account. Nothing already submitted is
edited; every correction is a credit note or a new entry.

    net = deposit balance + rent paid for periods not used - rent outstanding - charges (incl. VAT)
    net > 0  Payable to Tenant     net < 0  Receivable from Tenant     net == 0  Settled
"""

import hashlib
import json

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, get_datetime, getdate, now_datetime

CLOSED = ("Paid", "Cancelled")
PAYABLE, RECEIVABLE, SETTLED = "Payable to Tenant", "Receivable from Tenant", "Settled"
MAX_CHARGES = 25
TOL = 0.011


# --------------------------------------------------------------------------- helpers

def deposit_balance(deposit_name):
	"""Deposit still held: original amount less deductions and refunds already booked."""
	if not deposit_name:
		return 0.0
	d = frappe.db.get_value(
		"Security Deposit", deposit_name,
		["amount", "deduction_amount", "refunded_amount", "docstatus"], as_dict=True,
	)
	if not d or d.docstatus != 1:
		return 0.0
	return max(flt(d.amount) - flt(d.deduction_amount) - flt(d.refunded_amount), 0.0)


def _live_invoice(name):
	"""Submitted, not-cancelled, not-a-return Sales Invoice, else None."""
	if not name:
		return None
	si = frappe.db.get_value(
		"Sales Invoice", name,
		["name", "docstatus", "is_return", "grand_total", "outstanding_amount", "currency",
		 "debit_to", "customer"], as_dict=True,
	)
	if not si or si.docstatus != 1 or si.is_return:
		return None
	return si


def _ledger_outstanding(invoice):
	"""Outstanding of an invoice from the Payment Ledger (payments, JEs and credit notes all count)."""
	return flt(frappe.db.sql(
		"""select coalesce(sum(amount), 0) from `tabPayment Ledger Entry`
		   where against_voucher_type = 'Sales Invoice' and against_voucher_no = %s and delinked = 0""",
		invoice)[0][0], 3)


def _customer(lease):
	customer = frappe.db.get_value("Tenant", lease.tenant, "customer")
	if not customer:
		frappe.throw(_("Tenant {0} has no linked Customer, so no accounting entries can be posted.").format(lease.tenant))
	return customer


def vat_config(lease):
	"""VAT template/account/rate from the ERPNext tax configuration (never hardcoded).

	The company's default Sales Taxes template is used; failing that, the template of the
	tenant's latest rent invoice - the same convention the rent invoices follow.
	Returns None when nothing is configured.
	"""
	template = frappe.db.get_value(
		"Sales Taxes and Charges Template",
		{"company": lease.company, "is_default": 1, "disabled": 0}, "name")
	if not template:
		customer = frappe.db.get_value("Tenant", lease.tenant, "customer")
		template = frappe.db.get_value(
			"Sales Invoice",
			{"customer": customer, "company": lease.company, "docstatus": 1, "is_return": 0,
			 "taxes_and_charges": ["is", "set"]},
			"taxes_and_charges", order_by="posting_date desc, creation desc")
	if not template:
		return None
	rows = frappe.get_all(
		"Sales Taxes and Charges", filters={"parent": template, "parenttype": "Sales Taxes and Charges Template"},
		fields=["account_head", "rate", "charge_type"], order_by="idx asc", limit=1)
	if not rows or not flt(rows[0].rate):
		return None
	return {"template": template, "account_head": rows[0].account_head, "rate": flt(rows[0].rate)}


def normalise_charges(lease, charges, apply_charge):
	"""Validate the charge table and add VAT. Amounts are VAT-exclusive, like the rent rate."""
	if isinstance(charges, str):
		charges = json.loads(charges or "[]")
	if not cint(apply_charge):
		return {"rows": [], "net": 0.0, "vat": 0.0, "total": 0.0, "vat_rate": 0.0, "vat_template": None}
	charges = charges or []
	if len(charges) > MAX_CHARGES:
		frappe.throw(_("A maximum of {0} charge lines is allowed.").format(MAX_CHARGES))
	vat = None
	rows, seen = [], set()
	for i, c in enumerate(charges, 1):
		desc = (c.get("description") or "").strip()
		amount = flt(c.get("amount"), 3)
		if not desc:
			frappe.throw(_("Charge line {0}: Charge Description is required.").format(i))
		if amount <= 0:
			frappe.throw(_("Charge line {0}: Amount must be greater than zero.").format(i))
		key = (desc.lower(), amount)
		if key in seen:
			frappe.throw(_("Charge line {0}: duplicate of an earlier line ({1}, {2}).").format(i, desc, amount))
		seen.add(key)
		applicable = cint(c.get("vat_applicable"))
		rate = vat_amount = 0.0
		if applicable:
			if vat is None:
				vat = vat_config(lease) or False
			if not vat:
				frappe.throw(_("Charge line {0}: VAT is applicable but no VAT rate is configured for company {1} "
				               "(set a default Sales Taxes and Charges Template).").format(i, lease.company))
			rate = vat["rate"]
			vat_amount = flt(amount * rate / 100.0, 3)
		rows.append({"description": desc, "amount": amount, "vat_applicable": applicable,
		             "vat_rate": rate, "vat_amount": vat_amount, "total": flt(amount + vat_amount, 3)})
	net = flt(sum(r["amount"] for r in rows), 3)
	vat_total = flt(sum(r["vat_amount"] for r in rows), 3)
	return {"rows": rows, "net": net, "vat": vat_total, "total": flt(net + vat_total, 3),
	        "vat_rate": (vat or {}).get("rate", 0.0), "vat_template": (vat or {}).get("template") if vat else None}


def validate_posting_date(company, posting_date):
	"""Fiscal year must exist, the books must not be frozen/closed for that date."""
	from erpnext.accounts.utils import get_fiscal_year

	if not posting_date:
		frappe.throw(_("Posting Date is required."))
	pd = getdate(posting_date)
	get_fiscal_year(pd, company=company)  # throws when no fiscal year covers the date
	frozen = frappe.db.get_value("Company", company, ["accounts_frozen_till_date", "role_allowed_for_frozen_entries"], as_dict=True)
	if frozen and frozen.accounts_frozen_till_date and pd <= getdate(frozen.accounts_frozen_till_date):
		if not frozen.role_allowed_for_frozen_entries or frozen.role_allowed_for_frozen_entries not in frappe.get_roles():
			frappe.throw(_("Accounts are frozen up to {0}; Posting Date {1} is not allowed.")
			             .format(frozen.accounts_frozen_till_date, pd))
	for period in frappe.get_all("Accounting Period", filters={"company": company, "disabled": 0,
	                                                           "start_date": ["<=", pd], "end_date": [">=", pd]},
	                             pluck="name"):
		closed = frappe.get_all("Closed Document", filters={"parent": period, "closed": 1,
		                        "document_type": ["in", ["Journal Entry", "Sales Invoice"]]}, pluck="document_type")
		if closed:
			frappe.throw(_("Accounting Period {0} is closed for {1}; Posting Date {2} is not allowed.")
			             .format(period, ", ".join(closed), pd))
	return pd


def payment_account(mode_of_payment, company):
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account

	if not mode_of_payment:
		frappe.throw(_("Mode of Payment is required."))
	if not frappe.db.exists("Mode of Payment", mode_of_payment):
		frappe.throw(_("Mode of Payment {0} does not exist.").format(mode_of_payment))
	acc = (get_bank_cash_account(mode_of_payment, company) or {}).get("account")
	if not acc:
		frappe.throw(_("Mode of Payment {0} has no account configured for company {1}.")
		             .format(mode_of_payment, company))
	a = frappe.db.get_value("Account", acc, ["company", "disabled", "is_group", "account_type"], as_dict=True)
	if a.company != company or a.disabled or a.is_group:
		frappe.throw(_("Account {0} of Mode of Payment {1} cannot be used for company {2}.")
		             .format(acc, mode_of_payment, company))
	return acc


def _rounded(x):
	"""Invoices post the rounded total unless rounding is disabled in Global Defaults."""
	return flt(x, 2) if frappe.db.get_single_value("Global Defaults", "disable_rounded_total") else flt(x, 0)


def _simulate_gross(lease, row, settings):
	"""Grand total the installment invoice will have (same builder as the scheduler)."""
	from thinknxg_estate.core import tasks

	try:
		si = tasks._rent_invoice_doc(frappe._dict(row), lease, settings)
		si.set_missing_values()
		si.calculate_taxes_and_totals()
		if flt(si.grand_total):
			return _rounded(si.grand_total)
	except Exception:
		pass
	return flt(row["amount"], 3)


# --------------------------------------------------------------------------- calculation

def compute_settlement(lease, tenancy_end_date, posting_date=None, charges=None, apply_charge=False):
	"""Authoritative settlement figures (preview and execution use the same function)."""
	end = getdate(tenancy_end_date)
	settings = frappe.get_single("Property Settings")
	currency = frappe.db.get_value("Company", lease.company, "default_currency")
	ch = normalise_charges(lease, charges, apply_charge)
	out = {
		"tenancy_end_date": str(end),
		"schedule_end_date": str(getdate(lease.end_date)),
		"posting_date": str(getdate(posting_date)) if posting_date else None,
		"currency": currency,
		"rent_outstanding": 0.0,
		"outstanding_installments": [],
		"advance_invoices": [],
		"adjustments": [],
		"credit_note_total": 0.0,
		"paid_after_end": 0.0,
		"deposit_amount": flt(lease.security_deposit_amount),
		"deposit_balance": deposit_balance(lease.security_deposit),
		"charges": ch["rows"], "charges_net": ch["net"], "charges_vat": ch["vat"],
		"charges_total": ch["total"], "vat_rate": ch["vat_rate"], "vat_template": ch["vat_template"],
		"total_deductions": 0.0, "net_settlement": 0.0, "result": SETTLED,
	}
	rent = 0.0
	if lease.rent_schedule:
		rows = frappe.get_all(
			"Rent Installment",
			filters={"parent": lease.rent_schedule, "parenttype": "Rent Schedule"},
			fields=["name", "installment_no", "due_date", "amount", "paid_amount", "status", "sales_invoice"],
			order_by="due_date asc, installment_no asc")
		live = [r for r in rows if r.status != "Cancelled"]
		prorate = cint(settings.prorate_final_rent)
		for idx, r in enumerate(live):
			due = getdate(r.due_date)
			si = _live_invoice(r.sales_invoice)
			adj = {"installment": r.name, "due_date": str(due), "sales_invoice": si.name if si else None,
			       "to_invoice": 0, "credit_net": 0.0, "credit_gross": 0.0, "kind": ""}
			if due > end:
				if not si:
					continue  # never invoiced: the installment simply stops
				gross, before = flt(si.grand_total), flt(si.outstanding_amount)
				adj.update(kind="full", credit_net=flt(r.amount, 3), credit_gross=gross)
			else:
				if si:
					gross, before = flt(si.grand_total), flt(si.outstanding_amount)
				elif r.status in CLOSED:
					continue  # settled outside invoicing
				else:
					gross = _simulate_gross(lease, r, settings)
					before = flt(max(gross * (1 - min(flt(r.paid_amount) / flt(r.amount or 1), 1)), 0), 3)
					adj["to_invoice"] = 1
				period_end = getdate(live[idx + 1].due_date) if idx + 1 < len(live) else add_days(getdate(lease.end_date), 1)
				period_end = add_days(period_end, -1)
				if prorate and due <= end < period_end and flt(r.amount):
					frac = date_diff(period_end, end) / float(date_diff(period_end, due) + 1)
					net = flt(flt(r.amount) * frac, 2)
					adj.update(kind="prorata", credit_net=net, credit_gross=_rounded(net * gross / flt(r.amount)),
					           unused_days=date_diff(period_end, end), period_days=date_diff(period_end, due) + 1)
			credit = flt(adj["credit_gross"])
			adj.update(gross=flt(gross, 3), outstanding_before=flt(before, 3),
			           outstanding_after=flt(max(before - credit, 0), 3),
			           excess_paid=flt(max(credit - before, 0), 3))
			out["adjustments"].append(adj)
			rent += adj["outstanding_after"]
			out["paid_after_end"] += adj["excess_paid"]
			out["credit_note_total"] += credit
			if adj["outstanding_after"]:
				out["outstanding_installments"].append({
					"installment": r.name, "due_date": adj["due_date"], "amount": adj["outstanding_after"],
					"status": r.status})
			if adj["kind"] == "full":
				out["advance_invoices"].append({
					"installment": r.name, "due_date": adj["due_date"], "sales_invoice": si.name,
					"grand_total": gross, "paid": max(gross - before, 0), "outstanding": before})
	out["rent_outstanding"] = flt(rent, 3)
	out["paid_after_end"] = flt(out["paid_after_end"], 3)
	out["credit_note_total"] = flt(out["credit_note_total"], 3)
	out["total_deductions"] = flt(out["rent_outstanding"] + ch["total"], 3)
	out["net_settlement"] = flt(out["deposit_balance"] + out["paid_after_end"] - out["total_deductions"], 3)
	out["result"] = PAYABLE if out["net_settlement"] > TOL / 10 else RECEIVABLE if out["net_settlement"] < -TOL / 10 else SETTLED
	if out["result"] == SETTLED:
		out["net_settlement"] = 0.0
	out["token"] = token_for(lease, out)
	return out


def token_for(lease, s):
	"""Fingerprint of the inputs and the ledger state the figures were calculated from."""
	basis = {
		"lease": lease.name, "end": s["tenancy_end_date"], "posting": s["posting_date"],
		"charges": [(c["description"], c["amount"], c["vat_applicable"]) for c in s["charges"]],
		"adj": [(a["installment"], a["sales_invoice"], a["outstanding_before"], a["credit_net"])
		        for a in s["adjustments"]],
		"deposit": s["deposit_balance"], "rent": s["rent_outstanding"], "net": s["net_settlement"],
	}
	return hashlib.sha256(json.dumps(basis, sort_keys=True, default=str).encode()).hexdigest()[:32]


# --------------------------------------------------------------------------- posting

def _credit_note(lease, adj, posting_date):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	cn = make_return_doc("Sales Invoice", adj["sales_invoice"])
	cn.set_posting_time = 1
	cn.posting_date = posting_date
	cn.due_date = posting_date
	if adj["kind"] == "prorata":
		for it in cn.items:
			it.qty = -1
			it.rate = flt(adj["credit_net"], 3)
			it.amount = -flt(adj["credit_net"], 3)
		cn.remarks = _("Credit note: lease {0} ended {1}; unused {2} of {3} days of the period due {4}").format(
			lease.name, adj.get("end"), adj.get("unused_days"), adj.get("period_days"), adj["due_date"])
	else:
		cn.remarks = _("Credit note: lease {0} ended on tenancy end date, instalment due {1} not payable").format(
			lease.name, adj["due_date"])
	cn.insert(ignore_permissions=True)
	cn.submit()
	return cn


def _zero_vat_template(company, account_head):
	"""An existing Item Tax Template that sets the VAT account to 0% (exempt / not applicable)."""
	rows = frappe.db.sql(
		"""select t.name from `tabItem Tax Template` t join `tabItem Tax Template Detail` d on d.parent = t.name
		   where t.company = %s and t.disabled = 0 and d.tax_type = %s and d.tax_rate = 0 order by t.name limit 1""",
		(company, account_head))
	return rows[0][0] if rows else None


def _charge_invoice(lease, customer, ch, posting_date, settings):
	si = frappe.new_doc("Sales Invoice")
	from thinknxg_estate.core.tasks import set_company_currency

	si.customer = customer
	si.company = lease.company
	set_company_currency(si, lease.company)
	si.set_posting_time = 1
	si.posting_date = posting_date
	si.due_date = posting_date
	si.remarks = _("Tenant charges on termination of lease {0}").format(lease.name)
	vat = vat_config(lease) if any(r["vat_applicable"] for r in ch["rows"]) else None
	for r in ch["rows"]:
		item = {"item_code": settings.rent_item, "item_name": r["description"][:140],
		        "description": r["description"], "qty": 1, "rate": r["amount"]}
		if vat and not r["vat_applicable"]:
			zero = _zero_vat_template(lease.company, vat["account_head"])
			if zero:
				item["item_tax_template"] = zero
			item["item_tax_rate"] = json.dumps({vat["account_head"]: 0})
		si.append("items", item)
	if vat:
		si.taxes_and_charges = vat["template"]
		si.set_taxes()
	else:
		si.taxes_and_charges = None
		si.taxes = []
	si.insert(ignore_permissions=True)
	si.submit()
	return si


def post_settlement(lease, s, end, posting_date, mode_of_payment, reasons=None):
	"""Create every accounting document for the termination. Caller wraps this in a savepoint."""
	from thinknxg_estate.core import tasks
	from thinknxg_estate.core.security_deposit_accounting import _get_liability_account

	settings = frappe.get_single("Property Settings")
	customer = _customer(lease)
	company = lease.company
	pd = getdate(posting_date)
	created = {"rent_invoices": [], "credit_notes": [], "charge_invoice": None, "journal_entry": None}
	restore = []
	ch = {"rows": s["charges"], "net": s["charges_net"], "vat": s["charges_vat"], "total": s["charges_total"]}

	# 1. invoice what is due but not yet billed
	for a in s["adjustments"]:
		if a["to_invoice"]:
			row = frappe.db.get_value("Rent Installment", a["installment"],
			                          ["name", "due_date", "amount"], as_dict=True)
			row["lease_contract"] = lease.name
			si = tasks._invoice_installment(row, settings, posting_date=pd, allow_status=("Active", "Expiring"))
			if not si:
				frappe.throw(_("Could not invoice installment due {0}.").format(a["due_date"]))
			a["sales_invoice"] = si.name
			created["rent_invoices"].append(si.name)

	# 2. credit notes
	for a in s["adjustments"]:
		if a["credit_gross"]:
			a["end"] = str(end)
			cn = _credit_note(lease, a, pd)
			a["credit_note"] = cn.name
			created["credit_notes"].append(cn.name)

	# 3. tenant charges invoice
	charge_si = None
	if ch["rows"]:
		charge_si = _charge_invoice(lease, customer, ch, pd, settings)
		created["charge_invoice"] = charge_si.name
		if abs(flt(charge_si.grand_total) - ch["total"]) > TOL:
			frappe.throw(_("Tenant charges invoice total {0} differs from the calculated {1}.")
			             .format(charge_si.grand_total, ch["total"]))

	# 4. actual ledger figures after the documents above (Payment Ledger: invoice and credit-note
	#    balances are separate until allocated, so both are referenced in the entry)
	rent_cr, excess_dr = [], []
	rent_actual = excess_actual = 0.0
	for a in s["adjustments"]:
		inv_acct = frappe.db.get_value("Sales Invoice", a["sales_invoice"], "debit_to")
		inv_out = _ledger_outstanding(a["sales_invoice"])
		cn_out = _ledger_outstanding(a["credit_note"]) if a.get("credit_note") else 0.0
		if inv_out > 0:
			rent_cr.append((a["sales_invoice"], inv_acct, inv_out))
		if cn_out < 0:
			excess_dr.append((a["credit_note"], inv_acct, -cn_out))
		x = inv_out + cn_out
		rent_actual += max(x, 0)
		excess_actual += max(-x, 0)
	rent_actual, excess_actual = flt(rent_actual, 3), flt(excess_actual, 3)
	if abs(rent_actual - s["rent_outstanding"]) > TOL or abs(excess_actual - s["paid_after_end"]) > TOL:
		frappe.throw(_("The ledger no longer matches the calculated settlement (rent {0} vs {1}, credit {2} vs {3}). "
		               "Calculate Amount again.").format(rent_actual, s["rent_outstanding"], excess_actual, s["paid_after_end"]))

	deposit = flt(s["deposit_balance"], 3)
	charge_out = _ledger_outstanding(charge_si.name) if charge_si else 0.0
	net = flt(deposit + sum(x[2] for x in excess_dr) - sum(x[2] for x in rent_cr) - charge_out, 3)

	# 5. settlement journal entry
	lines = []
	cost_center = frappe.db.get_value("Company", company, "cost_center")
	if deposit:
		lines.append({"account": _get_liability_account(company), "party_type": "Customer", "party": customer,
		              "debit_in_account_currency": deposit,
		              "user_remark": _("Security deposit applied on termination of {0}").format(lease.name)})
	for inv, acct, amt in rent_cr:
		lines.append({"account": acct, "party_type": "Customer", "party": customer, "reference_type": "Sales Invoice",
		              "reference_name": inv, "credit_in_account_currency": amt})
	if charge_si and charge_out:
		lines.append({"account": charge_si.debit_to, "party_type": "Customer", "party": customer,
		              "reference_type": "Sales Invoice", "reference_name": charge_si.name,
		              "credit_in_account_currency": charge_out})
	for inv, acct, amt in excess_dr:
		lines.append({"account": acct, "party_type": "Customer", "party": customer, "reference_type": "Sales Invoice",
		              "reference_name": inv, "debit_in_account_currency": amt})
	if abs(net) > TOL / 10:
		acc = payment_account(mode_of_payment, company)
		if net > 0:   # pay the tenant
			lines.append({"account": acc, "credit_in_account_currency": net})
		else:         # collect from the tenant
			lines.append({"account": acc, "debit_in_account_currency": -net})
	if lines:
		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Journal Entry"
		je.company = company
		je.posting_date = pd
		je.mode_of_payment = mode_of_payment if abs(net) > TOL / 10 else None
		je.user_remark = _("Final settlement - termination of lease {0}, tenancy ended {1}").format(lease.name, end)
		for ln in lines:
			ln["cost_center"] = cost_center
			je.append("accounts", ln)
		if abs(sum(flt(x.get("debit_in_account_currency")) for x in lines)
		       - sum(flt(x.get("credit_in_account_currency")) for x in lines)) > TOL:
			frappe.throw(_("Settlement entry is not balanced."))
		je.insert(ignore_permissions=True)
		je.submit()
		created["journal_entry"] = je.name

	# 6. security deposit
	if lease.security_deposit and deposit:
		applied = min(deposit, max(rent_actual + charge_out - excess_actual, 0))
		refunded = flt(deposit - applied, 3)
		dep = frappe.db.get_value("Security Deposit", lease.security_deposit,
		                          ["deduction_amount", "refunded_amount", "status"], as_dict=True)
		frappe.db.set_value("Security Deposit", lease.security_deposit, {
			"deduction_amount": flt(dep.deduction_amount) + applied,
			"refunded_amount": flt(dep.refunded_amount) + refunded,
			"status": "Refunded" if refunded else "Forfeited",
		})
		created["deposit_before"] = {"deduction_amount": flt(dep.deduction_amount),
		                            "refunded_amount": flt(dep.refunded_amount), "status": dep.status}
		created["deposit_applied"], created["deposit_refunded"] = applied, refunded

	# 7. installments
	for a in s["adjustments"]:
		prior = frappe.db.get_value("Rent Installment", a["installment"],
		                            ["status", "paid_amount", "remarks"], as_dict=True)
		restore.append({"name": a["installment"], **prior})
		if a["kind"] == "full":
			frappe.db.set_value("Rent Installment", a["installment"], {
				"status": "Cancelled", "remarks": _("Credited by {0} on {1}").format(a.get("credit_note"), pd)})
		else:
			amount = flt(frappe.db.get_value("Rent Installment", a["installment"], "amount"))
			frappe.db.set_value("Rent Installment", a["installment"], {
				"status": "Paid", "paid_amount": max(amount - flt(a["credit_net"]), 0),
				"remarks": _("Settled on termination {0}").format(created["journal_entry"] or "")})
	created["restore_installments"] = restore
	created["net"] = net
	return created


def snapshot(settlement, created=None):
	data = dict(settlement)
	if created:
		data["posted"] = created
	return json.dumps(data, default=str)


def reverse_termination(lease, reason):
	"""Undo a termination: cancel the settlement documents in reverse order, restore the lease."""
	if lease.status != "Terminated" or not lease.termination_settlement:
		frappe.throw(_("Lease {0} is not terminated.").format(lease.name))
	posted = (json.loads(lease.termination_settlement) or {}).get("posted") or {}
	je_name, charge_name = lease.termination_journal_entry, lease.termination_charge_invoice
	lease.db_set({"termination_journal_entry": None, "termination_charge_invoice": None})  # release the links
	lease.termination_journal_entry = je_name
	if lease.termination_journal_entry and frappe.db.get_value("Journal Entry", lease.termination_journal_entry, "docstatus") == 1:
		frappe.get_doc("Journal Entry", je_name).cancel()
	for dt, names in (("Sales Invoice", [posted.get("charge_invoice")]),
	                  ("Sales Invoice", posted.get("credit_notes") or []),
	                  ("Sales Invoice", posted.get("rent_invoices") or [])):
		for n in filter(None, names):
			if frappe.db.get_value(dt, n, "docstatus") == 1:
				frappe.get_doc(dt, n).cancel()
	for r in posted.get("restore_installments") or []:
		frappe.db.set_value("Rent Installment", r["name"], {
			"status": r["status"], "paid_amount": r["paid_amount"], "remarks": r["remarks"]})
	for r in posted.get("rent_invoices") or []:
		frappe.db.set_value("Rent Installment", {"sales_invoice": r}, {"sales_invoice": None, "status": "Pending"})
	if lease.security_deposit and posted.get("deposit_before"):
		frappe.db.set_value("Security Deposit", lease.security_deposit, posted["deposit_before"])
	if lease.unit:
		frappe.db.set_value("Unit", lease.unit, {"status": "Occupied", "current_lease": lease.name})
	else:
		frappe.db.set_value("Property", lease.property, "current_lease", lease.name)
	lease.db_set({"status": "Active", "tenancy_end_date": None, "termination_posting_date": None,
	              "termination_settlement": None, "termination_settlement_status": None,
	              "termination_mode_of_payment": None, "termination_journal_entry": None,
	              "termination_charge_invoice": None, "terminated_by": None, "terminated_on": None})
	lease.add_comment("Comment", _("Termination reversed by {0}: {1}").format(frappe.session.user, reason))
	return lease.status


def stamp(lease, s, created, mode_of_payment, end, posting_date):
	lease.db_set({
		"status": "Terminated",
		"tenancy_end_date": end,
		"termination_posting_date": getdate(posting_date),
		"termination_settlement": snapshot(s, created),
		"termination_settlement_status": s["result"],
		"termination_mode_of_payment": mode_of_payment if abs(flt(s["net_settlement"])) > TOL / 10 else None,
		"termination_journal_entry": created.get("journal_entry"),
		"termination_charge_invoice": created.get("charge_invoice"),
		"terminated_by": frappe.session.user,
		"terminated_on": get_datetime(now_datetime()),
	})
