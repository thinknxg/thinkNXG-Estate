"""Signed-in website visitor features on the public site (/properties): wishlist, saved
searches and the visitor's own requests. Every function resolves the visitor from the session;
nothing here accepts a lead, customer or user from the caller."""

import frappe
from frappe import _
from frappe.utils import cint, flt

from thinknxg_estate.core.listing_portal_api import listing_portal as lp


def _listing(name):
    row = frappe.db.get_value("Listing", {"name": name, "is_published": 1},
                              ["name", "unit", "property_ref"], as_dict=True)
    if not row:
        frappe.throw(_("This listing is no longer available."), frappe.DoesNotExistError)
    return row


def _identity_filter():
    identity = lp._get_identity_for_current_user()
    return {"customer": identity["customer"]} if identity["customer"] else {"lead": identity["lead"]}


@frappe.whitelist(methods=["POST"])
def toggle_wishlist(listing):
    row = _listing(listing)
    if row.unit:
        return lp.toggle_wishlist(unit=row.unit)
    return lp.toggle_wishlist(property=row.property_ref)


def saved_listing_names():
    """Names of published listings in the current visitor's wishlist (empty for guests and staff)."""
    if frappe.session.user == "Guest" or not frappe.db.get_value("User", frappe.session.user, "portal_lead"):
        return set()
    saved = frappe.get_all("Property Wishlist", filters=_identity_filter(), fields=["unit", "property"])
    units = [s.unit for s in saved if s.unit]
    props = [s.property for s in saved if not s.unit and s.property]
    names = set()
    if units:
        names |= set(frappe.get_all("Listing", filters={"unit": ["in", units], "is_published": 1}, pluck="name"))
    if props:
        names |= set(frappe.get_all("Listing", filters={"property_ref": ["in", props], "unit": ["is", "not set"],
                                                        "is_published": 1}, pluck="name"))
    return names


SEARCH_KEYS = ("q", "listing_type", "usage", "development_status", "category", "unit_type", "city", "locality",
               "bedrooms", "bathrooms", "furnishing", "amenity", "min_price", "max_price", "min_area", "max_area",
               "featured", "new", "permit", "project")


@frappe.whitelist(methods=["POST"])
def save_search(params=None, city=None, unit_type=None, bedrooms=None, min_price=None, max_price=None, **_ignored):
    """Save the current /properties search (every filter); the daily job emails new matches.
    Callers that only know the original five filters (city, type, bedrooms, price) still work."""
    saved = {}
    if params:
        raw = frappe.parse_json(params) if isinstance(params, str) else params
        saved = {k: str(v)[:300] for k, v in (raw or {}).items() if k in SEARCH_KEYS and str(v).strip()}
    else:
        saved = {k: v for k, v in (("city", city), ("unit_type", unit_type), ("bedrooms", bedrooms),
                                   ("min_price", min_price), ("max_price", max_price)) if v}
    if not saved:
        frappe.throw(_("Choose at least one filter before saving a search."))
    from thinknxg_estate.portal.api.listings import csv

    return lp.create_saved_search(
        location=", ".join(csv(saved.get("city")) or csv(saved.get("locality")))[:140] or None,
        unit_type=(csv(saved.get("unit_type")) or [None])[0], bedrooms=cint(saved.get("bedrooms")) or None,
        min_rent=flt(saved.get("min_price")) or None, max_rent=flt(saved.get("max_price")) or None,
        search_params=frappe.as_json(saved))


@frappe.whitelist(methods=["POST"])
def delete_search(name):
    return lp.delete_saved_search(name)


def account_context():
    """Everything the visitor account page shows, for the signed-in visitor only."""
    names = list(saved_listing_names())
    wishlist = _rows(names[:30]) if names else []
    searches = lp.get_my_saved_searches()
    from urllib.parse import urlencode

    from thinknxg_estate.portal.api import catalog

    for s in searches:
        saved = lp._saved_params(s.get("search_params"))
        if saved:
            s["summary"] = ", ".join(c["label"] for c in catalog.chips(saved))
            s["url"] = "/properties?" + urlencode(saved)
    requests = lp.get_my_requests()
    # Enquiries sent from listing pages while signed in (Listing Inquiry, owned by the user).
    requests["enquiries"] = (requests.get("enquiries") or []) + frappe.get_all(
        "Listing Inquiry", filters={"owner": frappe.session.user, "inquiry_type": ["!=", "Viewing"]},
        fields=["name", "listing", "status", "creation"], order_by="creation desc", limit=50)
    titles = {}
    for r in requests["enquiries"]:
        if r.get("listing"):
            if r["listing"] not in titles:
                titles[r["listing"]] = frappe.db.get_value("Listing", r["listing"], "title")
            r["property"] = titles[r["listing"]]
    names = {}
    for r in (requests.get("visits") or []) + (requests.get("leases") or []):
        prop = r.get("property")
        if prop and prop not in names:
            names[prop] = frappe.db.get_value("Property", prop, "property_name") or prop
        label = names.get(prop) or ""
        if r.get("unit_no"):
            label = f"{label} / {r['unit_no']}" if label else r["unit_no"]
        r["label"] = label
        if r.get("docstatus") == 0 and r.get("status") in (None, "", "Draft"):
            r["status"] = "Awaiting review"
    return {"wishlist": wishlist, "searches": searches, "requests": requests}


def _rows(names):
    from thinknxg_estate.portal.api.listings import PUBLIC_FIELDS, _covers

    rows = frappe.get_all("Listing", filters={"name": ["in", names], "is_published": 1}, fields=PUBLIC_FIELDS)
    covers = _covers([r.name for r in rows])
    for r in rows:
        r["cover"] = covers.get(r.name)
    return rows


@frappe.whitelist(methods=["POST"])
def set_language(language):
    """Remember the signed-in visitor's language (English or Arabic) on their own account, so the
    site opens in it on every device. Guests keep it in a browser cookie instead."""
    if language not in ("en", "ar") or not frappe.db.exists("Language", {"name": language, "enabled": 1}):
        frappe.throw(_("This language is not available."))
    if frappe.session.user == "Guest" or frappe.db.get_value("User", frappe.session.user, "user_type") != "Website User":
        return {"language": language}
    frappe.db.set_value("User", frappe.session.user, "language", language, update_modified=False)
    return {"language": language}
