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


@frappe.whitelist(methods=["POST"])
def save_search(city=None, unit_type=None, bedrooms=None, min_price=None, max_price=None, **_ignored):
    """Save the current /properties filters; the daily job emails new matches."""
    if not any([city, unit_type, cint(bedrooms), flt(min_price), flt(max_price)]):
        frappe.throw(_("Choose at least one filter (city, type, bedrooms or price) before saving a search."))
    return lp.create_saved_search(location=city, unit_type=unit_type, bedrooms=cint(bedrooms) or None,
                                  min_rent=flt(min_price) or None, max_rent=flt(max_price) or None)


@frappe.whitelist(methods=["POST"])
def delete_search(name):
    return lp.delete_saved_search(name)


def account_context():
    """Everything the visitor account page shows, for the signed-in visitor only."""
    names = list(saved_listing_names())
    wishlist = _rows(names[:30]) if names else []
    searches = lp.get_my_saved_searches()
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
