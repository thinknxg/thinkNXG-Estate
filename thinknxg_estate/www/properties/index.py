"""The public property website: search, grid and map views, wishlist, compare and saved searches.
It replaces the older /listings page, which now redirects here."""

import frappe
from frappe import _

from thinknxg_estate.portal.api.listings import SORTS, run_search
from thinknxg_estate.portal.api.visitor import saved_listing_names
from thinknxg_estate.portal.utils import amount, money

FILTER_KEYS = ["listing_type", "city", "locality", "unit_type", "bedrooms", "bathrooms", "furnishing",
               "min_price", "max_price", "min_area", "max_area", "sort"]
MORE_KEYS = ("locality", "bathrooms", "furnishing", "min_area", "max_area")


def _options(fieldname):
    for doctype in ("Listing", "Unit"):
        options = frappe.get_meta(doctype).get_options(fieldname) if frappe.get_meta(doctype).has_field(
            fieldname) else ""
        values = [o for o in (options or "").split("\n") if o]
        if values:
            return values
    return []


def get_context(context):
    context.no_cache = 1
    args = frappe._dict({k: frappe.form_dict.get(k) for k in FILTER_KEYS})
    result = run_search(page=frappe.form_dict.get("page") or 1, **args)
    context.update(result)
    context.money = money
    context.amount = amount
    context.args = args
    context.view = "map" if frappe.form_dict.get("view") == "map" else "grid"
    context.total_pages = -(-result["total"] // result["page_size"])
    published = {"is_published": 1}
    context.cities = sorted(c for c in frappe.get_all("Listing", filters=published, distinct=True, pluck="city") if c)
    context.localities = sorted(
        c for c in frappe.get_all("Listing", filters=published, distinct=True, pluck="locality") if c)
    context.unit_types = sorted(
        {t for t in frappe.get_all("Listing", filters=published, distinct=True, pluck="unit_type") if t}
        | set(_options("unit_type")))
    context.furnishings = _options("furnishing")
    context.sorts = [(k, label) for k, label in (
        ("featured", _("Featured")), ("newest", _("Newest")), ("price_asc", _("Price: low to high")),
        ("price_desc", _("Price: high to low")), ("area_desc", _("Largest"))) if k in SORTS]
    context.filter_keys = FILTER_KEYS
    context.more_open = any(args.get(k) for k in MORE_KEYS)
    context.query = "&".join(f"{k}={frappe.utils.quote(str(args[k]))}" for k in FILTER_KEYS if args.get(k))
    context.saved = saved_listing_names()
    context.is_visitor = frappe.session.user != "Guest"
    settings = frappe.get_cached_doc("RE Portal Settings")
    # Settings text goes through translation so the shipped default title reads in Arabic too.
    context.portal_title = _(settings.portal_title) if settings.portal_title else _("Properties")
    context.portal_tagline = _(settings.portal_tagline) if settings.portal_tagline else ""
    context.map_tile_url = settings.get("map_tile_url") or "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    context.map_attribution = settings.get("map_attribution") or "&copy; OpenStreetMap contributors"
    context.map_lat = settings.get("map_default_lat") or 23.588
    context.map_lng = settings.get("map_default_lng") or 58.3829
    context.map_zoom = settings.get("map_default_zoom") or 11
    context.title = context.portal_title
    context.metatags = {"title": context.portal_title, "description": settings.portal_tagline or ""}
    return context
