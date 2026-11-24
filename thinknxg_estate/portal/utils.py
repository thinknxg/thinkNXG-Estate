import frappe
from frappe.utils import fmt_money


def money(amount, currency=None):
    """Template helper: OMR renders with 3 decimals via Currency settings."""
    if amount is None:
        return ""
    return fmt_money(amount, currency=currency or
                     frappe.db.get_single_value("RE Portal Settings", "currency_label") or "OMR")


def amount(value, currency=None):
    """Template helper: the number only, at the currency's precision (OMR: 3 decimals), for
    places that already print the currency code beside it."""
    if value is None:
        return ""
    from frappe.utils import fmt_money

    currency = currency or frappe.db.get_single_value("RE Portal Settings", "currency_label") or "OMR"
    return fmt_money(value, precision=_precision(currency))


def _precision(currency):
    frac = frappe.db.get_value("Currency", currency, "fraction_units")
    return {1000: 3, 100: 2, 10: 1, 1: 0}.get(frappe.utils.cint(frac), 2)
