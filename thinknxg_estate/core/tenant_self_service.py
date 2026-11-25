"""
Tenant Self-Service API (/tenant-self-service).

One API for the premium tenant portal. It serves two sign-in modes with the same checks:

  * website account  - a Frappe session whose user is linked from Tenant.portal_user
  * access code      - mobile number + access code (core.tenant_portal_api), the opaque
                       session token is sent in the `X-Tenant-Token` header (never in a URL)

Security model
  * The tenant is ALWAYS derived from the authenticated session/token on the server. No tenant,
    customer or party id is accepted from the browser.
  * Lease, invoice, payment-entry, inspection, request and file identifiers sent by the
    browser are only ever used as lookups INSIDE the set of records that belong to that tenant;
    anything else raises PermissionError.
  * Private files are served only through `download`, which checks the file against the set of
    files that belong to the tenant. File paths from the browser are never trusted for writes.
  * Tenants cannot change approved lease terms or mark anything paid; they raise Tenant Service
    Requests for management approval. Money is read-only.
"""

import json
import re

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, cstr, flt, getdate, now_datetime, nowdate, strip_html

from thinknxg_estate.core.tenant_portal_api import resolve_tenant_from_token

TOKEN_HEADER = "X-Tenant-Token"
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
ALLOWED_UPLOADS = {
    "jpg": (b"\xff\xd8\xff",), "jpeg": (b"\xff\xd8\xff",), "png": (b"\x89PNG",),
    "webp": (b"RIFF",), "pdf": (b"%PDF",),
}
OPEN_MAINT = ("Open", "In Progress", "On Hold")
REQUEST_TYPES = [
    "Renewal Request", "Extension Request", "Termination Request", "Move-out Inspection Request",
    "Damage Report", "Key / Access Card Request", "Parking Request", "Address Change",
    "Occupant Update", "Facility Access", "Profile Correction", "General Enquiry",
]
NEEDS_LEASE = {"Renewal Request", "Extension Request", "Termination Request",
               "Move-out Inspection Request"}
NEEDS_DATE = {"Extension Request", "Termination Request", "Move-out Inspection Request"}
PORTAL_UPLOAD = "portal_upload"      # staged, not yet attached to a request
PORTAL_DOCUMENT = "portal_document"  # uploaded to the tenant's own document centre
TENANT_NOTE = "[Tenant] "


# --------------------------------------------------------------------------------------
# Identity
# --------------------------------------------------------------------------------------

def _tenant():
    """Resolve the calling tenant from the token header or the website session."""
    token = frappe.get_request_header(TOKEN_HEADER)
    if token:
        return resolve_tenant_from_token(token)
    if frappe.session.user == "Guest":
        frappe.throw(_("Please sign in to continue."), frappe.AuthenticationError)
    from thinknxg_estate.estate_leasing.doctype.tenant.tenant import get_tenant_for_user
    tenant = get_tenant_for_user()
    if not tenant:
        frappe.throw(_("No tenant profile is linked to your account. Please contact the leasing office."),
                     frappe.PermissionError)
    return tenant


def _auth_mode():
    return "access_code" if frappe.get_request_header(TOKEN_HEADER) else "account"


def _deny():
    frappe.throw(_("You do not have access to this record."), frappe.PermissionError)


def _leases(tenant):
    return frappe.get_all(
        "Lease Contract", filters={"tenant": tenant, "docstatus": 1},
        fields=["name", "title", "unit", "property", "company", "start_date", "end_date",
                "duration_months", "notice_period_days", "auto_renew", "status",
                "total_contract_value", "payment_frequency", "security_deposit_amount",
                "ejari_contract_no", "rent_schedule", "security_deposit", "terms",
                "signed_contract", "municipality_attestation"],
        order_by="start_date desc")


def _pick_lease(tenant, lease=None):
    """The lease named by the browser (verified to be the tenant's) or the most relevant one."""
    leases = _leases(tenant)
    if lease:
        for row in leases:
            if row.name == lease:
                return row, leases
        _deny()
    live = [row for row in leases if row.status in ("Active", "Expiring")]
    return (live or leases or [None])[0], leases


def _currency(lease):
    company = lease.company if lease else None
    return (frappe.get_cached_value("Company", company, "default_currency") if company else None) \
        or frappe.db.get_default("currency") or "AED"


def _installments(lease):
    schedule = lease.rent_schedule or frappe.db.get_value(
        "Rent Schedule", {"lease_contract": lease.name, "status": ["!=", "Cancelled"]}, "name")
    if not schedule:
        return []
    rows = frappe.get_all(
        "Rent Installment", filters={"parent": schedule, "parenttype": "Rent Schedule"},
        fields=["name", "installment_no", "due_date", "amount", "paid_amount", "outstanding_amount",
                "status", "sales_invoice", "pdc"], order_by="due_date asc, installment_no asc",
        parent_doctype="Rent Schedule")
    today = getdate(nowdate())
    for row in rows:
        row["effective_status"] = row.status
        if row.status not in ("Paid", "Cancelled") and flt(row.outstanding_amount) > 0 \
                and getdate(row.due_date) < today:
            row["effective_status"] = "Overdue"
        row["days_to_due"] = (getdate(row.due_date) - today).days
    return rows


def _tenant_doc_fields(tenant):
    return frappe.db.get_value(
        "Tenant", tenant, ["name", "tenant_name", "tenant_type", "nationality", "mobile", "email",
                           "whatsapp_number", "customer", "emergency_contact_name",
                           "emergency_contact_mobile", "portal_user"], as_dict=True)


def _maint_label(row, job=None):
    if row.status == "Open":
        return "Assigned" if job and (job.get("supplier") or job.get("employee")) else "Submitted"
    return row.status


# --------------------------------------------------------------------------------------
# Session / bootstrap
# --------------------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def session_info():
    """Public: tells the sign-in screen which modes are available and whether we are signed in."""
    info = {"access_code_enabled": bool(cint(frappe.db.get_single_value(
        "Property Settings", "enable_access_code_portal"))), "authenticated": False}
    try:
        tenant = _tenant()
    except (frappe.AuthenticationError, frappe.PermissionError):
        return info
    t = _tenant_doc_fields(tenant)
    info.update({"authenticated": True, "mode": _auth_mode(), "tenant": t.name,
                 "tenant_name": t.tenant_name})
    return info


