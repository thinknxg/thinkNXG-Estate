"""Owner self-service APIs (/owner-portal).

The owner is always resolved from the session user; record names from the client are only
accepted after checking they belong to that owner. Owners have no document permissions:
every query here is scoped server-side to the properties and units they own.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

OPEN_INSTALLMENT = ("Pending", "Invoiced", "Overdue", "Partially Paid")
OPEN_MAINTENANCE = ("Open", "In Progress", "On Hold")


def require_owner():
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in."), frappe.PermissionError)
	from thinknxg_estate.estate_property.doctype.property_owner.property_owner import get_owner_for_user

	owner = get_owner_for_user()
	if not owner:
		frappe.throw(_("No owner profile is linked to your account."), frappe.PermissionError)
	return owner


def owner_scope(owner):
	"""Properties owned outright, and units owned (including units inside those properties)."""
	properties = frappe.get_all("Property", {"owner_ref": owner}, pluck="name")
	units = set(frappe.get_all("Unit", {"owner_ref": owner}, pluck="name"))
	if properties:
		units |= set(frappe.get_all("Unit", {"property": ["in", properties]}, pluck="name"))
	return properties, sorted(units)


def _leases(properties, units, active_only=True):
	if not (properties or units):
		return []
	conditions, values = [], {}
	if units:
		conditions.append("unit in %(units)s")
		values["units"] = tuple(units)
	if properties:
		conditions.append("(ifnull(unit, '') = '' and property in %(properties)s)")
		values["properties"] = tuple(properties)
	status = "and status in ('Active', 'Expiring')" if active_only else ""
	return frappe.db.sql(f"""
		select name, unit, property, tenant_name, start_date, end_date, status,
		       total_contract_value, payment_frequency, rent_schedule
		from `tabLease Contract`
		where docstatus = 1 {status} and ({' or '.join(conditions)})
		order by end_date asc""", values, as_dict=True)


@frappe.whitelist()
def dashboard(year=None):
	owner = require_owner()
	year = cint(year) or getdate(nowdate()).year
	start, end = f"{year}-01-01", f"{year}-12-31"
	properties, units = owner_scope(owner)
	owner_doc = frappe.db.get_value("Property Owner", owner, ["owner_name", "company"], as_dict=True)

	unit_rows = frappe.get_all("Unit", {"name": ["in", units or [""]]},
	                           ["name", "unit_no", "unit_title", "property", "status", "annual_rent"],
	                           order_by="property asc, unit_no asc")
	by_status = {}
	for u in unit_rows:
		by_status[u.status] = by_status.get(u.status, 0) + 1
	occupied = by_status.get("Occupied", 0)

	leases = _leases(properties, units)
	all_leases = _leases(properties, units, active_only=False)
	schedules = [lc.rent_schedule for lc in all_leases if lc.rent_schedule]

	income = outstanding = 0.0
	monthly = {}
	if schedules:
		for row in frappe.get_all("Rent Installment",
		                          {"parent": ["in", schedules], "due_date": ["between", [start, end]]},
		                          ["due_date", "amount", "paid_amount", "status"]):
			income += flt(row.paid_amount)
			key = getdate(row.due_date).strftime("%Y-%m")
			monthly.setdefault(key, {"billed": 0.0, "collected": 0.0})
			monthly[key]["billed"] += flt(row.amount)
			monthly[key]["collected"] += flt(row.paid_amount)
		outstanding = sum(
			flt(r.amount) - flt(r.paid_amount)
			for r in frappe.get_all("Rent Installment",
			                        {"parent": ["in", schedules], "status": ["in", OPEN_INSTALLMENT],
			                         "due_date": ["<=", nowdate()]},
			                        ["amount", "paid_amount"]))

	expenses = frappe.get_all(
		"Expense Property",
		{"property": ["in", properties or [""]], "docstatus": 1,
		 "expense_date": ["between", [start, end]]},
		["name", "property", "expense_date", "expense_type", "amount", "status"],
		order_by="expense_date desc") if properties else []

	statements = frappe.get_all(
		"Owner Statement", {"property_owner": owner, "docstatus": 1},
		["name", "period_from", "period_to", "rent_invoiced", "management_fee", "owner_expenses",
		 "net_payable", "purchase_invoice"], order_by="period_from desc", limit=24)
	for st in statements:
		st["paid"] = bool(st.purchase_invoice and frappe.db.get_value(
			"Purchase Invoice", st.purchase_invoice, "outstanding_amount") == 0)

	maintenance = frappe.get_all(
		"Maintenance Request",
		filters=[["unit", "in", units or [""]]],
		fields=["name", "unit", "category", "priority", "status", "creation"],
		order_by="creation desc", limit=20)

	return {
		"owner": owner,
		"owner_name": owner_doc.owner_name,
		"year": year,
		"property_count": len(properties),
		"unit_count": len(unit_rows),
		"occupied": occupied,
		"vacant": by_status.get("Vacant", 0),
		"reserved": by_status.get("Reserved", 0),
		"occupancy_rate": round(occupied * 100.0 / len(unit_rows), 1) if unit_rows else 0,
		"units": unit_rows,
		"leases": leases,
		"income_collected": flt(income, 3),
		"rent_outstanding": flt(outstanding, 3),
		"expenses_total": flt(sum(flt(e.amount) for e in expenses), 3),
		"expenses": expenses[:20],
		"monthly": [dict(month=k, **v) for k, v in sorted(monthly.items())],
		"statements": statements,
		"maintenance": maintenance,
		"open_maintenance": sum(1 for m in maintenance if m.status in OPEN_MAINTENANCE),
	}


@frappe.whitelist()
def statement(name, pdf=0):
	"""Printable owner statement, only for the statement's own owner."""
	owner = require_owner()
	if frappe.db.get_value("Owner Statement", {"name": name, "docstatus": 1}, "property_owner") != owner:
		frappe.throw(_("Statement not found."), frappe.PermissionError)
	frappe.flags.ignore_print_permissions = True
	try:
		if cint(pdf):
			frappe.local.response.filename = f"{name}.pdf"
			frappe.local.response.filecontent = frappe.get_print("Owner Statement", name, as_pdf=True)
			frappe.local.response.type = "pdf"
			return
		return frappe.get_print("Owner Statement", name)
	finally:
		frappe.flags.ignore_print_permissions = False
