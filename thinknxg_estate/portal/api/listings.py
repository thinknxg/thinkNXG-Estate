"""Guest-facing listing APIs. All endpoints rate-limited and read-only except inquiries."""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, flt, get_datetime, now_datetime, nowdate

PUBLIC_FIELDS = [
    "name", "title", "route", "listing_type", "headline_price", "price_period",
    "unit_type", "bedrooms", "bathrooms", "area_sqm", "furnishing",
    "city", "locality", "featured", "published_on", "usage", "development_status", "permit_number",
]


SORTS = {
    "relevance": "featured desc, published_on desc",
    "featured": "featured desc, published_on desc",
    "newest": "published_on desc",
    "price_asc": "headline_price asc",
    "price_desc": "headline_price desc",
    "area_desc": "area_sqm desc",
}

NEW_LISTING_DAYS = 30
CARD_PHOTOS = 4
MAX_LIST = 25  # most values accepted in one multi-select filter


def csv(value):
    """A filter value that may be a list or a comma-separated string -> a clean, bounded list."""
    if isinstance(value, (list, tuple)):
        items = value
    else:
        items = str(value or "").split(",")
    return [str(i).strip() for i in items if str(i).strip()][:MAX_LIST]


def categories():
    """Property categories the public site offers, as filters over fields Listings really have.
    Only categories that have listings are shown on the site."""
    return {
        "apartments": {"label": _("Apartments"), "icon": "building",
                       "unit_type": ["Studio", "1BR", "2BR", "3BR", "4BR+", "Penthouse", "Apartment Building"],
                       "usage": "Residential"},
        "villas": {"label": _("Villas"), "icon": "home", "unit_type": ["Villa", "Villa Compound"]},
        "land": {"label": _("Land and plots"), "icon": "map", "unit_type": ["Land"]},
        "offices": {"label": _("Office spaces"), "icon": "briefcase", "unit_type": ["Office", "Commercial Tower"]},
        "shops": {"label": _("Shops"), "icon": "store", "unit_type": ["Shop"]},
        "warehouses": {"label": _("Warehouses"), "icon": "warehouse", "unit_type": ["Warehouse"]},
        "commercial": {"label": _("Commercial properties"), "icon": "building2", "usage": "Commercial"},
    }


def build_filters(listing_type=None, unit_type=None, city=None, bedrooms=None, min_price=None,
                  max_price=None, furnishing=None, bathrooms=None, min_area=None, max_area=None,
                  locality=None, usage=None, development_status=None, category=None, featured=None,
                  new=None, permit=None, project=None, north=None, south=None, east=None, west=None,
                  amenity=None, **_ignored):
    """Listing filters shared by the search page, the map, saved searches and alerts.
    Multi-select values (unit_type, city, locality, furnishing, amenity) may be comma-separated."""
    filters = {"is_published": 1}
    if listing_type in ("Rent", "Sale"):
        filters["listing_type"] = listing_type
    if usage in ("Residential", "Commercial"):
        filters["usage"] = usage
    preset = categories().get(category or "")
    if preset:
        if preset.get("usage"):
            filters["usage"] = preset["usage"]
        if preset.get("unit_type") and not unit_type:
            unit_type = preset["unit_type"]
    for key, value in (("unit_type", unit_type), ("city", city), ("locality", locality),
                       ("furnishing", furnishing)):
        values = csv(value)
        if len(values) == 1:
            filters[key] = values[0]
        elif values:
            filters[key] = ["in", values]
    if development_status in ("Ready", "Under Development"):
        filters["development_status"] = development_status
    if str(bedrooms or "").lower() == "studio":
        filters["bedrooms"] = 0
    elif cint(bedrooms):
        filters["bedrooms"] = [">=", cint(bedrooms)]
    if flt(min_price) and flt(max_price):
        filters["headline_price"] = ["between", [flt(min_price), flt(max_price)]]
    elif flt(min_price):
        filters["headline_price"] = [">=", flt(min_price)]
    elif flt(max_price):
        filters["headline_price"] = ["<=", flt(max_price)]
    if cint(bathrooms):
        filters["bathrooms"] = [">=", cint(bathrooms)]
    if flt(min_area) and flt(max_area):
        filters["area_sqm"] = ["between", [flt(min_area), flt(max_area)]]
    elif flt(min_area):
        filters["area_sqm"] = [">=", flt(min_area)]
    elif flt(max_area):
        filters["area_sqm"] = ["<=", flt(max_area)]
    if cint(featured):
        filters["featured"] = 1
    if cint(new):
        filters["published_on"] = [">=", frappe.utils.add_days(nowdate(), -NEW_LISTING_DAYS)]
    if cint(permit):
        filters["permit_number"] = ["is", "set"]

    # Filters that depend on the property: project, map area, amenities. Each narrows the set of
    # properties; the listing filter is then "property_ref in (...)".
    property_sets = []
    if project:
        property_sets.append({project})
    if all(v not in (None, "") for v in (north, south, east, west)):
        # a property at exactly 0,0 has no location set
        in_box = frappe.get_all(
            "Property", filters={"latitude": ["between", [flt(south), flt(north)]],
                                 "longitude": ["between", [flt(west), flt(east)]]},
            fields=["name", "latitude", "longitude"], limit=5000)
        property_sets.append({p.name for p in in_box if p.latitude or p.longitude})
    amenities = csv(amenity)
    if amenities:
        rows = frappe.db.sql("""SELECT parent FROM `tabProperty Amenity`
            WHERE parenttype = 'Property' AND amenity IN %(a)s
            GROUP BY parent HAVING COUNT(DISTINCT amenity) = %(n)s""", {"a": amenities, "n": len(amenities)})
        property_sets.append({r[0] for r in rows})
    if property_sets:
        names = set.intersection(*property_sets)
        filters["property_ref"] = ["in", list(names) or ["-"]]
    return filters