@frappe.whitelist(allow_guest=True)
def bootstrap(lease=None):
    """Shell data: tenant, lease selector, contacts and counters for the nav badges."""
    tenant = _tenant()
    t = _tenant_doc_fields(tenant)
    current, leases = _pick_lease(tenant, lease)
    portal = frappe.get_cached_doc("RE Portal Settings") if frappe.db.exists("DocType", "RE Portal Settings") else None
    return {
        "tenant": {"name": t.name, "tenant_name": t.tenant_name, "email": t.email, "mobile": t.mobile},
        "mode": _auth_mode(),
        "current_lease": current.name if current else None,
        "leases": [{"name": l.name, "unit": l.unit, "property": l.property, "status": l.status,
                    "label": f"{frappe.db.get_value('Property', l.property, 'property_name') or l.property}"
                             f" - {frappe.db.get_value('Unit', l.unit, 'unit_no') or l.unit}"}
                   for l in leases],
        "contact": {"whatsapp": getattr(portal, "contact_whatsapp", None),
                    "email": getattr(portal, "contact_email", None),
                    "title": getattr(portal, "portal_title", None)},
        "currency": _currency(current),
        "counters": {
            "open_maintenance": frappe.db.count("Maintenance Request", {"tenant": tenant, "status": ["in", OPEN_MAINT]}),
            "open_requests": frappe.db.count("Tenant Service Request", {"tenant": tenant, "status": ["in", ["Open", "In Review"]]}),
        },
    }


# --------------------------------------------------------------------------------------
# Overview
# --------------------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def overview(lease=None):
    tenant = _tenant()
    cur, _all = _pick_lease(tenant, lease)
    if not cur:
        return {"has_lease": False, "tenant": _tenant_doc_fields(tenant), "announcements": _announcements(tenant)}
    today = getdate(nowdate())
    inst = _installments(cur)
    live = [i for i in inst if i.status != "Cancelled"]
    unpaid = [i for i in live if flt(i.outstanding_amount) > 0 and i.status != "Paid"]
    due_now = [i for i in unpaid if getdate(i.due_date) <= today]
    overdue = [i for i in unpaid if i.effective_status == "Overdue"]
    nxt = unpaid[0] if unpaid else None
    unit = frappe.db.get_value("Unit", cur.unit, ["unit_no", "unit_type", "floor"], as_dict=True) or {}
    prop = frappe.db.get_value("Property", cur.property, ["property_name", "city", "area"], as_dict=True) or {}
    dep = _deposit(cur)
    months = cint(cur.duration_months) or 0
    monthly = flt(cur.total_contract_value) / months if months else 0
    recent_paid = [i for i in live if i.status == "Paid"][-1:]
    maint = frappe.get_all("Maintenance Request", filters={"tenant": tenant},
                           fields=["name", "category", "priority", "status", "description", "maintenance_job", "modified", "creation"],
                           order_by="modified desc", limit=6)
    for m in maint:
        m["stage"] = _maint_label(m, _job_brief(m.maintenance_job))
    return {
        "has_lease": True,
        "currency": _currency(cur),
        "tenant": _tenant_doc_fields(tenant),
        "lease": {**{k: cur[k] for k in ("name", "status", "start_date", "end_date", "payment_frequency",
                                          "total_contract_value", "auto_renew", "notice_period_days")},
                  "unit_no": unit.get("unit_no"), "unit_type": unit.get("unit_type"),
                  "property_name": prop.get("property_name"), "city": prop.get("city"),
                  "days_left": (getdate(cur.end_date) - today).days,
                  "progress": _progress(cur.start_date, cur.end_date, today)},
        "metrics": {
            "monthly_rent": round(monthly, 2),
            "next_due": ({"amount": flt(nxt.outstanding_amount), "due_date": nxt.due_date,
                          "status": nxt.effective_status, "days": nxt.days_to_due} if nxt else None),
            "outstanding_balance": round(sum(flt(i.outstanding_amount) for i in due_now), 2),
            "overdue_amount": round(sum(flt(i.outstanding_amount) for i in overdue), 2),
            "overdue_count": len(overdue),
            "remaining_contract_balance": round(sum(flt(i.outstanding_amount) for i in unpaid), 2),
            "paid_to_date": round(sum(flt(i.paid_amount) for i in live), 2),
            "open_maintenance": frappe.db.count("Maintenance Request", {"tenant": tenant, "status": ["in", OPEN_MAINT]}),
            "deposit": dep,
        },
        "upcoming": [{"installment_no": i.installment_no, "due_date": i.due_date, "amount": i.amount,
                      "outstanding": i.outstanding_amount, "status": i.effective_status}
                     for i in live if i.status != "Paid"][:4],
        "last_paid": ({"due_date": recent_paid[0].due_date, "amount": recent_paid[0].paid_amount} if recent_paid else None),
        "maintenance": maint,
        "activity": _activity(tenant, cur, inst),
        "announcements": _announcements(tenant)[:3],
    }


def _progress(start, end, today):
    total = (getdate(end) - getdate(start)).days or 1
    return max(0, min(100, round((today - getdate(start)).days / total * 100)))


def _deposit(lease):
    if not lease.security_deposit:
        return {"amount": flt(lease.security_deposit_amount), "status": None, "held": 0, "refunded": 0, "deducted": 0}
    d = frappe.db.get_value("Security Deposit", lease.security_deposit,
                            ["amount", "status", "deduction_amount", "deduction_reason", "refunded_amount", "received_date"],
                            as_dict=True)
    if not d:
        return {"amount": flt(lease.security_deposit_amount), "status": None, "held": 0, "refunded": 0, "deducted": 0}
    held = flt(d.amount) - flt(d.deduction_amount) - flt(d.refunded_amount) if d.status in ("Held", "Partially Refunded") else 0
    return {"amount": flt(d.amount), "status": d.status, "held": max(held, 0), "refunded": flt(d.refunded_amount),
            "deducted": flt(d.deduction_amount), "deduction_reason": d.deduction_reason, "received_date": d.received_date}


def _job_brief(job):
    if not job:
        return None
    j = frappe.db.get_value("Maintenance Job", job, ["assigned_type", "employee", "supplier", "scheduled_date", "completion_date"], as_dict=True)
    if not j:
        return None
    who = None
    if j.assigned_type == "Supplier" and j.supplier:
        who = frappe.db.get_value("Supplier", j.supplier, "supplier_name") or j.supplier
    elif j.employee:
        who = frappe.db.get_value("Employee", j.employee, "employee_name") or j.employee
    return {"assigned_to": who, "supplier": j.supplier, "employee": j.employee,
            "scheduled_date": j.scheduled_date, "completion_date": j.completion_date}


