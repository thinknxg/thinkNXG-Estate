"""
Access-code tenant portal API (mobile number + access code, no website account).

Used by /tenant-self-service and the tenant mobile client. The standard tenant portal
(/tenant-portal, thinknxg_estate.portal.api.tenant) uses regular website logins and is
the recommended path; this API is kept for tenants without an email address.

Security model
  * Disabled unless Property Settings > "Enable Access-Code Tenant Portal" is on.
  * Login is rate limited per IP and compares codes in constant time.
  * The opaque session token is returned to the client once; only its SHA-256 hash is
    stored, so a database read does not yield usable sessions.
  * Every endpoint resolves the tenant from the token server-side. A `tenant` value from
    the client is never trusted.
  * Read-only for money: tenants cannot record payments against their own installments
    (that would post Payment Entries on the tenant's word). Payments are recorded by staff
    or through an online payment gateway.
"""

import hashlib
import hmac
import secrets
from datetime import timedelta

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cstr, flt, now_datetime

SESSION_LIFETIME_DAYS = 7


def _hash(token):
    return hashlib.sha256(cstr(token).encode()).hexdigest()


def _ensure_enabled():
    if not frappe.db.get_single_value("Property Settings", "enable_access_code_portal"):
        frappe.throw(_("Access-code sign in is not enabled. Please use the tenant portal login."),
                     frappe.PermissionError)


def _normalize_mobile(mobile):
    return cstr(mobile).strip().replace(" ", "").replace("-", "")


# ---------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------

@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=900)
def tenant_portal_login(mobile, access_code):
    """Validate mobile + access code, issue an opaque session token."""
    _ensure_enabled()
    if not mobile or not access_code:
        frappe.throw(_("Mobile number and access code are required"), frappe.AuthenticationError)

    tenant_name = frappe.db.get_value("Tenant", {"mobile": _normalize_mobile(mobile), "disabled": 0},
                                      "name") or \
        frappe.db.get_value("Tenant", {"mobile": cstr(mobile).strip(), "disabled": 0}, "name")
    tenant_doc = frappe.get_doc("Tenant", tenant_name) if tenant_name else None
    stored_code = tenant_doc.get_password("portal_access_code", raise_exception=False) if tenant_doc else None

    # Same error for "no such tenant" and "wrong code" - don't leak which one
    if not (stored_code and hmac.compare_digest(cstr(stored_code), cstr(access_code))):
        frappe.throw(_("Invalid mobile number or access code"), frappe.AuthenticationError)
    if not tenant_doc.enable_portal:
        frappe.throw(_("Portal access is disabled for this account. Contact your property manager."))

    token = secrets.token_urlsafe(32)
    expiry = now_datetime() + timedelta(days=SESSION_LIFETIME_DAYS)
    frappe.get_doc({
        "doctype": "Tenant Portal Session",
        "tenant": tenant_name,
        "token": _hash(token),
        "expiry": expiry,
        "created_on": now_datetime(),
    }).insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "token": token,
        "tenant": tenant_name,
        "tenant_name": tenant_doc.get("tenant_name") or tenant_name,
        "expiry": str(expiry),
    }


@frappe.whitelist(allow_guest=True, methods=["POST"])
def tenant_portal_logout(token):
    frappe.db.delete("Tenant Portal Session", {"token": _hash(token)})
    frappe.db.commit()
    return {"success": True}


def resolve_tenant_from_token(token):
    """Call at the top of every tenant-facing endpoint. Returns tenant name or throws."""
    _ensure_enabled()
    if not token:
        frappe.throw(_("Missing session token"), frappe.AuthenticationError)

    session = frappe.db.get_value(
        "Tenant Portal Session", {"token": _hash(token)}, ["name", "tenant", "expiry"], as_dict=True
    )
    if not session:
        frappe.throw(_("Invalid or expired session. Please log in again."), frappe.AuthenticationError)

    if session.expiry < now_datetime():
        frappe.db.delete("Tenant Portal Session", {"name": session.name})
        frappe.db.commit()
        frappe.throw(_("Session expired. Please log in again."), frappe.AuthenticationError)
    if frappe.db.get_value("Tenant", session.tenant, "disabled"):
        frappe.throw(_("Portal access is disabled for this account."), frappe.AuthenticationError)

    frappe.db.set_value("Tenant Portal Session", session.name, "last_used_on", now_datetime(),
                        update_modified=False)
    return session.tenant


# ---------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def tenant_portal_dashboard(token):
    tenant = resolve_tenant_from_token(token)

    leases = frappe.get_all(
        "Lease Contract",
        filters={"tenant": tenant, "status": ["in", ["Active", "active"]]},
        fields=["name", "unit", "property", "start_date", "end_date"],
    )

    lease_names = [l.name for l in leases]
    next_due = None
    total_outstanding = 0

    if lease_names:
        schedules = frappe.get_all(
            "Rent Schedule", filters={"lease_contract": ["in", lease_names]}, fields=["name"]
        )
        schedule_names = [s.name for s in schedules]

        if schedule_names:
            installments = frappe.get_all(
                "Rent Installment",
                filters={"parent": ["in", schedule_names], "status": ["!=", "Paid"]},
                fields=["name", "due_date", "amount", "paid_amount", "outstanding_amount", "status"],
                order_by="due_date asc",
            )
            if installments:
                next_due = installments[0]
                total_outstanding = sum(flt(i.outstanding_amount) for i in installments)

    open_maintenance = frappe.db.count(
        "Maintenance Request",
        {"tenant": tenant, "status": ["not in", ["Completed", "Rejected", "Cancelled"]]},
    )

    return {
        "leases": leases,
        "next_due_installment": next_due,
        "total_outstanding": total_outstanding,
        "open_maintenance_requests": open_maintenance,
    }


