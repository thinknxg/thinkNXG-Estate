import frappe
from frappe import _

from thinknxg_estate.portal.utils import amount, money


def get_context(context):
    context.no_cache = 1
    context.money = money
    context.amount = amount
    context.currency = frappe.db.get_single_value("RE Portal Settings", "currency_label") or "OMR"
    context.title = _("My account")
    nxt = frappe.form_dict.get("next") or "/properties/account"
    context.next = nxt if nxt.startswith("/") and not nxt.startswith("//") else "/properties/account"
    user = frappe.session.user
    context.signed_in = user != "Guest"
    context.is_staff = context.signed_in and frappe.db.get_value("User", user, "user_type") == "System User"
    if context.signed_in and not context.is_staff:
        from thinknxg_estate.portal.api.visitor import account_context

        context.update(account_context())
        context.full_name = frappe.db.get_value("User", user, "full_name")
    return context