def _payment_entries(tenant, lease_names=None):
    """Submitted Payment Entries that settled this tenant's rent invoices."""
    invoices = []
    for lease in (_leases(tenant) if lease_names is None else lease_names):
        for i in _installments(lease):
            if i.sales_invoice:
                invoices.append(i.sales_invoice)
    entries = set()
    if invoices:
        entries |= set(frappe.get_all("Payment Entry Reference",
                                      filters={"reference_doctype": "Sales Invoice", "reference_name": ["in", invoices]},
                                      pluck="parent"))
    if not entries:
        return []
    return frappe.get_all("Payment Entry", filters={"name": ["in", list(entries)], "docstatus": 1},
                          fields=["name", "posting_date", "paid_amount", "mode_of_payment", "reference_no",
                                  "reference_date", "payment_type"], order_by="posting_date desc")


def _activity(tenant, lease, inst):
    events = []
    for pe in _payment_entries(tenant, [lease])[:6]:
        events.append({"kind": "payment", "when": cstr(pe.posting_date), "title": _("Payment received"),
                       "detail": f"{flt(pe.paid_amount):,.2f}", "tone": "good"})
    for m in frappe.get_all("Maintenance Request", filters={"tenant": tenant}, fields=["name", "category", "status", "modified"], limit=5, order_by="modified desc"):
        events.append({"kind": "maintenance", "when": cstr(m.modified)[:10], "title": f"{m.category or _('Maintenance')} - {m.status}", "detail": m.name, "tone": "info"})
    for r in frappe.get_all("Tenant Service Request", filters={"tenant": tenant}, fields=["name", "request_type", "status", "modified"], limit=5, order_by="modified desc"):
        events.append({"kind": "request", "when": cstr(r.modified)[:10], "title": f"{r.request_type} - {r.status}", "detail": r.name, "tone": "info"})
    for a in _announcements(tenant)[:3]:
        events.append({"kind": "announcement", "when": cstr(a.publish_from or a.creation)[:10], "title": a.title, "detail": a.category, "tone": "neutral"})
    events.sort(key=lambda e: e["when"], reverse=True)
    return events[:10]


def _announcements(tenant):
    today = nowdate()
    props = set(frappe.get_all("Lease Contract", filters={"tenant": tenant, "docstatus": 1}, pluck="property"))
    rows = frappe.get_all("Tenant Announcement", filters={"is_published": 1},
                          fields=["name", "title", "category", "property", "body", "publish_from", "publish_until", "creation"],
                          order_by="creation desc", limit=50)
    out = []
    for r in rows:
        if r.publish_from and cstr(r.publish_from) > today:
            continue
        if r.publish_until and cstr(r.publish_until) < today:
            continue
        if r.property and r.property not in props:
            continue
        out.append(r)
    return out


@frappe.whitelist(allow_guest=True)
def announcements():
    tenant = _tenant()
    rows = _announcements(tenant)
    for r in rows:
        r["body"] = frappe.utils.sanitize_html(r.body or "")
    return rows


# --------------------------------------------------------------------------------------
# My property / lease
# --------------------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def my_property(lease=None):
    tenant = _tenant()
    cur, _all = _pick_lease(tenant, lease)
    if not cur:
        return {"has_lease": False}
    unit = frappe.db.get_value("Unit", cur.unit, ["name", "unit_no", "unit_title", "unit_type", "floor", "usage", "area_sqm",
                                                  "bedrooms", "bathrooms", "furnishing", "parking_slots"], as_dict=True)
    prop = frappe.db.get_value("Property", cur.property, ["name", "property_name", "property_type", "city", "area",
                                                          "address_line", "country", "latitude", "longitude", "cover_image",
                                                          "no_of_floors"], as_dict=True)
    amenities = frappe.get_all("Property Amenity", filters={"parent": cur.property, "parenttype": "Property"},
                               pluck="amenity", parent_doctype="Property")
    photos = frappe.get_all("Property Photo", filters={"parent": cur.property, "parenttype": "Property"},
                            fields=["image", "unit", "caption", "is_cover"], parent_doctype="Property")
    photos = [p for p in photos if p.image and (not p.unit or p.unit == cur.unit)][:12]
    utilities = frappe.get_all("Utility Account", filters={"unit": cur.unit},
                               fields=["utility_type", "provider", "account_number", "meter_number"])
    for u in utilities:
        n = cstr(u.account_number)
        u["account_number"] = ("*" * max(len(n) - 4, 0)) + n[-4:]
    portal = frappe.get_cached_doc("RE Portal Settings") if frappe.db.exists("DocType", "RE Portal Settings") else None
    return {"has_lease": True, "unit": unit, "property": prop, "amenities": amenities, "photos": photos,
            "utilities": utilities,
            "management": {"whatsapp": getattr(portal, "contact_whatsapp", None), "email": getattr(portal, "contact_email", None),
                           "name": getattr(portal, "portal_title", None)}}


@frappe.whitelist(allow_guest=True)
def lease_detail(lease=None):
    tenant = _tenant()
    cur, all_leases = _pick_lease(tenant, lease)
    if not cur:
        return {"has_lease": False}
    today = getdate(nowdate())
    charges = frappe.get_all("Lease Charge", filters={"parent": cur.name, "parenttype": "Lease Contract"},
                             fields=["charge_type", "description", "amount"], parent_doctype="Lease Contract")
    docs = []
    for field, label in (("signed_contract", "Signed lease contract"), ("municipality_attestation", "Municipality attestation")):
        if cur.get(field):
            docs.append({"title": label, "url": cur.get(field)})
    requests = frappe.get_all("Tenant Service Request",
                              filters={"tenant": tenant, "lease_contract": cur.name,
                                       "request_type": ["in", ["Renewal Request", "Extension Request", "Termination Request"]]},
                              fields=["name", "request_type", "status", "requested_date", "subject", "management_response", "creation"],
                              order_by="creation desc")
    notice = cint(cur.notice_period_days)
    end = getdate(cur.end_date)
    return {"has_lease": True, "currency": _currency(cur), "lease": {k: cur[k] for k in cur if k not in ("terms",)},
            "terms": strip_html(cur.terms or "")[:4000], "charges": charges, "documents": docs, "requests": requests,
            "deposit": _deposit(cur), "days_left": (end - today).days,
            "renewal_window_open": (end - today).days <= max(notice, 90) and cur.status in ("Active", "Expiring"),
            "history": [{"name": l.name, "start_date": l.start_date, "end_date": l.end_date, "status": l.status,
                         "unit": l.unit, "total_contract_value": l.total_contract_value} for l in all_leases]}


