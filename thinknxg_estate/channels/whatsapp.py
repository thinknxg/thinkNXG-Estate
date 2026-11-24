"""One WhatsApp channel for the whole app.

Every business message (lead welcome, visit and rent reminders, reservation warnings,
recommendations) goes through `send_text`, which:

* logs the message once in WhatsApp Message Log against its business record;
* sends free text only inside Meta's 24-hour customer-service window (the customer messaged
  us in the last 24 hours, tracked in Conversation Session);
* outside the window, sends the approved WhatsApp Template registered for the message's
  purpose, filling its variables in order;
* otherwise records the message as Skipped with the reason, instead of letting Meta reject it.

Interactive replies inside a live conversation (buttons, lists, media) stay in
thinknxg_estate.voice.channel.outbound, which this module uses as its transport.
"""

import frappe
from frappe import _
from frappe.utils import cstr

PURPOSES = ("Lead Welcome", "Visit Reminder", "Reservation Expiry", "Rent Reminder",
            "Property Recommendations", "Post Visit Feedback", "Follow Up", "Other")


def normalize(number):
	settings = frappe.get_cached_doc("WhatsApp Settings")
	number = cstr(number).strip().replace(" ", "").replace("-", "")
	if number and not number.startswith("+"):
		code = cstr(settings.default_country_code or "+968").lstrip("+")
		number = number if number.startswith(code) else code + number
	return number.lstrip("+")


def window_open(number):
	from thinknxg_estate.voice.channel.outbound import window_open as _open

	return _open(number)


def approved_template(purpose):
	if not purpose:
		return None
	return frappe.db.get_value("WhatsApp Template", {"purpose": purpose, "approval_status": "Approved"},
	                           "name")


def send_text(to, message, reference_doctype=None, reference_name=None, purpose=None, variables=None):
	"""Queue a business message. Safe to call unconditionally; returns the log name."""
	settings = frappe.get_cached_doc("WhatsApp Settings")
	number = normalize(to) if to else ""
	log = frappe.get_doc({
		"doctype": "WhatsApp Message Log", "to_number": number, "message": cstr(message)[:900],
		"reference_doctype": reference_doctype, "reference_name": reference_name, "status": "Queued",
	}).insert(ignore_permissions=True)

	if not (settings.enabled and number):
		log.db_set({"status": "Skipped",
		            "response": _("WhatsApp is disabled") if number else _("No number")})
		return log.name
	if window_open(number):
		frappe.enqueue("thinknxg_estate.channels.whatsapp.dispatch", queue="short", log_name=log.name,
		               enqueue_after_commit=True)
		return log.name
	template = approved_template(purpose)
	if template:
		frappe.enqueue("thinknxg_estate.channels.whatsapp.dispatch", queue="short", log_name=log.name,
		               template=template, variables=list(variables or []), enqueue_after_commit=True)
		return log.name
	log.db_set({"status": "Skipped", "response": _(
		"Outside the 24-hour customer service window. Register an approved WhatsApp Template "
		"with purpose '{0}' to send this message.").format(purpose or _("Other"))})
	return log.name


def dispatch(log_name, template=None, variables=None):
	from thinknxg_estate.voice.channel import outbound

	log = frappe.get_doc("WhatsApp Message Log", log_name)
	try:
		if template:
			response = outbound.send_template(log.to_number, template, variables or [])
		else:
			response = outbound.send_text(log.to_number, log.message, force=True)
		log.db_set({"status": "Sent" if response else "Failed",
		            "response": cstr(response)[:500] if response else _("Provider call failed; see Error Log")})
	except Exception:
		log.db_set({"status": "Failed", "response": frappe.get_traceback()[-500:]})
		frappe.log_error(title="thinkNXG Estate: WhatsApp send failed", message=f"Log {log.name}")
