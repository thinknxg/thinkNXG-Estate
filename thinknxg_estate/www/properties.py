import frappe
from thinknxg_estate.portal.api.listings import search
from thinknxg_estate.portal.utils import money


def get_context(context):
    context.no_cache = 1
    args = frappe.form_dict
    result = search(
        listing_type=args.get("listing_type"),
        unit_type=args.get("unit_type"),
        city=args.get("city"),
        bedrooms=args.get("bedrooms"),
        min_price=args.get("min_price"),
        max_price=args.get("max_price"),
        page=args.get("page") or 1,
        furnishing=args.get("furnishing"),
        bathrooms=args.get("bathrooms"),
        min_area=args.get("min_area"),
        max_area=args.get("max_area"),
        sort=args.get("sort"),
    )
    context.update(result)
    context.money = money
    context.args = args
    context.total_pages = -(-result["total"] // result["page_size"])
    context.cities = frappe.get_all("Listing", filters={"is_published": 1},
                                    distinct=True, pluck="city")
    meta = frappe.get_meta("Listing")
    context.unit_types = [o for o in (meta.get_options("unit_type") or "").split("\n") if o] or \
        [o for o in (frappe.get_meta("Unit").get_options("unit_type") or "").split("\n") if o]
    context.furnishings = [o for o in (meta.get_options("furnishing") or
                                       frappe.get_meta("Unit").get_options("furnishing") or "").split("\n") if o]
    context.filter_keys = ["listing_type", "city", "unit_type", "bedrooms", "bathrooms", "furnishing",
                           "min_price", "max_price", "min_area", "max_area", "sort"]
    settings = frappe.get_cached_doc("RE Portal Settings")
    context.portal_title = settings.portal_title
    context.portal_tagline = settings.portal_tagline
    context.title = "Properties"
    return context