# --------------------------------------------------------------------------------------
# Rent & payments
# --------------------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def payments(lease=None):
    tenant = _tenant()
    cur, _all = _pick_lease(tenant, lease)
    if not cur:
        return {"has_lease": False}
    inst = _installments(cur)
    live = [i for i in inst if i.status != "Cancelled"]
    unpaid = [i for i in live if flt(i.outstanding_amount) > 0 and i.status != "Paid"]
    today = getdate(nowdate())
    invoices = {}
    for i in live:
        if i.sales_invoice:
            inv = frappe.db.get_value("Sales Invoice", i.sales_invoice,
                                      ["name", "posting_date", "due_date", "grand_total", "outstanding_amount", "status", "docstatus"], as_dict=True)
            if inv and inv.docstatus == 1:
                invoices[i.sales_invoice] = inv
    for i in inst:
        i["invoice_available"] = i.sales_invoice in invoices
        i["pdc_no"] = frappe.db.get_value("Post Dated Cheque", i.pdc, "cheque_no") if i.pdc else None
    pes = _payment_entries(tenant, [cur])
    customer = frappe.db.get_value("Tenant", tenant, "customer")
    credits = frappe.get_all("Rent Credit Balance", filters={"lease_contract": cur.name, "status": ["!=", "Fully Used"]},
                             fields=["name", "amount", "amount_used", "status", "creation"]) if cur else []
    cheques = frappe.get_all("Post Dated Cheque", filters={"tenant": tenant, "lease_contract": cur.name, "docstatus": ["<", 2]},
                             fields=["name", "cheque_no", "bank", "cheque_date", "amount", "status", "deposit_date", "clearance_date"],
                             order_by="cheque_date asc")
    return {
        "has_lease": True, "currency": _currency(cur), "lease": cur.name,
        "summary": {
            "total": round(sum(flt(i.amount) for i in live), 2),
            "paid": round(sum(flt(i.paid_amount) for i in live), 2),
            "outstanding_due": round(sum(flt(i.outstanding_amount) for i in unpaid if getdate(i.due_date) <= today), 2),
            "overdue": round(sum(flt(i.outstanding_amount) for i in unpaid if i.effective_status == "Overdue"), 2),
            "upcoming": round(sum(flt(i.outstanding_amount) for i in unpaid if getdate(i.due_date) > today), 2),
            "credit_balance": round(sum(flt(c.amount) - flt(c.amount_used) for c in credits), 2),
        },
        "installments": inst, "payments": pes, "cheques": cheques, "deposit": _deposit(cur),
        "credits": credits, "customer": bool(customer),
        "instructions": _payment_instructions(cur),
    }


def _payment_instructions(lease):
    """Bank details come from the company's default bank account; no provider is invented."""
    acct = frappe.db.get_value("Bank Account", {"company": lease.company, "is_company_account": 1, "is_default": 1},
                               ["account_name", "bank", "iban", "branch_code"], as_dict=True) if lease.company else None
    note = _("Online card payment is not configured. Pay by bank transfer or cheque{0}; "
             "your balance updates once the leasing team records the payment.").format(
        _(" using the details above") if acct else _(" - ask your property manager for the payment details"))
    return {"bank": acct, "online_payment": False, "note": note}


def _own_invoice(tenant, name):
    for lease in _leases(tenant):
        for i in _installments(lease):
            if i.sales_invoice == name:
                if frappe.db.get_value("Sales Invoice", name, "docstatus") == 1:
                    return True
    return False


def _own_payment_entry(tenant, name):
    return any(pe.name == name for pe in _payment_entries(tenant))


def _own_inspection(tenant, name):
    lease = frappe.db.get_value("Move In Out Inspection", name, "lease_contract")
    return bool(lease) and frappe.db.get_value("Lease Contract", lease, "tenant") == tenant


def _own_files(tenant):
    """URLs of every file that belongs to the tenant (the allow-list for `download`)."""
    urls = set()
    leases = _leases(tenant)
    for l in leases:
        for f in (l.signed_contract, l.municipality_attestation):
            if f:
                urls.add(f)
        props = frappe.db.get_value("Property", l.property, "cover_image") if l.property else None
        if props:
            urls.add(props)
        for p in frappe.get_all("Property Photo", filters={"parent": l.property, "parenttype": "Property"}, pluck="image", parent_doctype="Property"):
            if p:
                urls.add(p)
        for insp in frappe.get_all("Move In Out Inspection", filters={"lease_contract": l.name, "docstatus": ["<", 2]}, pluck="name"):
            doc = frappe.get_doc("Move In Out Inspection", insp)
            for it in doc.get("items") or []:
                if it.photo:
                    urls.add(it.photo)
            if doc.tenant_signature:
                urls.add(doc.tenant_signature)
    for k in frappe.get_doc("Tenant", tenant).get("kyc_documents") or []:
        if k.attachment:
            urls.add(k.attachment)
    for m in frappe.get_all("Maintenance Request", filters={"tenant": tenant}, fields=["name", "photo_1", "photo_2"]):
        for f in (m.photo_1, m.photo_2):
            if f:
                urls.add(f)
        urls |= set(frappe.get_all("File", filters={"attached_to_doctype": "Maintenance Request", "attached_to_name": m.name}, pluck="file_url"))
    for r in frappe.get_all("Tenant Service Request", filters={"tenant": tenant}, pluck="name"):
        urls |= set(frappe.get_all("File", filters={"attached_to_doctype": "Tenant Service Request", "attached_to_name": r}, pluck="file_url"))
    urls |= set(frappe.get_all("File", filters={"attached_to_doctype": "Tenant", "attached_to_name": tenant,
                                                "attached_to_field": ["in", [PORTAL_UPLOAD, PORTAL_DOCUMENT]]}, pluck="file_url"))
    return {u for u in urls if u}


def _pdf(doctype, name):
    """Render a record the caller has already been verified to own.

    Access-code sessions run as Guest, which has no print permission on finance
    documents, so the render itself runs with the print check relaxed. Callers
    must verify ownership first (see _own_invoice and friends).
    """
    from frappe.utils.pdf import get_pdf
    prev = frappe.session.user
    try:
        frappe.set_user("Administrator")
        html = frappe.get_print(doctype, name, doc=frappe.get_doc(doctype, name), no_letterhead=0)
    finally:
        frappe.set_user(prev)
    # Never let the renderer fetch third-party resources (web fonts etc.): slower,
    # and a failed fetch aborts the whole PDF.
    html = re.sub(r"<link[^>]+href=[\"']https?://[^>]*>", "", html)
    html = re.sub(r"@import\s+url\([^)]*https?://[^)]*\)\s*;?", "", html)
    return get_pdf(html)


