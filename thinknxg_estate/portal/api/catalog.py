"""Data for the public property site's landing page and search page: category and location
counts, featured and premium listings, new projects, filter options, search suggestions and
the HTML of result cards.

Counts and showcase rows are cached for a couple of minutes (they are the same for every
visitor); anything that depends on the visitor, such as which listings are saved, is added
when the page is rendered. All of it reads Listings that are published, so nothing here can
show an unpublished or fabricated property."""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, flt

from thinknxg_estate.portal.api.listings import (
    PUBLIC_FIELDS, PUBLIC_READ_LIMIT, SORTS, _covers, _photos, categories, csv, excerpt, run_search,
)

CACHE_SECONDS = 120
FILTER_KEYS = [
    "q", "listing_type", "usage", "development_status", "category", "unit_type", "city", "locality",
    "bedrooms", "bathrooms", "furnishing", "amenity", "min_price", "max_price", "min_area", "max_area",
    "featured", "new", "permit", "project", "north", "south", "east", "west", "sort",
]
MULTI_KEYS = ("unit_type", "city", "locality", "furnishing", "amenity")
MAP_KEYS = ("north", "south", "east", "west")


# ---------------------------------------------------------------- showcase data (cached)

def _cached(key, generator):
    full = f"thinknxg_estate:{key}"
    value = frappe.cache.get_value(full, expires=True)
    if value is None:
        value = generator()
        frappe.cache.set_value(full, value, expires_in_sec=CACHE_SECONDS)
    return value


def _with_media(rows):
    names = [r.name for r in rows]
    photos = _photos(names)
    for r in rows:
        r["photos"] = photos.get(r.name, [])
        r["cover"] = r["photos"][0] if r["photos"] else None
        r["excerpt"] = excerpt(r.pop("description", None))
    return rows


def _listing_rows(filters=None, order_by=None, limit=8, extra=None):
    rows = frappe.get_all("Listing", filters={"is_published": 1, **(filters or {})},
                          fields=PUBLIC_FIELDS + ["description", "property_ref"] + (extra or []),
                          order_by=order_by or "featured desc, published_on desc", limit=limit)
    return _with_media(rows)


def counts():
    def build():
        by_type = dict(frappe.db.sql("""SELECT listing_type, COUNT(*) FROM `tabListing`
                                        WHERE is_published = 1 GROUP BY listing_type"""))
        usage = dict(frappe.db.sql("""SELECT IFNULL(`usage`, ''), COUNT(*) FROM `tabListing`
                                      WHERE is_published = 1 GROUP BY `usage`"""))
        building = frappe.db.sql("""SELECT COUNT(*) FROM `tabListing`
                                    WHERE is_published = 1 AND development_status = 'Under Development'""")[0][0]
        by_unit = frappe.db.sql("""SELECT unit_type, IFNULL(`usage`, ''), COUNT(*) FROM `tabListing`
                                   WHERE is_published = 1 GROUP BY unit_type, `usage`""")
        total = sum(by_type.values())
        return {"total": total, "Rent": by_type.get("Rent", 0), "Sale": by_type.get("Sale", 0),
                "Commercial": usage.get("Commercial", 0), "projects": building,
                "by_unit": [list(r) for r in by_unit]}

    return _cached("counts", build)


def category_cards():
    """Categories that have at least one listing, with their counts."""
    c = counts()
    cards = []
    for key, preset in categories().items():
        n = sum(cnt for unit_type, usage, cnt in c["by_unit"]
                if (not preset.get("unit_type") or unit_type in preset["unit_type"])
                and (not preset.get("usage") or usage == preset["usage"]))
        if n:
            cards.append({"key": key, "label": preset["label"], "icon": preset["icon"], "count": n})
    return cards


