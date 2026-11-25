from thinknxg_estate.compat import LEGACY_METHODS

app_name = "thinknxg_estate"
app_title = "thinkNXG Estate"
app_publisher = "Kreatao"
app_description = "Property Management, Leasing and Real Estate CRM on thinkNXG ERP"
app_email = "sales@kreatao.com"
app_license = "MIT"
app_logo_url = "/assets/thinknxg_estate/images/thinknxg_estate_logo.svg"

required_apps = ["erpnext"]

before_install = "thinknxg_estate.setup.install.before_install"
after_install = "thinknxg_estate.setup.install.after_install"
after_sync = "thinknxg_estate.setup.install.after_sync"
after_migrate = "thinknxg_estate.setup.install.after_migrate"

add_to_apps_screen = [
	{
		"name": "thinknxg_estate",
		"logo": "/assets/thinknxg_estate/images/thinknxg_estate_logo.svg",
		"title": "thinkNXG Estate",
		"route": "/app/thinknxg-estate",
	}
]

# ----------------------------------------------------------------------------- fixtures
ESTATE_ROLES = [
	# operations
	"RE Manager", "Property Manager", "Leasing Manager", "Leasing Officer", "Maintenance Supervisor",
	"Maintenance Technician", "Receptionist",
	# CRM
	"RE Sales Manager", "RE Sales Agent", "Broker",
	# voice / messaging
	"Voice Ops Manager",
	# portal users
	"Tenant", "Property Owner",
]

fixtures = [
	{"dt": "Role", "filters": [["name", "in", ESTATE_ROLES]]},
	{"dt": "Custom Field", "filters": [["module", "=", "thinkNXG Estate"]]},
	{"dt": "Print Format", "filters": [["name", "in", ["Lease Contract Standard", "Tenant Rent Invoice"]]]},
]

# ----------------------------------------------------------------------------- website
web_include_js = ["/assets/thinknxg_estate/js/chat_widget.js"]
web_include_css = ["/assets/thinknxg_estate/css/estate.css", "/assets/thinknxg_estate/css/chat_widget.css"]

jinja = {"methods": ["thinknxg_estate.portal.utils.money", "thinknxg_estate.portal.utils.amount"]}

# /listings was a second public site; /properties replaced it in 1.2.
website_redirects = [
	{"source": "/listings", "target": "/properties"},
	{"source": r"/listings/(.*)", "target": "/properties"},
]

# Short address for the tenant self-service app. A route rewrite, not a redirect: the page is
# served as is, and /tenant-self-service keeps working.
website_route_rules = [
	{"from_route": "/re-tenant", "to_route": "tenant-self-service"},
]

standard_portal_menu_items = [
	{"title": "My Tenancy", "route": "/tenant-portal", "role": "Tenant"},
	{"title": "Tenant Self-Service", "route": "/re-tenant", "role": "Tenant"},
	{"title": "My Properties", "route": "/owner-portal", "role": "Property Owner"},
]

doctype_js = {
	"Property": ["public/js/property_live_toggle.js", "public/js/estate_timeline.js"],
	"Unit": "public/js/unit_lease_contract.js",
	"RE Lead": "public/js/estate_timeline.js",
	"RE Deal": "public/js/estate_timeline.js",
	"Tenant": "public/js/estate_timeline.js",
	"Property Owner": "public/js/estate_timeline.js",
}

# ----------------------------------------------------------------------------- permissions
# Row-level isolation for portal Tenant users (staff roles are unaffected).
_PERM = "thinknxg_estate.core.permissions"
permission_query_conditions = {
	"Lease Contract": f"{_PERM}.lease_contract_query",
	"Rent Schedule": f"{_PERM}.rent_schedule_query",
	"Post Dated Cheque": f"{_PERM}.pdc_query",
	"Security Deposit": f"{_PERM}.security_deposit_query",
	"Maintenance Request": f"{_PERM}.maintenance_request_query",
	"Tenant": f"{_PERM}.tenant_query",
}
has_permission = {dt: f"{_PERM}.has_permission" for dt in permission_query_conditions}

# CRM record ownership for sales agents
for _dt, _fn in (("RE Lead", "re_lead_query"), ("RE Deal", "re_deal_query"), ("Site Visit", "site_visit_query")):
	permission_query_conditions[_dt] = f"{_PERM}.{_fn}"
	has_permission[_dt] = f"{_PERM}.agent_has_permission"

# ----------------------------------------------------------------------------- events
doc_events = {
	"Post Dated Cheque": {
		"on_submit": "thinknxg_estate.core.pdc_bank_sync.create_or_sync_payment_entry",
	},
	"Security Deposit": {
		"on_submit": "thinknxg_estate.core.security_deposit_accounting.create_deposit_journal_entry",
	},
	"Lease Contract": {
		"on_submit": "thinknxg_estate.estate_portal.doctype.listing.listing.unpublish_unit_listings",
	},
	"Listing": {
		"on_update": "thinknxg_estate.portal.api.catalog.clear_cache",
		"on_trash": "thinknxg_estate.portal.api.catalog.clear_cache",
	},
	"Property": {"on_update": "thinknxg_estate.portal.sync.sync_property_on_update"},
	"Unit": {"on_update": "thinknxg_estate.portal.sync.sync_unit_on_update"},
	"Site Visit": {"on_update": "thinknxg_estate.voice.events.on_site_visit_update"},
	"RE Lead": {
		"after_insert": "thinknxg_estate.voice.events.on_lead_insert",
		"on_update": "thinknxg_estate.crm.matching.recommend_on_qualify",
	},
}

# ----------------------------------------------------------------------------- scheduler
scheduler_events = {
	"hourly": [
		"thinknxg_estate.crm.tasks.lead_sla_escalation",
		"thinknxg_estate.crm.tasks.site_visit_reminders",
		"thinknxg_estate.voice.tasks.post_visit_feedback_prompts",
	],
	"daily": [
		# leasing & collections
		"thinknxg_estate.core.tasks.invoice_due_installments",
		"thinknxg_estate.core.tasks.mark_overdue_installments",
		"thinknxg_estate.core.tasks.lease_expiry_pipeline",
		"thinknxg_estate.core.tasks.pdc_deposit_reminders",
		"thinknxg_estate.core.tasks.document_expiry_alerts",
		# CRM
		"thinknxg_estate.crm.tasks.release_expired_reservations",
		"thinknxg_estate.crm.tasks.rent_due_whatsapp_reminders",
		# portal
		"thinknxg_estate.core.listing_portal_api.listing_portal.check_saved_searches",
		"thinknxg_estate.portal.sync.backfill_all",
		# voice & AI
		"thinknxg_estate.voice.tasks.nightly_scoring",
		"thinknxg_estate.voice.tasks.refresh_thread_summaries",
		"thinknxg_estate.voice.tasks.purge_expired_audio",
		"thinknxg_estate.voice.tasks.purge_expired_transcripts",
		"thinknxg_estate.voice.tasks.reset_monthly_spend",
	],
	"monthly": [
		"thinknxg_estate.core.owner_statement_scheduler.generate_monthly_owner_statements",
	],
}

# ----------------------------------------------------------------------------- compatibility
# Old /api/method/re_core..., re_crm..., re_portal..., re_voice... URLs keep working.
override_whitelisted_methods = LEGACY_METHODS