@frappe.whitelist(allow_guest=True)
def download(kind, ref):
    """Secure gateway for PDFs and private files. kind: invoice | receipt | inspection | file."""
    tenant = _tenant()
    kind = cstr(kind)
    ref = cstr(ref)
    if kind == "invoice" and _own_invoice(tenant, ref):
        content, name, mime = _pdf("Sales Invoice", ref), f"{ref}.pdf", "application/pdf"
    elif kind == "receipt" and _own_payment_entry(tenant, ref):
        content, name, mime = _pdf("Payment Entry", ref), f"{ref}.pdf", "application/pdf"
    elif kind == "inspection" and _own_inspection(tenant, ref):
        content, name, mime = _pdf("Move In Out Inspection", ref), f"{ref}.pdf", "application/pdf"
    elif kind == "file":
        if ref not in _own_files(tenant):
            _deny()
        fdoc = frappe.get_doc("File", {"file_url": ref}) if frappe.db.exists("File", {"file_url": ref}) else None
        if not fdoc or not fdoc.is_folder == 0:
            frappe.throw(_("File not found."), frappe.DoesNotExistError)
        content, name = fdoc.get_content(), fdoc.file_name
        if isinstance(content, str):
            content = content.encode()
        ext = cstr(name).rsplit(".", 1)[-1].lower()
        mime = {"pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "webp": "image/webp"}.get(ext, "application/octet-stream")
    else:
        _deny()
    frappe.local.response.filename = name
    frappe.local.response.filecontent = content
    frappe.local.response.type = "download"
    frappe.local.response.content_type = mime


# --------------------------------------------------------------------------------------
# Maintenance
# --------------------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def maintenance(lease=None):
    tenant = _tenant()
    rows = frappe.get_all(
        "Maintenance Request", filters={"tenant": tenant},
        fields=["name", "unit", "property", "category", "priority", "status", "description", "photo_1", "photo_2",
                "maintenance_job", "resolution_notes", "creation", "modified"], order_by="creation desc")
    out = []
    for r in rows:
        job = _job_brief(r.maintenance_job)
        notes = frappe.get_all("Comment", filters={"reference_doctype": "Maintenance Request", "reference_name": r.name,
                                                    "comment_type": "Comment", "content": ["like", f"%{TENANT_NOTE}%"]},
                               fields=["content", "creation"], order_by="creation asc")
        timeline = [{"when": cstr(r.creation), "title": _("Request submitted")}]
        if job and job.get("scheduled_date"):
            timeline.append({"when": cstr(job["scheduled_date"]), "title": _("Visit scheduled") + (f" - {job['assigned_to']}" if job.get("assigned_to") else "")})
        if r.status == "Completed":
            timeline.append({"when": cstr((job or {}).get("completion_date") or r.modified), "title": _("Work completed")})
        if r.status in ("Rejected", "Cancelled", "On Hold"):
            timeline.append({"when": cstr(r.modified), "title": r.status})
        for n in notes:
            timeline.append({"when": cstr(n.creation), "title": strip_html(n.content).replace(TENANT_NOTE, "", 1)})
        attachments = frappe.get_all("File", filters={"attached_to_doctype": "Maintenance Request", "attached_to_name": r.name},
                                     fields=["file_name", "file_url"])
        photos = [u for u in (r.photo_1, r.photo_2) if u] + [a.file_url for a in attachments]
        out.append({**r, "stage": _maint_label(r, job), "job": job, "timeline": timeline, "photos": photos,
                    "resolution_notes": r.resolution_notes if r.status in ("Completed", "Rejected") else None})
    return {"requests": out, "categories": ["Plumbing", "Electrical", "AC", "Civil", "Appliances", "Pest Control", "Other"],
            "priorities": ["Low", "Medium", "High", "Emergency"], "units": _tenant_units(tenant)}


def _tenant_units(tenant):
    rows = frappe.get_all("Lease Contract", filters={"tenant": tenant, "docstatus": 1, "status": ["in", ["Active", "Expiring"]]},
                          fields=["unit", "property"])
    return [{"unit": r.unit, "label": f"{frappe.db.get_value('Property', r.property, 'property_name') or r.property}"
                                      f" - {frappe.db.get_value('Unit', r.unit, 'unit_no') or r.unit}"} for r in rows]


def _clean(text, limit):
    return strip_html(cstr(text)).strip()[:limit]


def _claim_files(tenant, file_ids, doctype, docname):
    """Move staged uploads (file ids returned by `upload`) onto a newly created record."""
    claimed = []
    for fid in (file_ids or [])[:6]:
        f = frappe.db.get_value("File", fid, ["name", "attached_to_doctype", "attached_to_name", "attached_to_field", "file_url"], as_dict=True)
        if not f or f.attached_to_doctype != "Tenant" or f.attached_to_name != tenant or f.attached_to_field != PORTAL_UPLOAD:
            _deny()
        frappe.db.set_value("File", f.name, {"attached_to_doctype": doctype, "attached_to_name": docname, "attached_to_field": None})
        claimed.append(f.file_url)
    return claimed


def _parse_ids(value):
    if isinstance(value, str):
        try:
            value = json.loads(value or "[]")
        except ValueError:
            value = []
    return [cstr(v) for v in (value or [])]


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=3600)
def create_maintenance(category, description, priority="Medium", unit=None, preferred_access=None, file_ids=None):
    tenant = _tenant()
    units = _tenant_units(tenant)
    if not units:
        frappe.throw(_("Maintenance requests need an active lease."))
    allowed = {u["unit"] for u in units}
    unit = unit or units[0]["unit"]
    if unit not in allowed:
        _deny()
    if category not in ("Plumbing", "Electrical", "AC", "Civil", "Appliances", "Pest Control", "Other"):
        frappe.throw(_("Please choose an issue category."))
    desc = _clean(description, 2000)
    if len(desc) < 10:
        frappe.throw(_("Please describe the problem in a little more detail."))
    if preferred_access:
        desc += "\n\n" + _("Preferred access: {0}").format(_clean(preferred_access, 200))
    doc = frappe.get_doc({"doctype": "Maintenance Request", "unit": unit, "tenant": tenant, "category": category,
                          "priority": priority if priority in ("Low", "Medium", "High", "Emergency") else "Medium",
                          "description": desc, "status": "Open"})
    doc.insert(ignore_permissions=True)
    urls = _claim_files(tenant, _parse_ids(file_ids), "Maintenance Request", doc.name)
    for field, url in zip(("photo_1", "photo_2"), [u for u in urls if u.split(".")[-1].lower() in ("jpg", "jpeg", "png", "webp")]):
        frappe.db.set_value("Maintenance Request", doc.name, field, url, update_modified=False)
    _notify_staff("Maintenance Request", doc.name, _("New maintenance request {0} from {1}").format(doc.name, tenant), desc)
    frappe.db.commit()
    return {"name": doc.name}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=30, seconds=3600)
