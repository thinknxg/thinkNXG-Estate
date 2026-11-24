"""Guest-facing listing APIs. All endpoints rate-limited and read-only except inquiries."""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, flt, get_datetime, now_datetime, nowdate

PUBLIC_FIELDS = [
    "name", "title", "route", "listing_type", "headline_price", "price_period",
    "unit_type", "bedrooms", "bathrooms", "area_sqm", "furnishing",
    "city", "locality", "featured", "published_on",
]


SORTS = {
    "featured": "featured desc, published_on desc",
    "newest": "published_on desc",
    "price_asc": "headline_price asc",
    "price_desc": "headline_price desc",
    "area_desc": "area_sqm desc",
}


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=120, seconds=3600)
def search(listing_type=None, unit_type=None, city=None, bedrooms=None,
           min_price=None, max_price=None, furnishing=None, page=1, page_size=None,
           bathrooms=None, min_area=None, max_area=None, locality=None, sort=None):
    settings = frappe.get_cached_doc("RE Portal Settings")
    page_size = min(cint(page_size) or cint(settings.page_size) or 9, 30)
    page = max(cint(page), 1)

    filters = {"is_published": 1}
    if listing_type in ("Rent", "Sale"):
        filters["listing_type"] = listing_type
    if unit_type:
        filters["unit_type"] = unit_type
    if city:
        filters["city"] = city
    if cint(bedrooms):
        filters["bedrooms"] = [">=", cint(bedrooms)]
    if flt(min_price) and flt(max_price):
        filters["headline_price"] = ["between", [flt(min_price), flt(max_price)]]
    elif flt(min_price):
        filters["headline_price"] = [">=", flt(min_price)]
    elif flt(max_price):
        filters["headline_price"] = ["<=", flt(max_price)]
    if furnishing:
        filters["furnishing"] = furnishing
    if cint(bathrooms):
        filters["bathrooms"] = [">=", cint(bathrooms)]
    if flt(min_area) and flt(max_area):
        filters["area_sqm"] = ["between", [flt(min_area), flt(max_area)]]
    elif flt(min_area):
        filters["area_sqm"] = [">=", flt(min_area)]
    elif flt(max_area):
        filters["area_sqm"] = ["<=", flt(max_area)]
    if locality:
        filters["locality"] = locality

    total = frappe.db.count("Listing", filters)
    rows = frappe.get_all("Listing", filters=filters, fields=PUBLIC_FIELDS + ["property_ref"],
                          order_by=SORTS.get(sort, SORTS["featured"]),
                          start=(page - 1) * page_size, page_length=page_size)
    for row in rows:
        row["cover"] = frappe.db.get_value(
            "Listing Photo", {"parent": row["name"]}, "image", order_by="idx asc")
        coords = frappe.db.get_value("Property", row.pop("property_ref"), ["latitude", "longitude"],
                                     as_dict=True) if row.get("property_ref") else None
        row["latitude"], row["longitude"] = (coords.latitude, coords.longitude) if coords else (None, None)
    return {"total": total, "page": page, "page_size": page_size, "results": rows,
            "currency": settings.currency_label or "OMR"}


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=240, seconds=3600)
def get(route):
    name = frappe.db.get_value("Listing", {"route": route, "is_published": 1})
    if not name:
        frappe.throw(_("Listing not found."), frappe.DoesNotExistError)
    doc = frappe.get_doc("Listing", name)
    out = {k: doc.get(k) for k in PUBLIC_FIELDS}
    out["description"] = doc.description
    out["photos"] = [p.image for p in doc.photos]
    return out


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="inquiry", limit=20, seconds=3600)
def submit_inquiry(full_name, mobile, listing=None, email=None, message=None,
                   website_url=None, form_ts=None, inquiry_type=None, preferred_date=None,
                   preferred_time_slot=None):
    """Create a Listing Inquiry. Guards: honeypot (website_url must stay empty),
    time-trap (form rendered >= 3s before submit), mobile sanity check."""
    if website_url:
        return {"ok": True}  # honeypot hit: pretend success, store nothing
    if form_ts:
        try:
            if (now_datetime() - get_datetime(form_ts)).total_seconds() < 3:
                return {"ok": True}
        except Exception:
            pass

    mobile = (mobile or "").strip()
    digits = mobile.lstrip("+").replace(" ", "")
    if not (digits.isdigit() and 7 <= len(digits) <= 15):
        frappe.throw(_("Please enter a valid mobile number."))

    if listing and not frappe.db.exists("Listing", {"name": listing, "is_published": 1}):
        listing = None

    inquiry = frappe.new_doc("Listing Inquiry")
    inquiry.full_name = frappe.utils.strip_html((full_name or "").strip())[:120]
    inquiry.mobile = mobile
    inquiry.email = (email or "").strip() or None
    inquiry.listing = listing
    inquiry.message = frappe.utils.strip_html(message or "")[:1000]
    user_agent = frappe.get_request_header("User-Agent", "") if frappe.request else ""
    inquiry.client_meta = f"{frappe.local.request_ip} | {(user_agent or '')[:180]}"
    if inquiry_type == "Viewing":
        _validate_viewing(preferred_date, preferred_time_slot)
        inquiry.inquiry_type = "Viewing"
        inquiry.preferred_date = preferred_date
        inquiry.preferred_time_slot = preferred_time_slot
    inquiry.flags.ignore_permissions = True
    inquiry.insert(ignore_permissions=True)

    _maybe_create_lead(inquiry)
    if inquiry.inquiry_type == "Viewing":
        _request_visit(inquiry)
    return {"ok": True, "inquiry": inquiry.name}