def home_data():
    def build():
        c = counts()
        featured = _listing_rows({"featured": 1}, limit=8)
        has_featured = len(featured) > 0
        if len(featured) < 4:
            seen = {r.name for r in featured}
            featured += [r for r in _listing_rows(limit=8) if r.name not in seen][: 8 - len(featured)]

        # Premium: the highest-priced listings of the busiest purpose (prices of rent and sale
        # are not comparable with each other).
        busiest = "Sale" if c["Sale"] > c["Rent"] else "Rent"
        premium = [r for r in _listing_rows({"listing_type": busiest}, "headline_price desc", 12)
                   if r.cover][:4]

        cities = []
        for city, n in frappe.db.sql("""SELECT city, COUNT(*) n FROM `tabListing`
                WHERE is_published = 1 AND IFNULL(city, '') != '' GROUP BY city ORDER BY n DESC LIMIT 8"""):
            names = frappe.get_all("Listing", filters={"is_published": 1, "city": city}, pluck="name",
                                   order_by="featured desc, published_on desc", limit=12)
            covers = _covers(names)
            cities.append({"city": city, "count": n,
                           "cover": next((covers[nm] for nm in names if covers.get(nm)), None)})

        projects = []
        for prop, n, low, types in frappe.db.sql("""SELECT property_ref, COUNT(*), MIN(headline_price),
                GROUP_CONCAT(DISTINCT unit_type ORDER BY unit_type SEPARATOR ',')
                FROM `tabListing` WHERE is_published = 1 AND development_status = 'Under Development'
                AND IFNULL(property_ref, '') != '' GROUP BY property_ref ORDER BY MAX(published_on) DESC LIMIT 6"""):
            info = frappe.db.get_value("Property", prop, ["property_name", "city", "area", "cover_image"],
                                       as_dict=True) or {}
            names = frappe.get_all("Listing", filters={"is_published": 1, "property_ref": prop}, pluck="name", limit=6)
            covers = _covers(names)
            projects.append({
                "property": prop, "name": info.get("property_name") or prop, "city": info.get("city"),
                "locality": info.get("area"), "count": n, "from_price": low,
                "types": [t for t in (types or "").split(",") if t],
                "cover": info.get("cover_image") or next((covers[nm] for nm in names if covers.get(nm)), None)})
        return {"featured": featured, "has_featured": has_featured, "premium": premium,
                "premium_type": busiest, "cities": cities, "projects": projects}

    return _cached("home", build)


def facets():
    """Filter options with what the site really has: places, types, amenities and price range."""
    def build():
        cities = [{"value": c, "count": n} for c, n in frappe.db.sql("""SELECT city, COUNT(*) FROM `tabListing`
                  WHERE is_published = 1 AND IFNULL(city, '') != '' GROUP BY city ORDER BY COUNT(*) DESC, city""")]
        localities = [{"value": loc, "city": c, "count": n} for loc, c, n in frappe.db.sql(
            """SELECT locality, city, COUNT(*) FROM `tabListing` WHERE is_published = 1
               AND IFNULL(locality, '') != '' GROUP BY locality, city ORDER BY COUNT(*) DESC, locality LIMIT 300""")]
        types = [{"value": t, "count": n} for t, n in frappe.db.sql("""SELECT unit_type, COUNT(*) FROM `tabListing`
                 WHERE is_published = 1 AND IFNULL(unit_type, '') != '' GROUP BY unit_type ORDER BY COUNT(*) DESC""")]
        furnishing = [{"value": f, "count": n} for f, n in frappe.db.sql("""SELECT furnishing, COUNT(*) FROM `tabListing`
                 WHERE is_published = 1 AND IFNULL(furnishing, '') != '' GROUP BY furnishing ORDER BY furnishing""")]
        amenities = [{"value": a, "count": n} for a, n in frappe.db.sql(
            """SELECT pa.amenity, COUNT(DISTINCT l.name) FROM `tabListing` l
               JOIN `tabProperty Amenity` pa ON pa.parent = l.property_ref AND pa.parenttype = 'Property'
               WHERE l.is_published = 1 GROUP BY pa.amenity ORDER BY COUNT(DISTINCT l.name) DESC, pa.amenity LIMIT 40""")]
        price = {t: [flt(lo), flt(hi)] for t, lo, hi in frappe.db.sql(
            """SELECT listing_type, MIN(headline_price), MAX(headline_price) FROM `tabListing`
               WHERE is_published = 1 AND headline_price > 0 GROUP BY listing_type""")}
        flags = frappe.db.sql("""SELECT SUM(featured), SUM(IFNULL(permit_number, '') != ''),
                SUM(published_on >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)) FROM `tabListing` WHERE is_published = 1""")[0]
        area = frappe.db.sql("""SELECT MIN(area_sqm), MAX(area_sqm) FROM `tabListing`
                                WHERE is_published = 1 AND area_sqm > 0""")[0]
        return {"cities": cities, "localities": localities, "unit_types": types, "furnishing": furnishing,
                "amenities": amenities, "price": price, "featured": cint(flags[0]), "permit": cint(flags[1]),
                "new": cint(flags[2]), "area": [flt(area[0]), flt(area[1])]}

    return _cached("facets", build)


