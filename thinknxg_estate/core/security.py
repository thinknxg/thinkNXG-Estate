"""Server-side authorization helpers for thinkNXG Estate.

Two rules that every endpoint follows:

1. Staff APIs (the desk console, CRM actions, finance actions) are callable only by desk
   users who hold an estate or accounting role. Website users (tenants, portal visitors)
   are refused even though they are logged in, because several staff endpoints aggregate
   data with direct database reads that do not apply record permissions.

2. Whitelisted document methods that change state check the matching document permission
   themselves. Frappe's run_doc_method only checks *read* permission, so without this a
   tenant who can read their own post-dated cheque could mark it cleared (posting a Payment
   Entry) or refund their own security deposit.
"""

from functools import wraps

import frappe
from frappe import _

ESTATE_STAFF_ROLES = frozenset({
	"System Manager", "RE Manager", "Property Manager", "Leasing Officer", "Maintenance Supervisor",
	"RE Sales Manager", "RE Sales Agent", "Voice Ops Manager", "Accounts User", "Accounts Manager",
})


def is_estate_staff(user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	if user == "Guest" or frappe.db.get_value("User", user, "user_type") != "System User":
		return False
	return bool(ESTATE_STAFF_ROLES & set(frappe.get_roles(user)))


def require_staff():
	if not is_estate_staff():
		frappe.throw(_("You are not permitted to use this function."), frappe.PermissionError)


def staff_only(fn):
	"""Decorator for whitelisted staff endpoints. Place it below @frappe.whitelist()."""

	@wraps(fn)
	def wrapper(*args, **kwargs):
		require_staff()
		return fn(*args, **kwargs)

	return wrapper


def requires_permission(ptype):
	"""Decorator for whitelisted document methods: the caller needs `ptype` on this document.
	Internal callers that have already authorized the action may set
	doc.flags.ignore_permissions = True."""

	def decorator(fn):
		@wraps(fn)
		def wrapper(self, *args, **kwargs):
			self.check_permission(ptype)
			return fn(self, *args, **kwargs)

		return wrapper

	return decorator