def maintenance_feedback(name, action, note=None):
    """Tenant confirms the work is done or asks for more help. Recorded on the request and
    sent to the leasing team; status stays under staff control."""
    tenant = _tenant()
    row = frappe.db.get_value("Maintenance Request", name, ["tenant", "status"], as_dict=True)
    if not row or row.tenant != tenant:
        _deny()
    if action not in ("confirm", "reopen", "note"):
        frappe.throw(_("Unknown action."))
    if action in ("confirm", "reopen") and row.status != "Completed":
        frappe.throw(_("This request has not been marked completed yet."))
    label = {"confirm": _("Tenant confirmed the work is complete"), "reopen": _("Tenant needs further assistance"),
             "note": _("Tenant note")}[action]
    text = f"{TENANT_NOTE}{label}" + (f": {_clean(note, 500)}" if note else "")
    frappe.get_doc("Maintenance Request", name).add_comment("Comment", text)
    if action != "confirm":
        _notify_staff("Maintenance Request", name, f"{label} ({name})", text)
    frappe.db.commit()
    return {"ok": True}


# --------------------------------------------------------------------------------------
# Uploads and documents
# --------------------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=40, seconds=3600)
def upload(purpose="attachment"):
    """Stage one file (multipart field `file`). Returns a file id that create_* endpoints accept.
    purpose='document' stores it straight in the tenant's own document centre."""
    tenant = _tenant()
    f = frappe.request.files.get("file") if frappe.request else None
    if not f or not f.filename:
        frappe.throw(_("No file received."))
    content = f.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        frappe.throw(_("Files can be at most 8 MB."))
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in ALLOWED_UPLOADS or not any(content.startswith(sig) for sig in ALLOWED_UPLOADS[ext]):
        frappe.throw(_("Only JPG, PNG, WebP or PDF files are accepted."))
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", f.filename)[-80:] or f"upload.{ext}"
    field = PORTAL_DOCUMENT if purpose == "document" else PORTAL_UPLOAD
    doc = frappe.get_doc({"doctype": "File", "file_name": safe, "content": content, "is_private": 1,
                          "attached_to_doctype": "Tenant", "attached_to_name": tenant, "attached_to_field": field})
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"id": doc.name, "file_name": doc.file_name, "url": doc.file_url}


@frappe.whitelist(allow_guest=True)
def documents(lease=None):
    tenant = _tenant()
    cur, all_leases = _pick_lease(tenant, lease)
    docs = []
    for l in all_leases:
        for field, label in (("signed_contract", _("Signed lease contract")), ("municipality_attestation", _("Municipality attestation"))):
            if l.get(field):
                docs.append({"category": "Lease agreements", "title": f"{label} - {l.name}", "kind": "file", "ref": l.get(field),
                             "date": cstr(l.start_date), "expiry": None})
        for i in _installments(l):
            if i.sales_invoice and frappe.db.get_value("Sales Invoice", i.sales_invoice, "docstatus") == 1:
                docs.append({"category": "Rent invoices", "title": f"{i.sales_invoice} - {_('instalment')} {i.installment_no}",
                             "kind": "invoice", "ref": i.sales_invoice, "date": cstr(i.due_date), "expiry": None})
        for insp in frappe.get_all("Move In Out Inspection", filters={"lease_contract": l.name, "docstatus": 1},
                                   fields=["name", "inspection_type", "inspection_date"]):
            docs.append({"category": "Inspection reports", "title": f"{insp.inspection_type} {_('inspection')} - {insp.name}",
                         "kind": "inspection", "ref": insp.name, "date": cstr(insp.inspection_date), "expiry": None})
    for pe in _payment_entries(tenant):
        docs.append({"category": "Payment receipts", "title": f"{_('Receipt')} {pe.name} - {flt(pe.paid_amount):,.2f}",
                     "kind": "receipt", "ref": pe.name, "date": cstr(pe.posting_date), "expiry": None})
    t = frappe.get_doc("Tenant", tenant)
    today = getdate(nowdate())
    for k in t.get("kyc_documents") or []:
        if k.attachment:
            exp = getdate(k.expiry_date) if k.expiry_date else None
            docs.append({"category": "Identity & KYC", "title": k.id_type or _("Identity document"), "kind": "file", "ref": k.attachment,
                         "date": None, "expiry": cstr(exp) if exp else None,
                         "expiry_state": ("expired" if exp and exp < today else "soon" if exp and (exp - today).days <= 60 else "valid") if exp else None})
    for f in frappe.get_all("File", filters={"attached_to_doctype": "Tenant", "attached_to_name": tenant, "attached_to_field": PORTAL_DOCUMENT},
                            fields=["file_name", "file_url", "creation"], order_by="creation desc"):
        docs.append({"category": "Other documents", "title": f.file_name, "kind": "file", "ref": f.file_url, "date": cstr(f.creation)[:10], "expiry": None})
    return {"documents": docs, "categories": ["Lease agreements", "Rent invoices", "Payment receipts", "Inspection reports",
                                                "Identity & KYC", "Other documents"]}


# --------------------------------------------------------------------------------------
# Service requests and messages
# --------------------------------------------------------------------------------------

def _request_row(r):
    r["messages"] = [{"sender_type": m.sender_type, "message": m.message, "posted_on": cstr(m.posted_on)}
                     for m in frappe.get_all("Tenant Request Message", filters={"parent": r.name, "parenttype": "Tenant Service Request"},
                                             fields=["sender_type", "message", "posted_on"], order_by="idx asc", parent_doctype="Tenant Service Request")]
    r["attachments"] = frappe.get_all("File", filters={"attached_to_doctype": "Tenant Service Request", "attached_to_name": r.name},
                                      fields=["file_name", "file_url"])
    return r


@frappe.whitelist(allow_guest=True)
def service_requests(kind="requests"):
    """kind='requests' -> everything except General Enquiry; kind='messages' -> enquiry threads."""
    tenant = _tenant()
    flt_type = ["=", "General Enquiry"] if kind == "messages" else ["!=", "General Enquiry"]
    rows = frappe.get_all("Tenant Service Request", filters={"tenant": tenant, "request_type": flt_type},
                          fields=["name", "request_type", "status", "subject", "details", "requested_date", "lease_contract",
                                  "management_response", "creation", "modified"], order_by="modified desc")
    return {"requests": [_request_row(r) for r in rows],
            "types": [t for t in REQUEST_TYPES if t != "General Enquiry"]}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=3600)
