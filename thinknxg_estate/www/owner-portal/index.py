import frappe
from frappe import _

from thinknxg_estate.portal.utils import money

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/owner-portal"
		raise frappe.Redirect
	from thinknxg_estate.portal.api.owner import dashboard

	context.update(dashboard(year=frappe.form_dict.get("year")))
	context.money = money
	context.title = _("My Properties")
	context.no_cache = 1
	return context