def listing_query(q=None, **filters):
    """get_all() keyword arguments for a search: filters plus the free-text box, which looks
    in the title, city and locality."""
    query = {"filters": build_filters(**filters)}
    q = (q or "").strip()[:80]
    if q:
        like = ["like", f"%{q}%"]
        query["or_filters"] = {"title": like, "city": like, "locality": like}
    return query


def _coords(property_names):
    names = list({n for n in property_names if n})
    if not names:
        return {}
    return {r.name: r for r in frappe.get_all(
        "Property", filters={"name": ["in", names]}, fields=["name", "latitude", "longitude"])}


def _covers(listing_names):
    covers = {}
    if not listing_names:
        return covers
    for r in frappe.get_all("Listing Photo", filters={"parent": ["in", list(listing_names)]},
                            fields=["parent", "image"], order_by="idx asc"):
        covers.setdefault(r.parent, r.image)
    return covers


def _photos(listing_names, limit=CARD_PHOTOS):
    """Up to `limit` photos per listing, in gallery order, for the card slideshow."""
    photos = {}
    if not listing_names:
        return photos
    for r in frappe.get_all("Listing Photo", filters={"parent": ["in", list(listing_names)]},
                            fields=["parent", "image"], order_by="idx asc"):
        if r.image and len(photos.setdefault(r.parent, [])) < limit:
            photos[r.parent].append(r.image)
    return photos


def excerpt(html, length=150):
    text = " ".join(frappe.utils.strip_html_tags(html or "").split())
    return text if len(text) <= length else text[:length].rsplit(" ", 1)[0] + "…"


# Read-only public endpoints are limited per visitor IP to stop scraping, high enough that a person
# browsing (or an office sharing one IP) never meets the limit. The /properties page itself calls
# run_search() directly, so page views do not count against the API limit.
PUBLIC_READ_LIMIT = 600


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=PUBLIC_READ_LIMIT, seconds=3600)
def search(page=1, page_size=None, sort=None, **filters):
    filters.pop("cmd", None)
    return run_search(page=page, page_size=page_size, sort=sort, **filters)


