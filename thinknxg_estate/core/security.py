"""Server-side authorization helpers for thinkNXG Estate.

Two rules that every endpoint follows:

1. Console APIs (the /re-portal console, dashboard, CRM and finance actions) are callable only by
   desk users with a portfolio-wide role (CONSOLE_ROLES). Website users (tenants, portal visitors)
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

# Roles that see the whole portfolio: the staff console (/re-portal), the dashboard and the
# console APIs, many of which aggregate without record-level filtering.
CONSOLE_ROLES = frozenset({
	"System Manager", "RE Manager", "Property Manager", "Leasing Manager", "Leasing Officer",
	"Maintenance Supervisor", "RE Sales Manager", "Voice Ops Manager", "Accounts User", "Accounts Manager",
})
# Every desk role of the app, including roles limited to their own or front-desk records, which
# work through desk forms where document permissions and ownership rules apply.
ESTATE_STAFF_ROLES = CONSOLE_ROLES | {"RE Sales Agent", "Broker", "Receptionist", "Maintenance Technician"}


def _desk_user_with(roles, user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	if user == "Guest" or frappe.db.get_value("User", user, "user_type") != "System User":
		return False
	return bool(roles & set(frappe.get_roles(user)))


def is_estate_staff(user=None):
	"""Any desk user of the app."""
	return _desk_user_with(ESTATE_STAFF_ROLES, user)


def is_console_user(user=None):
	"""Desk users who see the whole portfolio."""
	return _desk_user_with(CONSOLE_ROLES, user)


def require_staff():
	if not is_console_user():
		frappe.throw(_("You are not permitted to use this function."), frappe.PermissionError)


def staff_only(fn):
	"""Decorator for whitelisted console endpoints (portfolio-wide data). Place it below
	@frappe.whitelist()."""

	@wraps(fn)
	def wrapper(*args, **kwargs):
		require_staff()
		return fn(*args, **kwargs)

	return wrapper


def desk_staff_only(fn):
	"""Decorator for endpoints any desk role may use because they check record permissions
	themselves (lead matching, communication history)."""

	@wraps(fn)
	def wrapper(*args, **kwargs):
		if not is_estate_staff():
			frappe.throw(_("You are not permitted to use this function."), frappe.PermissionError)
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
