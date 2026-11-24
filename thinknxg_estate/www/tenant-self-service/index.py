import frappe

no_cache = 1


def get_context(context):
	# Access-code sign in is opt-in (Property Settings); everyone else uses the tenant portal.
	if not frappe.db.get_single_value("Property Settings", "enable_access_code_portal"):
		frappe.local.flags.redirect_location = "/tenant-portal"
		raise frappe.Redirect
	context.csrf_token = frappe.sessions.get_csrf_token()
	context.no_cache = 1
	return context
