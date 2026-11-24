"""Unified communication history for a lead, tenant, owner or property.

Collects WhatsApp messages (business log and conversation threads), voice notes, emails,
comments, enquiries, visit requests and site visits, and maintenance requests into one list,
newest first. Read access to the anchor record is required.
"""

import frappe
from frappe import _
from frappe.utils import cint, strip_html

from thinknxg_estate.core.security import desk_staff_only

ANCHORS = ("RE Lead", "Tenant", "Property Owner", "Property", "RE Deal")


def _item(at, channel, summary, direction=None, reference_doctype=None, reference_name=None):
	return {"at": str(at), "channel": channel, "direction": direction,
	        "summary": strip_html(summary or "")[:500],
	        "reference_doctype": reference_doctype, "reference_name": reference_name}


def _numbers(*values):
	from thinknxg_estate.channels.whatsapp import normalize

	return sorted({normalize(v) for v in values if v})


def _whatsapp(numbers, refs):
	items = []
	filters = []
	if numbers:
		filters.append(["to_number", "in", numbers])
	for dt, names in refs.items():
		if names:
			items += [_item(r.creation, "WhatsApp", r.message, "Outbound", r.reference_doctype or None,
			                r.reference_name or None)
			          for r in frappe.get_all("WhatsApp Message Log",
			                                  filters={"reference_doctype": dt, "reference_name": ["in", names]},
			                                  fields=["creation", "message", "reference_doctype", "reference_name",
			                                          "status"])]
	if filters:
		seen = {(i["at"], i["summary"]) for i in items}
		for r in frappe.get_all("WhatsApp Message Log", filters=filters,
		                        fields=["creation", "message", "reference_doctype", "reference_name"]):
			key = (str(r.creation), strip_html(r.message or "")[:500])
			if key not in seen:
				items.append(_item(r.creation, "WhatsApp", r.message, "Outbound", r.reference_doctype or None,
				                   r.reference_name or None))
		threads = frappe.get_all("Customer Thread", {"phone_number": ["in", numbers]}, pluck="name")
		if threads:
			for m in frappe.get_all("Thread Message", {"parent": ["in", threads], "parenttype": "Customer Thread"},
			                        ["sent_at", "creation", "direction", "body", "message_type", "parent"]):
				items.append(_item(m.sent_at or m.creation, "WhatsApp", m.body or m.message_type, m.direction,
				                   "Customer Thread", m.parent))
		for v in frappe.get_all("Voice Message", {"from_number": ["in", numbers]},
		                        ["name", "creation", "transcript", "translation"]):
			items.append(_item(v.creation, _("Voice note"), v.translation or v.transcript, "Inbound",
			                   "Voice Message", v.name))
	return items


def _docs_comms(refs):
	items = []
	for dt, names in refs.items():
		if not names:
			continue
		for c in frappe.get_all("Communication",
		                        {"reference_doctype": dt, "reference_name": ["in", names]},
		                        ["creation", "communication_medium", "subject", "content", "sent_or_received",
		                         "reference_doctype", "reference_name"]):
			items.append(_item(c.creation, c.communication_medium or _("Email"), c.subject or c.content,
			                   "Outbound" if c.sent_or_received == "Sent" else "Inbound",
			                   c.reference_doctype, c.reference_name))
		for c in frappe.get_all("Comment",
		                        {"reference_doctype": dt, "reference_name": ["in", names],
		                         "comment_type": ["in", ["Comment", "Info"]]},
		                        ["creation", "content", "comment_by", "reference_doctype", "reference_name"]):
			items.append(_item(c.creation, _("Note"), f"{c.comment_by or ''}: {c.content}", None,
			                   c.reference_doctype, c.reference_name))
	return items


def _records(doctype, filters, label, summary_fields, date_field="creation"):
	fields = list({"name", "creation", date_field, *summary_fields})
	return [_item(r.get(date_field) or r.creation, label,
	              " · ".join(str(r.get(f)) for f in summary_fields if r.get(f)), None, doctype, r.name)
	        for r in frappe.get_all(doctype, filters=filters, fields=fields)]


@frappe.whitelist()
@desk_staff_only
def get_timeline(doctype, name, limit=200):
	if doctype not in ANCHORS:
		frappe.throw(_("Communication history is not available for {0}.").format(doctype))
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")

	items, refs, numbers = [], {doctype: [name]}, []
	if doctype == "RE Lead":
		numbers = _numbers(doc.mobile)
		deals = frappe.get_all("RE Deal", {"lead": name}, pluck="name")
		refs["RE Deal"] = deals
		items += _records("Listing Inquiry", {"re_lead": name}, _("Enquiry"), ["inquiry_type", "message"])
		items += _records("Property Enquiry", {"re_lead": name}, _("Enquiry"), ["unit", "message"])
		items += _records("Site Visit Booking", {"re_lead": name}, _("Visit request"),
		                  ["unit", "visit_date", "visit_time_slot", "status"])
		if deals:
			items += _records("Site Visit", {"deal": ["in", deals]}, _("Site visit"),
			                  ["unit", "outcome", "feedback"], "visit_datetime")
	elif doctype == "RE Deal":
		numbers = _numbers(doc.mobile)
		items += _records("Site Visit", {"deal": name}, _("Site visit"), ["unit", "outcome", "feedback"],
		                  "visit_datetime")
	elif doctype == "Tenant":
		numbers = _numbers(doc.mobile, doc.whatsapp_number)
		leases = frappe.get_all("Lease Contract", {"tenant": name}, pluck="name")
		refs["Lease Contract"] = leases
		schedules = frappe.get_all("Rent Schedule", {"lease_contract": ["in", leases or [""]]}, pluck="name")
		refs["Rent Installment"] = frappe.get_all("Rent Installment", {"parent": ["in", schedules or [""]]},
		                                          pluck="name")
		items += _records("Maintenance Request", {"tenant": name}, _("Maintenance"),
		                  ["category", "status", "description"])
	elif doctype == "Property Owner":
		numbers = _numbers(doc.mobile)
		items += _records("Owner Statement", {"property_owner": name, "docstatus": 1}, _("Statement"),
		                  ["period_from", "period_to", "net_payable"])
	elif doctype == "Property":
		units = frappe.get_all("Unit", {"property": name}, pluck="name")
		refs["Unit"] = units
		items += _records("Maintenance Request", {"property": name}, _("Maintenance"),
		                  ["unit", "category", "status"])
		items += _records("Listing Inquiry", {"unit": ["in", units or [""]]}, _("Enquiry"),
		                  ["full_name", "inquiry_type", "message"])

	items += _whatsapp(numbers, refs)
	items += _docs_comms(refs)
	items.sort(key=lambda i: i["at"], reverse=True)
	return items[:cint(limit) or 200]
