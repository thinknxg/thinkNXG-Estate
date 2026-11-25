"""Shared context for every page of the public property site: header navigation, location menu,
footer links, language switch and the visitor's state. Pages call site_context() from get_context()."""

import frappe
from frappe import _

from thinknxg_estate.portal.api import catalog
from thinknxg_estate.portal.utils import amount, money

LEGAL_ROUTES = {  # footer links shown only when the Web Page exists
    "privacy": ("privacy", "privacy-policy"),
    "terms": ("terms", "terms-and-conditions", "terms-of-service"),
}
LANGUAGES = {"en": "English", "ar": "العربية"}


def _web_page(routes):
    return next((r for r in routes if frappe.db.exists("Web Page", {"route": r, "published": 1})), None)


def site_context(context, active=None):
    """Adds `site` (and the money helpers) to a page context."""
    settings = frappe.get_cached_doc("RE Portal Settings")
    counts = catalog.counts()
    user = frappe.session.user
    visitor = user != "Guest" and frappe.db.get_value("User", user, "user_type") == "Website User"
    staff = user != "Guest" and not visitor

    nav = [("rent", _("Rent"), "/properties?listing_type=Rent", counts["Rent"]),
           ("buy", _("Buy"), "/properties?listing_type=Sale", counts["Sale"]),
           ("projects", _("New projects"), "/properties?development_status=Under+Development", counts["projects"]),
           ("commercial", _("Commercial"), "/properties?usage=Commercial", counts["Commercial"])]
    # Rent is always offered; the others appear when the site has listings for them.
    nav = [{"key": k, "label": label, "url": url, "count": n} for k, label, url, n in nav if n or k == "rent"]

    lang = frappe.local.lang or "en"
    other = "en" if lang.startswith("ar") else "ar"
    enabled = set(frappe.get_all("Language", filters={"enabled": 1}, pluck="name"))
    saved = len(_saved()) if visitor else 0

    labels = {"privacy": _("Privacy policy"), "terms": _("Terms and conditions")}
    footer_links = []
    for key, routes in LEGAL_ROUTES.items():
        route = _web_page(routes)
        if route:
            footer_links.append({"label": labels[key], "url": "/" + route})
    extra = frappe.get_cached_doc("Website Settings").get("footer_items") or []
    more = [{"label": _(i.label), "url": i.url} for i in extra if i.get("label") and i.get("url")]

    context.site = frappe._dict(
        title=_(settings.portal_title) if settings.portal_title else _("Properties"),
        tagline=_(settings.portal_tagline) if settings.portal_tagline else "",
        currency=settings.currency_label or "OMR", whatsapp=settings.contact_whatsapp,
        email=settings.contact_email, nav=nav, active=active, counts=counts,
        cities=catalog.facets()["cities"][:12], visitor=visitor, staff=staff, saved_count=saved,
        owner_portal=user != "Guest" and "Property Owner" in frappe.get_roles(user),
        lang=lang, other_lang=other if other in enabled else None, other_label=LANGUAGES[other],
        footer_links=more, legal=footer_links,
        map_tile_url=settings.get("map_tile_url") or "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        map_attribution=settings.get("map_attribution") or "&copy; OpenStreetMap contributors",
        base_url=frappe.utils.get_url())
    context.money = money
    context.amount = amount
    context.currency = context.site.currency
    return context


def _saved():
    from thinknxg_estate.portal.api.visitor import saved_listing_names

    return saved_listing_names()