def clear_cache(doc=None, method=None):
    for key in ("counts", "home", "facets"):
        frappe.cache.delete_value(f"thinknxg_estate:{key}")


# ---------------------------------------------------------------- amenity icons

AMENITY_ICONS = (("pool", "waves"), ("swim", "waves"), ("gym", "dumbbell"), ("fitness", "dumbbell"),
                 ("park", "car"), ("garage", "car"), ("secur", "shield"), ("guard", "shield"), ("cctv", "shield"),
                 ("lift", "lift"), ("elevator", "lift"), ("garden", "tree"), ("landscap", "tree"),
                 ("power", "zap"), ("generator", "zap"), ("backup", "zap"), ("club", "users"),
                 ("play", "smile"), ("kid", "smile"), ("a/c", "wind"), ("air", "wind"), ("balcon", "sun"),
                 ("wardrobe", "door"), ("maid", "user"), ("pet", "paw"))


def amenity_icon(name):
    lowered = (name or "").lower()
    return next((icon for key, icon in AMENITY_ICONS if key in lowered), "check")


# ---------------------------------------------------------------- active filter chips

BOUND_KEYS = ("north", "south", "east", "west")


def parse_args(source):
    """The search arguments present in a request or form, as a plain dict."""
    out = {}
    for key in FILTER_KEYS:
        value = source.get(key)
        if value in (None, ""):
            continue
        # "0" means "off" for flags and counts, but is a real coordinate for the map bounds
        if value in ("0", 0) and key not in BOUND_KEYS:
            continue
        out[key] = value
    return out


def chips(args):
    """One removable chip per active filter value, with a translated label."""
    out = []

    def add(key, label, value=None):
        out.append({"key": key, "value": value, "label": label})

    if args.get("q"):
        add("q", f'"{args["q"]}"')
    if args.get("listing_type"):
        add("listing_type", _("For rent") if args["listing_type"] == "Rent" else _("For sale"))
    if args.get("usage"):
        add("usage", _(args["usage"]))
    if args.get("development_status"):
        add("development_status", _("Under construction") if args["development_status"] == "Under Development"
            else _("Ready to move"))
    preset = categories().get(args.get("category") or "")
    if preset:
        add("category", preset["label"])
    for key in ("unit_type", "city", "locality", "furnishing", "amenity"):
        for value in csv(args.get(key)):
            add(key, _(value), value)
    if args.get("bedrooms"):
        add("bedrooms", _("Studio") if str(args["bedrooms"]).lower() == "studio"
            else _("{0}+ bedrooms").format(cint(args["bedrooms"])))
    if args.get("bathrooms"):
        add("bathrooms", _("{0}+ bathrooms").format(cint(args["bathrooms"])))
    if args.get("min_price") or args.get("max_price"):
        add("price", _("Price {0} – {1}").format(args.get("min_price") or "0", args.get("max_price") or "∞"))
    if args.get("min_area") or args.get("max_area"):
        add("area", _("Area {0} – {1} sqm").format(args.get("min_area") or "0", args.get("max_area") or "∞"))
    for key, label in (("featured", _("Featured")), ("new", _("New listings")), ("permit", _("Permit on file"))):
        if args.get(key):
            add(key, label)
    if args.get("project"):
        add("project", frappe.db.get_value("Property", args["project"], "property_name") or args["project"])
    if all(args.get(k) for k in MAP_KEYS):
        add("map", _("Map area"))
    return out


# ---------------------------------------------------------------- rendered results

def page_links(page, pages):
    """Page numbers to show: first, last and a window around the current page, gaps marked 0."""
    shown = sorted({1, pages} | {p for p in range(page - 2, page + 3) if 1 <= p <= pages})
    out, prev = [], 0
    for p in shown:
        if prev and p - prev > 1:
            out.append(0)
        out.append(p)
        prev = p
    return out


def query_string(args, view="grid"):
    from urllib.parse import urlencode

    params = dict(args)
    if view != "grid":
        params["view"] = view
    return urlencode(params)


def render_pager(page, pages, args, view="grid"):
    return frappe.render_template("templates/estate/pager.html", {
        "page": page, "total_pages": pages, "page_links": page_links(page, pages),
        "qs_base": query_string(args, view)})


