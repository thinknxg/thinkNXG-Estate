"""Tenant self-service APIs. Identity is always resolved from the session user;
tenant IDs are never accepted from the client."""

import frappe
from frappe import _
from frappe.utils import fmt_money, getdate, nowdate


def _require_tenant():
    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in."), frappe.PermissionError)
    from thinknxg_estate.estate_leasing.doctype.tenant.tenant import get_tenant_for_user
    tenant = get_tenant_for_user()
    if not tenant:
        frappe.throw(_("No tenant profile is linked to your account."),
                     frappe.PermissionError)
    return tenant


def _active_lease(tenant):
    return frappe.db.get_value(
        "Lease Contract",
        {"tenant": tenant, "docstatus": 1, "status": ["in", ["Active", "Expiring"]]},
        ["name", "unit", "property", "start_date", "end_date", "status",
         "total_contract_value", "payment_frequency", "rent_schedule",
         "security_deposit"],
        as_dict=True, order_by="end_date desc")


@frappe.whitelist()
def dashboard():
    tenant = _require_tenant()
    tenant_doc = frappe.db.get_value("Tenant", tenant, ["tenant_name"], as_dict=True)
    lease = _active_lease(tenant)
    out = {"tenant": tenant, "tenant_name": tenant_doc.tenant_name, "lease": lease,
           "next_installment": None, "open_requests": 0, "overdue_count": 0}
    if lease:
        out["unit_title"] = frappe.db.get_value("Unit", lease.unit, "unit_title")
        out["next_installment"] = frappe.db.get_value(
            "Rent Installment",
            {"parent": lease.rent_schedule,
             "status": ["in", ["Pending", "Invoiced", "Overdue"]]},
            ["due_date", "amount", "status"], as_dict=True, order_by="due_date asc")
        out["overdue_count"] = frappe.db.count(
            "Rent Installment", {"parent": lease.rent_schedule, "status": "Overdue"})
    out["open_requests"] = frappe.db.count(
        "Maintenance Request",
        {"tenant": tenant, "status": ["in", ["Open", "In Progress", "On Hold"]]})
    return out


@frappe.whitelist()
def installments():
    tenant = _require_tenant()
    lease = _active_lease(tenant)
    if not lease:
        return {"lease": None, "installments": []}
    rows = frappe.get_all(
        "Rent Installment",
        filters={"parent": lease.rent_schedule},
        fields=["installment_no", "due_date", "amount", "status",
                "sales_invoice", "pdc"],
        order_by="installment_no asc")
    for row in rows:
        row["invoice_pdf"] = (
            f"/api/method/frappe.utils.print_format.download_pdf?doctype=Sales%20Invoice"
            f"&name={row.sales_invoice}" if row.sales_invoice else None)
    return {"lease": lease, "installments": rows}


@frappe.whitelist()
def maintenance_list():
    tenant = _require_tenant()
    return frappe.get_all(
        "Maintenance Request", filters={"tenant": tenant},
        fields=["name", "unit", "category", "priority", "status",
                "description", "creation", "resolution_notes"],
        order_by="creation desc", page_length=50)


@frappe.whitelist()
def get_outstanding_rent(upto_date=None):
    tenant = _require_tenant()
    lease = _active_lease(tenant)
    if not lease:
        frappe.throw(_("No active lease found."))
    doc = frappe.get_doc("Lease Contract", lease.name)
    return doc.get_outstanding_rent(upto_date=upto_date)


@frappe.whitelist(methods=["POST"])
def terminate_lease(termination_date, reasons, outstanding_rent=None,
                     mode_of_payment=None, apply_charge_to_tenant=None, reason=None):
    """Tenant self-service termination. The lease is always resolved from the session
    tenant - a lease name is never accepted from the client.

    Unless Property Settings allows online termination, this records a termination
    request for the leasing team (comment + notification + ToDo) and leaves the lease
    and unit untouched, so notice periods, inspections and deposit settlement stay
    under staff control."""
    tenant = _require_tenant()
    lease = _active_lease(tenant)
    if not lease:
        frappe.throw(_("No active lease found."))
    doc = frappe.get_doc("Lease Contract", lease.name)

    if not frappe.db.get_single_value("Property Settings", "allow_tenant_self_termination"):
        note = _("Tenant requested termination on {0}. Reason: {1}. {2}").format(
            termination_date, reasons, frappe.utils.strip_html(reason or "")[:500])
        doc.add_comment("Comment", note)
        _notify_leasing_team(doc, note)
        return {"ok": True, "status": "Requested", "unit": doc.unit, "reasons": reasons}

    # Online termination is only completed here when nothing needs accounting (no credit
    # notes, no cash to move). Otherwise it is routed to staff, who post the settlement.
    from thinknxg_estate.core import lease_settlement as ls

    posting = frappe.utils.nowdate()
    settle = ls.compute_settlement(doc, termination_date, posting)
    if settle["result"] != ls.SETTLED or settle["adjustments"]:
        note = _("Tenant requested termination on {0}. Reason: {1}. A settlement of {2} {3} must be "
                 "posted by the leasing team.").format(termination_date, reasons, abs(settle["net_settlement"]),
                                                      settle["currency"])
        doc.add_comment("Comment", note)
        _notify_leasing_team(doc, note)
        return {"ok": True, "status": "Requested", "unit": doc.unit, "reasons": reasons}
    doc.flags.ignore_permissions = True
    status = doc.terminate(
        termination_date=termination_date, reasons=reasons, posting_date=posting,
        calc_token=settle["token"], reason=reason)
    return {"ok": True, "status": status, "unit": doc.unit, "reasons": reasons}


def _notify_leasing_team(lease_doc, note):
    users = set()
    for role in ("RE Manager", "Leasing Officer"):
        users |= set(frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"},
                                    pluck="parent"))
    for user in users:
        if not frappe.db.get_value("User", user, "enabled") or user in ("Administrator", "Guest"):
            continue
        frappe.get_doc({
            "doctype": "Notification Log", "for_user": user, "type": "Alert",
            "document_type": "Lease Contract", "document_name": lease_doc.name,
            "subject": _("Termination requested by tenant for lease {0}").format(lease_doc.name),
        }).insert(ignore_permissions=True)
    frappe.get_doc({
        "doctype": "ToDo", "reference_type": "Lease Contract", "reference_name": lease_doc.name,
        "description": note, "priority": "High", "role": "Leasing Officer",
    }).insert(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def create_maintenance(category, description, priority="Medium"):
    tenant = _require_tenant()
    lease = _active_lease(tenant)
    if not lease:
        frappe.throw(_("No active lease found; maintenance requests need an active lease."))
    request = frappe.new_doc("Maintenance Request")
    request.unit = lease.unit
    request.tenant = tenant
    request.category = category
    request.priority = priority if priority in ("Low", "Medium", "High", "Emergency") \
        else "Medium"
    request.description = frappe.utils.strip_html(description or "")[:2000]
    request.insert()  # Tenant role has create perm; validate() re-checks unit ownership
    return {"ok": True, "name": request.name}