def run_search(page=1, page_size=None, sort=None, **filters):
    settings = frappe.get_cached_doc("RE Portal Settings")
    page_size = min(cint(page_size) or cint(settings.page_size) or 9, 30)
    page = max(cint(page), 1)
    query = listing_query(**filters)

    total = cint(frappe.get_all("Listing", fields=[{"COUNT": "name", "as": "n"}], **query)[0].n)
    rows = frappe.get_all("Listing", fields=PUBLIC_FIELDS + ["property_ref", "unit", "description"],
                          order_by=SORTS.get(sort, SORTS["featured"]),
                          start=(page - 1) * page_size, limit=page_size, **query)
    names = [r.name for r in rows]
    photos = _photos(names)
    coords = _coords([r.property_ref for r in rows])
    for row in rows:
        row["photos"] = photos.get(row["name"], [])
        row["cover"] = row["photos"][0] if row["photos"] else None
        row["excerpt"] = excerpt(row.pop("description", None))
        c = coords.get(row.pop("property_ref"))
        row["latitude"], row["longitude"] = (c.latitude, c.longitude) if c else (None, None)
    return {"total": total, "page": page, "page_size": page_size, "results": rows,
            "currency": settings.currency_label or "OMR"}


MAP_LIMIT = 500


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=PUBLIC_READ_LIMIT, seconds=3600)
def map_points(**kwargs):
    """Every listing matching the search filters that has map coordinates (up to 500),
    for the map view. Coordinates come from the property, so units share their building's pin."""
    kwargs = {k: v for k, v in kwargs.items() if k not in ("cmd", "page", "sort", "view")}
    rows = frappe.get_all("Listing", **listing_query(**kwargs),
                          fields=["name", "title", "route", "headline_price", "price_period", "listing_type",
                                  "bedrooms", "bathrooms", "area_sqm", "unit_type", "locality", "city",
                                  "property_ref"],
                          order_by=SORTS["featured"], limit=MAP_LIMIT)
    coords = _coords([r.property_ref for r in rows])
    covers = _covers([r.name for r in rows])
    points = []
    for r in rows:
        c = coords.get(r.pop("property_ref"))
        if not c or not (c.latitude and c.longitude):
            continue
        r.update(lat=c.latitude, lng=c.longitude, cover=covers.get(r.name))
        points.append(r)
    settings = frappe.get_cached_doc("RE Portal Settings")
    return {"points": points, "matching": len(rows), "currency": settings.currency_label or "OMR"}


COMPARE_FIELDS = PUBLIC_FIELDS + ["unit", "property_ref", "description"]


def compare_rows(names):
    """Up to three published listings, in the order given, for the compare page."""
    names = [n for n in (names or []) if n][:3]
    if not names:
        return []
    rows = {r.name: r for r in frappe.get_all(
        "Listing", filters={"name": ["in", names], "is_published": 1}, fields=COMPARE_FIELDS)}
    covers = _covers(list(rows))
    from thinknxg_estate.estate_portal.doctype.listing.listing import listing_amenities

    out = []
    for n in names:
        if n in rows:
            row = rows[n]
            row["cover"] = covers.get(n)
            row["amenities"] = listing_amenities(row.property_ref)
            out.append(row)
    return out


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=PUBLIC_READ_LIMIT, seconds=3600)
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
    prop = (frappe.db.get_value("Unit", unit, "property") if unit else
            inquiry.listing and frappe.db.get_value("Listing", inquiry.listing, "property_ref"))
    if not prop:
        return
    portal_lead = (frappe.db.get_value("User", frappe.session.user, "portal_lead")
                   if frappe.session.user != "Guest" else None)
    try:
        booking = frappe.get_doc({
            "doctype": "Site Visit Booking", "unit": unit, "property": prop, "lead": portal_lead,
            "re_lead": inquiry.re_lead or frappe.db.get_value("Listing Inquiry", inquiry.name, "re_lead"),
            "visit_date": inquiry.preferred_date, "visit_time_slot": inquiry.preferred_time_slot,
            "status": "Requested",
            "notes": _("Requested from the listing page by {0} ({1})").format(inquiry.full_name, inquiry.mobile),
        }).insert(ignore_permissions=True)
        inquiry.db_set("site_visit_booking", booking.name, update_modified=False)
        from thinknxg_estate.core.listing_portal_api.listing_portal import _notify_re_managers
        _notify_re_managers("Site Visit Booking", booking.name,
                            _("New viewing request for {0}").format(unit or prop))
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