def render_cards(rows, layout="grid", saved=None):
    context = {"rows": rows, "layout": layout, "saved": saved or set(),
               "currency": frappe.get_cached_doc("RE Portal Settings").currency_label or "OMR",
               "new_after": str(frappe.utils.add_days(frappe.utils.nowdate(), -30))}
    return frappe.render_template("templates/includes/property_cards.html", context)


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=PUBLIC_READ_LIMIT * 2, seconds=3600)
def search_results(page=1, layout="grid", view="grid", **args):
    """One page of result cards as HTML plus the totals and filter chips, for the search page.
    The page renders the first results itself; this answers every later filter, sort and page
    change without a reload."""
    from thinknxg_estate.portal.api.visitor import saved_listing_names

    args = parse_args({k: v for k, v in args.items() if k != "cmd"})
    result = run_search(page=page, **args)
    pages = max(-(-result["total"] // result["page_size"]), 1)
    return {"html": render_cards(result["results"], "list" if layout == "list" else "grid",
                                 saved_listing_names()),
            "total": result["total"], "page": result["page"], "pages": pages,
            "pager": render_pager(result["page"], pages, args, view if view in ("grid", "list", "map") else "grid"),
            "chips": chips(args), "heading": _heading(args),
            "summary": _("{0} properties found").format(result["total"])}


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=PUBLIC_READ_LIMIT * 2, seconds=3600)
def cards_by_name(names=None, similar_to=None):
    """Cards for specific listings (recently viewed) or listings similar to one."""
    from thinknxg_estate.portal.api.visitor import saved_listing_names

    if similar_to:
        rows = similar_listings(similar_to, 4)
    else:
        wanted = csv(names)[:8]
        rows = _listing_rows({"name": ["in", wanted]}, limit=8) if wanted else []
        rows.sort(key=lambda r: wanted.index(r.name))
    return {"html": render_cards(rows, "grid", saved_listing_names()), "count": len(rows)}


def similar_listings(name, limit=4):
    """Published listings like this one: same purpose and city first, then close in price."""
    base = frappe.db.get_value("Listing", name, ["listing_type", "city", "unit_type", "headline_price"], as_dict=True)
    if not base:
        return []
    rows = _listing_rows({"name": ["!=", name], "listing_type": base.listing_type, "city": base.city},
                         order_by="featured desc, published_on desc", limit=24)
    price = flt(base.headline_price) or 1
    rows.sort(key=lambda r: ((r.unit_type != base.unit_type), abs(flt(r.headline_price) - price) / price))
    return rows[:limit]


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=PUBLIC_READ_LIMIT * 3, seconds=3600)
def suggest(q=None):
    """Search suggestions for the hero box: matching cities, localities and listing titles."""
    q = (q or "").strip()[:60]
    if len(q) < 2:
        return {"items": []}
    like = f"%{q}%"
    items = []
    for city, n in frappe.db.sql("""SELECT city, COUNT(*) FROM `tabListing` WHERE is_published = 1
            AND city LIKE %s GROUP BY city ORDER BY COUNT(*) DESC LIMIT 4""", like):
        items.append({"type": "city", "label": city, "value": city, "count": n})
    for loc, city, n in frappe.db.sql("""SELECT locality, city, COUNT(*) FROM `tabListing` WHERE is_published = 1
            AND locality LIKE %s GROUP BY locality, city ORDER BY COUNT(*) DESC LIMIT 5""", like):
        items.append({"type": "locality", "label": loc, "sub": city, "value": loc, "count": n})
    for title, route in frappe.db.sql("""SELECT title, route FROM `tabListing` WHERE is_published = 1
            AND title LIKE %s ORDER BY featured DESC, published_on DESC LIMIT 4""", like):
        items.append({"type": "listing", "label": title, "value": route})
    return {"items": items}


def seo_title(args, total=0):
    """Short, specific page title such as 'Apartments for rent in Muscat'."""
    preset = categories().get(args.get("category") or "")
    kind = preset["label"] if preset else (_("Properties") if not csv(args.get("unit_type")) else _(csv(args["unit_type"])[0]))
    purpose = {"Rent": _("for rent"), "Sale": _("for sale")}.get(args.get("listing_type"), "")
    places = csv(args.get("city")) or csv(args.get("locality"))
    where = (_("in {0}").format(", ".join(places[:2])) if places else "")
    return " ".join(p for p in (kind, purpose, where) if p)


def _heading(args):
    return seo_title(args)


def sort_options():
    return [(k, label) for k, label in (
        ("relevance", _("Relevance")), ("newest", _("Newest")), ("price_asc", _("Price: low to high")),
        ("price_desc", _("Price: high to low")), ("area_desc", _("Largest area"))) if k in SORTS]
