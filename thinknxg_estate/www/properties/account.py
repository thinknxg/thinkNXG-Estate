import frappe
from frappe import _

from thinknxg_estate.portal.site import site_context


def get_context(context):
    context.no_cache = 1
    site_context(context)
    context.title = f"{_('My account')} | {context.site.title}"
    context.metatags = {"title": context.title, "robots": "noindex, nofollow"}
    context.canonical = frappe.utils.get_url("/properties/account")
    nxt = frappe.form_dict.get("next") or "/properties/account"
    context.next = nxt if nxt.startswith("/") and not nxt.startswith("//") else "/properties/account"
    user = frappe.session.user
    context.signed_in = user != "Guest"
    context.is_staff = context.site.staff
    if context.signed_in and not context.is_staff:
        from thinknxg_estate.portal.api import catalog
        from thinknxg_estate.portal.api.visitor import account_context

        context.update(account_context())
        context.full_name = frappe.db.get_value("User", user, "full_name")
        context.saved = {r.name for r in context.wishlist}
        context.saved_html = catalog.render_cards(
            [_card_row(r) for r in context.wishlist], "grid", context.saved)
    return context


def _card_row(row):
    """Account page wishlist rows carry what the card needs; fill the optional extras."""
    row.setdefault("photos", [row.cover] if row.get("cover") else [])
    row.setdefault("excerpt", "")
    row.setdefault("latitude", None)
    row.setdefault("longitude", None)
    return row
