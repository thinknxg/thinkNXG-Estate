import frappe
from frappe.utils import cint


def setting(doctype, fieldname, default=None):
	"""Value of a Single field, or `default` when the site has never stored one.

	Settings added in an upgrade have no row in tabSingles until someone saves the form, and
	get_single_value would then return 0 for a checkbox whose declared default is 1."""
	row = frappe.db.sql("select value from `tabSingles` where doctype=%s and field=%s",
	                    (doctype, fieldname))
	if not row or row[0][0] in (None, ""):
		return default
	return row[0][0]


def enabled(doctype, fieldname, default=0):
	return bool(cint(setting(doctype, fieldname, default)))
