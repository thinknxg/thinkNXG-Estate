import frappe
from frappe import _

from thinknxg_estate.portal.api.listings import compare_rows
from thinknxg_estate.portal.utils import amount, money


def get_context(context):
    context.no_cache = 1
    names = [n.strip() for n in (frappe.form_dict.get("l") or "").split(",") if n.strip()]
    context.rows = compare_rows(names)
    context.money = money
    context.amount = amount
    context.currency = frappe.db.get_single_value("RE Portal Settings", "currency_label") or "OMR"
    context.title = _("Compare properties")
    context.specs = [
        ("listing_type", _("Rent or buy")), ("unit_type", _("Property type")), ("city", _("City")),
        ("locality", _("Area")), ("bedrooms", _("Bedrooms")), ("bathrooms", _("Bathrooms")),
        ("area_sqm", _("Area (sqm)")), ("furnishing", _("Furnishing")),
    ]
    return context
