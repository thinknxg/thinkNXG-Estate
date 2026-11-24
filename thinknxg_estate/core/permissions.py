"""Row-level isolation for portal Tenant users (wired in hooks)."""

import frappe

TENANT_LINKED = {
    "Lease Contract": "tenant",
    "Rent Schedule": "tenant",
    "Post Dated Cheque": "tenant",
    "Security Deposit": "tenant",
    "Maintenance Request": "tenant",
    "Tenant": "name",
}


def _tenant_of(user):
    from thinknxg_estate.estate_leasing.doctype.tenant.tenant import get_tenant_for_user
    return get_tenant_for_user(user)


def _is_portal_tenant(user):
    from thinknxg_estate.core.security import ESTATE_STAFF_ROLES

    roles = frappe.get_roles(user)
    return "Tenant" in roles and not (ESTATE_STAFF_ROLES & set(roles))


def make_query_condition(doctype):
    field = TENANT_LINKED[doctype]

    def query_condition(user):
        user = user or frappe.session.user
        if not _is_portal_tenant(user):
            return None
        tenant = _tenant_of(user)
        if not tenant:
            return "1=0"
        return f"`tab{doctype}`.`{field}` = {frappe.db.escape(tenant)}"

    return query_condition


lease_contract_query = make_query_condition("Lease Contract")
rent_schedule_query = make_query_condition("Rent Schedule")
pdc_query = make_query_condition("Post Dated Cheque")
security_deposit_query = make_query_condition("Security Deposit")
maintenance_request_query = make_query_condition("Maintenance Request")
tenant_query = make_query_condition("Tenant")


def has_permission(doc, ptype, user):
    """Belt-and-braces per-document check for tenant users."""
    if not _is_portal_tenant(user):
        return True
    tenant = _tenant_of(user)
    field = TENANT_LINKED.get(doc.doctype)
    if not field:
        return False
    value = doc.name if field == "name" else doc.get(field)
    return bool(tenant) and value == tenant


# ---------------------------------------------------------------------------- CRM ownership
# Sales agents (RE Sales Agent without a manager role) see the leads, deals and site visits
# assigned to their own RE Agent record. Switch off in RE CRM Settings.
AGENT_LINKED = {"RE Lead": "assigned_agent", "RE Deal": "assigned_agent", "Site Visit": "agent"}
CRM_MANAGER_ROLES = {"RE Sales Manager", "RE Manager", "System Manager", "Property Manager",
                     "Leasing Officer", "Leasing Manager", "Voice Ops Manager", "Receptionist"}
OWN_RECORD_ROLES = {"RE Sales Agent", "Broker"}


def _restricted_agent(user):
	"""The user's RE Agent names if ownership rules apply to them, else None."""
	if user == "Administrator":
		return None
	roles = set(frappe.get_roles(user))
	if not (roles & OWN_RECORD_ROLES) or roles & CRM_MANAGER_ROLES:
		return None
	from thinknxg_estate.utils import enabled

	if not enabled("RE CRM Settings", "agents_see_own_records", default=1):
		return None
	return frappe.get_all("RE Agent", {"user": user}, pluck="name")


def make_agent_condition(doctype):
	field = AGENT_LINKED[doctype]

	def query_condition(user):
		agents = _restricted_agent(user or frappe.session.user)
		if agents is None:
			return None
		if not agents:
			return "1=0"
		return f"`tab{doctype}`.`{field}` in ({', '.join(frappe.db.escape(a) for a in agents)})"

	return query_condition


re_lead_query = make_agent_condition("RE Lead")
re_deal_query = make_agent_condition("RE Deal")
site_visit_query = make_agent_condition("Site Visit")


def agent_has_permission(doc, ptype, user):
	agents = _restricted_agent(user or frappe.session.user)
	if agents is None:
		return True
	value = doc.get(AGENT_LINKED[doc.doctype])
	# a new, unassigned record may be created by the agent; it then needs assigning
	if not value and ptype == "create":
		return True
	return value in agents