# ---------------------------------------------------------------------
# My Lease
# ---------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def tenant_portal_lease(token):
    tenant = resolve_tenant_from_token(token)

    leases = frappe.get_all(
        "Lease Contract",
        filters={"tenant": tenant},
        fields=[
            "name", "title", "unit", "property", "owner_ref", "company",
            "start_date", "end_date", "duration_months", "status",
            "total_contract_value", "payment_frequency",
            "security_deposit_amount", "rent_schedule",
        ],
        order_by="start_date desc",
    )
    return {"leases": leases}


# ---------------------------------------------------------------------
# Payments / Installments
# ---------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def tenant_portal_installments(token):
    tenant = resolve_tenant_from_token(token)

    leases = frappe.get_all("Lease Contract", filters={"tenant": tenant}, fields=["name"])
    lease_names = [l.name for l in leases]
    if not lease_names:
        return {"installments": []}

    schedules = frappe.get_all(
        "Rent Schedule", filters={"lease_contract": ["in", lease_names]}, fields=["name", "lease_contract"]
    )
    schedule_names = [s.name for s in schedules]
    if not schedule_names:
        return {"installments": []}

    installments = frappe.get_all(
        "Rent Installment",
        filters={"parent": ["in", schedule_names]},
        fields=[
            "name", "parent", "installment_no", "due_date", "amount",
            "paid_amount", "outstanding_amount", "status", "sales_invoice", "pdc",
        ],
        order_by="due_date asc",
    )
    return {"installments": installments}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def tenant_portal_pay_installment(token, installment_name=None, amount=None, mode_of_payment=None,
                                  remarks=None):
    """Kept for API compatibility. Tenants cannot post payments against their own rent:
    the leasing team records receipts (or an online payment gateway confirms them)."""
    resolve_tenant_from_token(token)
    frappe.throw(_("Online rent payment is not available here. Please pay through your property "
                   "manager; your installment will update once the payment is recorded."),
                 frappe.PermissionError)


# ---------------------------------------------------------------------
# Cheque Schedule (PDCs)
# ---------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def tenant_portal_pdcs(token):
    tenant = resolve_tenant_from_token(token)

    pdcs = frappe.get_all(
        "Post Dated Cheque",
        filters={"tenant": tenant},
        fields=[
            "name", "cheque_no", "bank", "cheque_date", "amount",
            "status", "deposit_date", "clearance_date", "lease_contract",
        ],
        order_by="cheque_date asc",
    )
    return {"cheques": pdcs}


# ---------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------
# Matches the real Maintenance Request schema: linked via `unit` (not
# lease_contract — that field doesn't exist on this doctype), `property`
# is auto-fetched from unit, `tenant` is set here on portal-raised
# requests, category options are "\nPlumbing\nElectrical\nAC\nCivil\n
# Appliances\nPest Control\nOther", priority is Low/Medium/High/Emergency,
# status is Open/In Progress/On Hold/Completed/Rejected/Cancelled.
# Resolution (maintenance_job, resolution_notes) is staff-only — never
# exposed for tenant write access.

@frappe.whitelist(allow_guest=True)
def tenant_portal_maintenance_list(token):
    tenant = resolve_tenant_from_token(token)

    requests = frappe.get_all(
        "Maintenance Request",
        filters={"tenant": tenant},
        fields=[
            "name", "unit", "property", "category", "priority",
            "description", "status", "maintenance_job", "resolution_notes",
            "creation", "modified",
        ],
        order_by="creation desc",
    )
    return {"requests": requests}


def _tenant_units(tenant):
    """Units the tenant currently holds an active lease on."""
    return frappe.get_all(
        "Lease Contract",
        filters={"tenant": tenant, "status": ["in", ["Active", "active"]]},
        pluck="unit",
    )


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=3600)
def tenant_portal_create_maintenance_request(
    token, category, description, priority="Medium",
    unit=None, photo_1=None, photo_2=None
):
    tenant = resolve_tenant_from_token(token)
    tenant_units = _tenant_units(tenant)

    if not tenant_units:
        frappe.throw("No active lease found for this account")

    if not unit:
        unit = tenant_units[0]
    elif unit not in tenant_units:
        frappe.throw("Not authorized to raise a request against this unit", frappe.PermissionError)

    doc = frappe.get_doc({
        "doctype": "Maintenance Request",
        "unit": unit,
        "tenant": tenant,
        "category": category,
        "priority": priority,
        "description": description,
        "photo_1": photo_1,
        "photo_2": photo_2,
        "status": "Open",
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name}


@frappe.whitelist(allow_guest=True)
def tenant_portal_units(token):
    """Helper for the New Request form — units the tenant can raise a request against."""
    tenant = resolve_tenant_from_token(token)
    units = _tenant_units(tenant)
    return {"units": units}


# ---------------------------------------------------------------------
# My Documents
# ---------------------------------------------------------------------
# NOTE: assumes documents are Frappe File attachments on Lease Contract.
# If there's a dedicated "Tenant Document" doctype instead, swap the
# frappe.get_all("File", ...) block below to query that doctype.

@frappe.whitelist(allow_guest=True)
def tenant_portal_documents(token):
    tenant = resolve_tenant_from_token(token)

    leases = frappe.get_all("Lease Contract", filters={"tenant": tenant}, fields=["name"])
    lease_names = [l.name for l in leases]
    if not lease_names:
        return {"documents": []}

    files = frappe.get_all(
        "File",
        filters={"attached_to_doctype": "Lease Contract", "attached_to_name": ["in", lease_names]},
        fields=["name", "file_name", "file_url", "attached_to_name", "creation"],
        order_by="creation desc",
    )
    return {"documents": files}