def create_service_request(request_type, subject, details=None, requested_date=None, lease=None, file_ids=None):
    tenant = _tenant()
    if request_type not in REQUEST_TYPES:
        frappe.throw(_("Unknown request type."))
    cur, _all = _pick_lease(tenant, lease)
    if request_type in NEEDS_LEASE and not cur:
        frappe.throw(_("This request needs a lease on your account."))
    subject = _clean(subject, 140) or request_type
    if request_type in NEEDS_DATE:
        if not requested_date:
            frappe.throw(_("Please choose a date."))
        d = getdate(requested_date)
        if d < getdate(nowdate()):
            frappe.throw(_("The date cannot be in the past."))
        if request_type == "Extension Request" and cur and d <= getdate(cur.end_date):
            frappe.throw(_("The new end date must be after the current lease end date ({0}).").format(cur.end_date))
    if request_type in NEEDS_LEASE and cur and frappe.db.exists(
            "Tenant Service Request", {"tenant": tenant, "lease_contract": cur.name, "request_type": request_type,
                                       "status": ["in", ["Open", "In Review"]]}):
        frappe.throw(_("You already have an open {0} for this lease.").format(request_type))
    doc = frappe.get_doc({"doctype": "Tenant Service Request", "tenant": tenant, "request_type": request_type,
                          "subject": subject, "details": _clean(details, 2000), "status": "Open",
                          "requested_date": requested_date or None,
                          "lease_contract": cur.name if cur else None, "unit": cur.unit if cur else None,
                          "property": cur.property if cur else None})
    doc.append("messages", {"sender_type": "Tenant", "message": _clean(details, 2000) or subject,
                            "posted_by": tenant, "posted_on": now_datetime()})
    doc.insert(ignore_permissions=True)
    _claim_files(tenant, _parse_ids(file_ids), "Tenant Service Request", doc.name)
    if cur and request_type in ("Renewal Request", "Extension Request", "Termination Request"):
        frappe.get_doc("Lease Contract", cur.name).add_comment("Comment", f"{request_type} from tenant ({doc.name}): {subject}")
    _notify_staff("Tenant Service Request", doc.name, f"{request_type}: {subject} ({tenant})", doc.details or "")
    frappe.db.commit()
    return {"name": doc.name}


def _own_request(tenant, name):
    if frappe.db.get_value("Tenant Service Request", name, "tenant") != tenant:
        _deny()
    return frappe.get_doc("Tenant Service Request", name)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=60, seconds=3600)
def reply_service_request(name, message):
    return _reply(_tenant(), name, message)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def cancel_service_request(name):
    tenant = _tenant()
    doc = _own_request(tenant, name)
    if doc.status != "Open":
        frappe.throw(_("Only requests that have not been picked up yet can be cancelled."))
    doc.status = "Cancelled"
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=3600)
def send_message(message, subject=None, thread=None):
    """Tenant-to-management messaging: a General Enquiry thread."""
    tenant = _tenant()
    if thread:
        return _reply(tenant, thread, message)
    return _new_enquiry(tenant, subject, message)


def _reply(tenant, thread, message):
    doc = _own_request(tenant, thread)
    if doc.status == "Cancelled":
        frappe.throw(_("This request is closed."))
    text = _clean(message, 1500)
    if not text:
        frappe.throw(_("Please type a message."))
    doc.append("messages", {"sender_type": "Tenant", "message": text, "posted_by": tenant, "posted_on": now_datetime()})
    doc.flags.ignore_permissions = True
    doc.save()
    _notify_staff("Tenant Service Request", doc.name, f"Reply from tenant on {doc.name}", text)
    frappe.db.commit()
    return {"ok": True, "name": doc.name}


def _new_enquiry(tenant, subject, message):
    text = _clean(message, 1500)
    if not text:
        frappe.throw(_("Please type a message."))
    cur, _all = _pick_lease(tenant)
    doc = frappe.get_doc({"doctype": "Tenant Service Request", "tenant": tenant, "request_type": "General Enquiry",
                          "subject": _clean(subject, 140) or text[:60], "details": text, "status": "Open",
                          "lease_contract": cur.name if cur else None, "unit": cur.unit if cur else None,
                          "property": cur.property if cur else None})
    doc.append("messages", {"sender_type": "Tenant", "message": text, "posted_by": tenant, "posted_on": now_datetime()})
    doc.insert(ignore_permissions=True)
    _notify_staff("Tenant Service Request", doc.name, f"New message from tenant {tenant}", text)
    frappe.db.commit()
    return {"ok": True, "name": doc.name}


@frappe.whitelist(allow_guest=True)
def communications():
    """Automated notifications that were sent to the tenant (WhatsApp log), newest first."""
    tenant = _tenant()
    t = _tenant_doc_fields(tenant)
    nums = {re.sub(r"\D", "", cstr(n)) for n in (t.mobile, t.whatsapp_number) if n}
    nums.discard("")
    if not nums:
        return {"notifications": []}
    rows = frappe.get_all("WhatsApp Message Log", fields=["to_number", "message", "status", "creation", "reference_doctype"],
                          order_by="creation desc", limit=200)
    out = [r for r in rows if re.sub(r"\D", "", cstr(r.to_number)) in nums or
           any(re.sub(r"\D", "", cstr(r.to_number)).endswith(n[-8:]) for n in nums)]
    return {"notifications": [{"when": cstr(r.creation), "message": r.message, "status": r.status} for r in out[:40]]}


# --------------------------------------------------------------------------------------
# Move-in / move-out
# --------------------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def inspections(lease=None):
    tenant = _tenant()
    cur, all_leases = _pick_lease(tenant, lease)
    out = []
    for l in all_leases:
        for r in frappe.get_all("Move In Out Inspection", filters={"lease_contract": l.name, "docstatus": ["<", 2]},
                                fields=["name", "inspection_type", "inspection_date", "estimated_damage_cost", "summary",
                                        "tenant_present", "tenant_signature", "docstatus", "lease_contract"], order_by="inspection_date desc"):
            doc = frappe.get_doc("Move In Out Inspection", r.name)
            ack = frappe.get_all("Comment", filters={"reference_doctype": "Move In Out Inspection", "reference_name": r.name,
                                                      "comment_type": "Comment", "content": ["like", f"%{TENANT_NOTE}Acknowledged%"]},
                                 fields=["creation"], limit=1)
            out.append({**r, "items": [{"room": i.room, "item": i.item, "condition": i.condition, "photo": i.photo, "remarks": i.remarks}
                                       for i in (doc.get("items") or [])],
                        "acknowledged_on": cstr(ack[0].creation) if ack else None,
                        "currency": _currency(l)})
    requests = frappe.get_all("Tenant Service Request", filters={"tenant": tenant, "request_type": ["in", ["Move-out Inspection Request", "Damage Report", "Key / Access Card Request"]]},
                              fields=["name", "request_type", "status", "subject", "requested_date", "management_response", "creation"], order_by="creation desc")
    return {"inspections": out, "requests": requests, "deposit": _deposit(cur) if cur else None,
            "currency": _currency(cur), "lease": cur.name if cur else None, "lease_status": cur.status if cur else None}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def acknowledge_inspection(name):
    tenant = _tenant()
    if not _own_inspection(tenant, name):
        _deny()
    if frappe.db.exists("Comment", {"reference_doctype": "Move In Out Inspection", "reference_name": name,
                                    "comment_type": "Comment", "content": ["like", f"%{TENANT_NOTE}Acknowledged%"]}):
        return {"ok": True}
    frappe.get_doc("Move In Out Inspection", name).add_comment(
        "Comment", f"{TENANT_NOTE}Acknowledged by tenant {tenant} on {now_datetime():%Y-%m-%d %H:%M}")
    frappe.db.commit()
    return {"ok": True}