VISIT_SLOTS = ("10:00 - 12:00", "12:00 - 14:00", "14:00 - 16:00", "16:00 - 18:00")


def _validate_viewing(preferred_date, preferred_time_slot):
    from frappe.utils import add_days, getdate

    if not preferred_date or preferred_time_slot not in VISIT_SLOTS:
        frappe.throw(_("Please choose a viewing date and time."))
    day = getdate(preferred_date)
    if day < getdate(nowdate()) or day > getdate(add_days(nowdate(), 90)):
        frappe.throw(_("Please choose a viewing date within the next 90 days."))


def _request_visit(inquiry):
    """A viewing request becomes a Site Visit Booking for the CRM lead (same record the
    /listings app creates), so agents confirm every visit request in one list."""
    unit = inquiry.unit or (inquiry.listing and frappe.db.get_value("Listing", inquiry.listing, "unit"))
    if not unit or not frappe.db.exists("Unit", unit):
        return
    try:
        booking = frappe.get_doc({
            "doctype": "Site Visit Booking", "unit": unit,
            "property": frappe.db.get_value("Unit", unit, "property"),
            "re_lead": inquiry.re_lead or frappe.db.get_value("Listing Inquiry", inquiry.name, "re_lead"),
            "visit_date": inquiry.preferred_date, "visit_time_slot": inquiry.preferred_time_slot,
            "status": "Requested",
            "notes": _("Requested from the listing page by {0} ({1})").format(inquiry.full_name, inquiry.mobile),
        }).insert(ignore_permissions=True)
        inquiry.db_set("site_visit_booking", booking.name, update_modified=False)
        from thinknxg_estate.core.listing_portal_api.listing_portal import _notify_re_managers
        _notify_re_managers("Site Visit Booking", booking.name,
                            _("New viewing request for unit {0}").format(unit))
    except Exception:
        frappe.log_error(title="thinkNXG Estate: viewing request failed", message=inquiry.name)


def _maybe_create_lead(inquiry, source="Website"):
    """Bridge to Phase 3: create an RE Lead when re_crm is installed."""
    if not frappe.db.exists("DocType", "RE Lead"):
        return
    try:
        existing = frappe.db.get_value("RE Lead", {"mobile": inquiry.mobile}, "name")
        if existing:
            inquiry.db_set("re_lead", existing)
            inquiry.db_set("status", "Converted")
            return
        lead = frappe.new_doc("RE Lead")
        lead.full_name = inquiry.full_name
        lead.mobile = inquiry.mobile
        lead.email = inquiry.email
        lead.source = source if frappe.db.exists("Lead Source RE", source) else "Website"
        unit = inquiry.unit or (inquiry.listing and frappe.db.get_value("Listing", inquiry.listing, "unit"))
        if unit:
            lead.unit_of_interest = unit
        lead.insert(ignore_permissions=True)
        inquiry.db_set("re_lead", lead.name)
        inquiry.db_set("status", "Converted")
    except Exception:
        frappe.log_error(title="re_portal: RE Lead creation failed",
                         message=f"Inquiry {inquiry.name}")
