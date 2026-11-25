import frappe

no_cache = 1


def get_context(context):
	# /tenant-self-service is its own application. It never redirects to /tenant-portal:
	# sign-in (website account or, when enabled, mobile + access code) happens inside the page
	# and every data call is authorised server-side by thinknxg_estate.core.tenant_self_service.
	context.no_cache = 1
	context.no_breadcrumbs = 1
	context.csrf_token = frappe.sessions.get_csrf_token() if frappe.session.user != "Guest" else ""
	context.site_title = "thinkNXG Estate"
	context.lang = frappe.local.lang or "en"
	context.is_rtl = 1 if (frappe.local.lang or "").split("-")[0] in ("ar", "he", "fa", "ur") else 0
	return context