# --------------------------------------------------------------------------------------
# Profile
# --------------------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def profile():
    tenant = _tenant()
    t = _tenant_doc_fields(tenant)
    doc = frappe.get_doc("Tenant", tenant)
    today = getdate(nowdate())
    kyc = []
    for k in doc.get("kyc_documents") or []:
        exp = getdate(k.expiry_date) if k.expiry_date else None
        number = cstr(k.id_number)
        kyc.append({"id_type": k.id_type, "id_number": ("*" * max(len(number) - 3, 0)) + number[-3:] if number else None,
                    "expiry_date": cstr(exp) if exp else None, "has_file": bool(k.attachment),
                    "state": ("expired" if exp and exp < today else "expiring" if exp and (exp - today).days <= 60 else "valid") if exp else "no expiry"})
    sessions = frappe.get_all("Tenant Portal Session", filters={"tenant": tenant, "expiry": [">", now_datetime()]},
                              fields=["created_on", "last_used_on"], order_by="last_used_on desc")
    return {"tenant": {k: t[k] for k in ("name", "tenant_name", "tenant_type", "nationality", "mobile", "email", "whatsapp_number",
                                         "emergency_contact_name", "emergency_contact_mobile")},
            "kyc": kyc, "mode": _auth_mode(), "login_email": t.portal_user,
            "active_sessions": [{"created_on": cstr(s.created_on), "last_used_on": cstr(s.last_used_on)} for s in sessions]}


def _phone(value, label):
    v = re.sub(r"[\s-]", "", cstr(value))
    if v and not re.fullmatch(r"\+?\d{7,15}", v):
        frappe.throw(_("{0} is not a valid phone number.").format(label))
    return v


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=3600)
def update_profile(whatsapp_number=None, emergency_contact_name=None, emergency_contact_mobile=None):
    """Only contact details that do not affect sign-in or KYC can be changed directly."""
    tenant = _tenant()
    values = {"whatsapp_number": _phone(whatsapp_number, _("WhatsApp number")),
              "emergency_contact_name": _clean(emergency_contact_name, 140),
              "emergency_contact_mobile": _phone(emergency_contact_mobile, _("Emergency contact number"))}
    frappe.db.set_value("Tenant", tenant, values)
    frappe.get_doc("Tenant", tenant).add_comment("Comment", "Contact details updated by the tenant in the self-service portal")
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def sign_out_everywhere():
    """Access-code sessions only: remove every stored session for this tenant."""
    tenant = _tenant()
    frappe.db.delete("Tenant Portal Session", {"tenant": tenant})
    frappe.db.commit()
    return {"ok": True}


# --------------------------------------------------------------------------------------
# Notifications (derived from real records)
# --------------------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def notifications(lease=None):
    tenant = _tenant()
    cur, _all = _pick_lease(tenant, lease)
    items = []
    today = getdate(nowdate())
    if cur:
        for i in _installments(cur):
            if i.status in ("Paid", "Cancelled") or flt(i.outstanding_amount) <= 0:
                continue
            if i.effective_status == "Overdue":
                items.append({"tone": "bad", "when": cstr(i.due_date), "title": _("Rent overdue"),
                              "detail": f"{flt(i.outstanding_amount):,.2f} - {_('due')} {i.due_date}", "route": "payments"})
            elif i.days_to_due <= 14:
                items.append({"tone": "warn", "when": cstr(i.due_date), "title": _("Rent due soon"),
                              "detail": f"{flt(i.outstanding_amount):,.2f} - {_('due')} {i.due_date}", "route": "payments"})
        left = (getdate(cur.end_date) - today).days
        if 0 <= left <= max(cint(cur.notice_period_days), 90):
            items.append({"tone": "warn", "when": cstr(cur.end_date), "title": _("Lease ends in {0} days").format(left),
                          "detail": _("Ask for a renewal from My Lease."), "route": "lease"})
    for r in frappe.get_all("Tenant Service Request", filters={"tenant": tenant, "status": ["in", ["Approved", "Rejected", "Completed", "In Review"]]},
                            fields=["name", "request_type", "status", "modified"], order_by="modified desc", limit=5):
        items.append({"tone": "info", "when": cstr(r.modified), "title": f"{r.request_type}: {r.status}", "detail": r.name, "route": "requests"})
    for m in frappe.get_all("Maintenance Request", filters={"tenant": tenant, "status": ["in", ["In Progress", "Completed", "On Hold", "Rejected"]]},
                            fields=["name", "category", "status", "modified"], order_by="modified desc", limit=5):
        items.append({"tone": "info", "when": cstr(m.modified), "title": f"{m.category or _('Maintenance')}: {m.status}", "detail": m.name, "route": "maintenance"})
    for a in _announcements(tenant)[:3]:
        items.append({"tone": "neutral", "when": cstr(a.creation), "title": a.title, "detail": a.category, "route": "announcements"})
    items.sort(key=lambda x: x["when"], reverse=True)
    return {"items": items[:15]}


def _notify_staff(doctype, name, subject, description):
    users = set()
    for role in ("RE Manager", "Leasing Officer"):
        users |= set(frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"}, pluck="parent"))
    for user in users:
        if user in ("Administrator", "Guest") or not frappe.db.get_value("User", user, "enabled"):
            continue
        frappe.get_doc({"doctype": "Notification Log", "for_user": user, "type": "Alert", "document_type": doctype,
                        "document_name": name, "subject": subject}).insert(ignore_permissions=True)
    frappe.get_doc({"doctype": "ToDo", "reference_type": doctype, "reference_name": name,
                    "description": strip_html(cstr(description))[:500] or subject, "priority": "Medium",
                    "role": "Leasing Officer"}).insert(ignore_permissions=True)
