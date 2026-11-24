"""Accounts and records the HTTP smoke test (scripts/consolidation/smoke.sh) signs in with.
For test and staging copies only; refuses to run unless `allow_tests` is set in site_config.

Prints the shell variables smoke.sh expects:
    eval "$(bench --site SITE console <<< 'from thinknxg_estate.setup.smoke_fixtures import run; run()' | grep ^export)"
"""

import frappe
from frappe.utils import add_months, nowdate

TENANT_EMAIL, TENANT_PASSWORD = "smoke.tenant@example.com", "Smoke#Tenant2026"
OWNER_EMAIL, OWNER_PASSWORD = "smoke.owner@example.com", "Smoke#Owner2026"


def _vacant_unit(exclude=None):
	return frappe.db.get_value("Unit", {"status": "Vacant", "annual_rent": [">", 0],
	                                    "name": ["not in", exclude or [""]]}, "name")


def _lease(tenant, unit):
	lease = frappe.get_doc({
		"doctype": "Lease Contract", "tenant": tenant, "unit": unit, "start_date": nowdate(),
		"end_date": add_months(nowdate(), 12), "payment_frequency": "Quarterly",
		"charges": [{"charge_type": "Rent", "description": "Base Rent",
		             "amount": frappe.db.get_value("Unit", unit, "annual_rent")}],
	}).insert(ignore_permissions=True)
	lease.submit()
	return lease.name


def run():
	if not frappe.conf.get("allow_tests"):
		frappe.throw("Smoke fixtures are for test sites: set allow_tests in site_config.json first.")
	company = frappe.db.get_value("Company", {}, "name")

	tenant = frappe.db.get_value("Tenant", {"email": TENANT_EMAIL})
	if not tenant:
		doc = frappe.get_doc({"doctype": "Tenant", "tenant_name": "Smoke Tenant", "mobile": "+96890007001",
		                      "email": TENANT_EMAIL, "enable_portal": 1}).insert(ignore_permissions=True)
		tenant = doc.name
	user = frappe.get_doc("User", TENANT_EMAIL)
	user.new_password = TENANT_PASSWORD
	user.save(ignore_permissions=True)
	own = frappe.db.get_value("Lease Contract", {"tenant": tenant, "docstatus": 1}) or _lease(tenant, _vacant_unit())

	other = frappe.db.get_value("Lease Contract", {"tenant": ["!=", tenant], "docstatus": 1})
	if not other:
		other_tenant = frappe.get_doc({"doctype": "Tenant", "tenant_name": "Smoke Other Tenant",
		                               "mobile": "+96890007002"}).insert(ignore_permissions=True).name
		other = _lease(other_tenant, _vacant_unit())

	owner = frappe.db.get_value("Property Owner", {"email": OWNER_EMAIL})
	if not owner:
		owner = frappe.get_doc({"doctype": "Property Owner", "owner_name": "Smoke Owner", "company": company,
		                        "email": OWNER_EMAIL, "enable_portal": 1}).insert(ignore_permissions=True).name
	owner_user = frappe.get_doc("User", OWNER_EMAIL)
	owner_user.new_password = OWNER_PASSWORD
	owner_user.save(ignore_permissions=True)

	lead = frappe.db.get_value("RE Lead", {}) or frappe.get_doc({
		"doctype": "RE Lead", "full_name": "Smoke Lead", "mobile": "+96890007003"}).insert(ignore_permissions=True).name
	frappe.db.commit()
	print(f"export OWN_LEASE={own} OTHER_LEASE={other} LEAD={lead}")
