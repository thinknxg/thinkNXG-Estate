"""Final-settlement maths and accounting adjustments for lease termination.

Three dates are kept apart on purpose:

* Schedule End Date  - the contractual end (``Lease Contract.end_date``). Never changed here.
* Tenancy End Date   - the actual end; decides which rent is owed and which is not.
* Posting Date       - the date the settlement entries enter the General Ledger.

Rent is invoiced ahead of its due date (see ``core.tasks.invoice_due_installments``), so an
installment that falls after the Tenancy End Date may already carry a submitted Sales Invoice.
Cancelling the installment alone would leave that invoice receivable on the books, so such
invoices are reversed with a credit note (Sales Invoice return) posted on the Posting Date.
"""

import json

import frappe
from frappe import _
from frappe.utils import flt, getdate

CLOSED = ("Paid", "Cancelled")


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
		["name", "docstatus", "is_return", "grand_total", "outstanding_amount", "currency"], as_dict=True,
	)
	if not si or si.docstatus != 1 or si.is_return:
		return None
	return si


def compute_settlement(lease, tenancy_end_date):
	"""Return the settlement for ``lease`` if the tenancy ends on ``tenancy_end_date``.

	rent_outstanding   unpaid part of every installment due on/before the Tenancy End Date,
	                   whatever its status (Pending, Invoiced, Partially Paid, Overdue, Bounced)
	advance_invoices   installments due AFTER the Tenancy End Date that already hold a live
	                   Sales Invoice; these need a credit note
	paid_after_end     cash already received against those invoices (owed back to the tenant)
	deposit_balance    deposit actually still held, not the original amount
	net_settlement     deposit_balance + paid_after_end - rent_outstanding
	                   (> 0 refundable to tenant, < 0 payable by tenant)
	"""
	end = getdate(tenancy_end_date)
	out = {
		"tenancy_end_date": str(end),
		"schedule_end_date": str(getdate(lease.end_date)),
		"rent_outstanding": 0.0,
		"outstanding_installments": [],
		"advance_invoices": [],
		"credit_note_total": 0.0,
		"paid_after_end": 0.0,
		"deposit_amount": flt(lease.security_deposit_amount),
		"deposit_balance": deposit_balance(lease.security_deposit),
		"net_settlement": 0.0,
	}
	if lease.rent_schedule:
		rows = frappe.get_all(
			"Rent Installment",
			filters={"parent": lease.rent_schedule, "parenttype": "Rent Schedule"},
			fields=["name", "installment_no", "due_date", "amount", "paid_amount", "status", "sales_invoice"],
			order_by="due_date asc, installment_no asc",
		)
		for r in rows:
			if r.status == "Cancelled":
				continue
			if getdate(r.due_date) <= end:
				if r.status in CLOSED:
					continue
				owed = max(flt(r.amount) - flt(r.paid_amount), 0.0)
				if owed:
					out["rent_outstanding"] += owed
					out["outstanding_installments"].append(
						{"installment": r.name, "due_date": str(r.due_date), "amount": owed, "status": r.status})
			else:
				si = _live_invoice(r.sales_invoice)
				if si:
					paid = max(flt(si.grand_total) - flt(si.outstanding_amount), 0.0)
					out["advance_invoices"].append({
						"installment": r.name, "due_date": str(r.due_date), "sales_invoice": si.name,
						"grand_total": flt(si.grand_total), "paid": paid,
						"outstanding": flt(si.outstanding_amount),
					})
					out["credit_note_total"] += flt(si.grand_total)
					out["paid_after_end"] += paid
	out["rent_outstanding"] = flt(out["rent_outstanding"], 3)
	out["net_settlement"] = flt(out["deposit_balance"] + out["paid_after_end"] - out["rent_outstanding"], 3)
	return out


def issue_credit_notes(lease, advance_invoices, posting_date):
	"""Reverse live advance invoices with credit notes dated ``posting_date``.

	Uses the standard ERPNext Sales Invoice return, so receivables, income and tax are
	reversed through the normal ledger entries. Any cash already received stays on the
	customer account as credit and is refunded through the normal Payment Entry process;
	nothing is refunded automatically.
	"""
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	made = []
	for row in advance_invoices:
		cn = make_return_doc("Sales Invoice", row["sales_invoice"])
		cn.set_posting_time = 1
		cn.posting_date = posting_date
		cn.due_date = posting_date
		cn.remarks = _("Credit note: lease {0} ended on tenancy end date, instalment due {1} not payable").format(
			lease.name, row["due_date"])
		cn.insert(ignore_permissions=True)
		cn.submit()
		frappe.db.set_value("Rent Installment", row["installment"], {
			"status": "Cancelled",
			"remarks": _("Credited by {0} on {1}").format(cn.name, posting_date),
		})
		made.append({**row, "credit_note": cn.name})
	return made


def snapshot(settlement, credit_notes=None):
	data = dict(settlement)
	if credit_notes is not None:
		data["credit_notes"] = [c["credit_note"] for c in credit_notes]
	return json.dumps(data, default=str)
