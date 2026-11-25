import frappe
from frappe import _

from thinknxg_estate.portal.api.listings import compare_rows
from thinknxg_estate.portal.site import site_context


def get_context(context):
    context.no_cache = 1
    site_context(context)
    names = [n.strip() for n in (frappe.form_dict.get("l") or "").split(",") if n.strip()]
    context.rows = compare_rows(names)
    context.title = f"{_('Compare properties')} | {context.site.title}"
    context.metatags = {"title": context.title, "robots": "noindex, follow"}
    context.canonical = frappe.utils.get_url("/properties/compare")
    context.specs = [
        ("listing_type", _("Rent or buy")), ("unit_type", _("Property type")), ("city", _("City")),
        ("locality", _("Area")), ("bedrooms", _("Bedrooms")), ("bathrooms", _("Bathrooms")),
        ("area_sqm", _("Area (sqm)")), ("furnishing", _("Furnishing")),
    ]
    return context
