"""The public property site: a landing page, and a search page with filters, grid / list / map
views, sorting and saved searches. Both are one route (/properties); a request with filters,
a page number or a view shows results, a bare request shows the landing page.

The first page of results is rendered here (so search engines and slow connections get real
content); later filter, sort and page changes use catalog.search_results without a reload."""

import json

import frappe
from frappe import _
from frappe.utils import cint, flt

from thinknxg_estate.portal.api import catalog
from thinknxg_estate.portal.api.catalog import seo_title
from thinknxg_estate.portal.api.listings import PUBLIC_READ_LIMIT, categories, csv, run_search  # noqa: F401
from thinknxg_estate.portal.api.visitor import saved_listing_names
from thinknxg_estate.portal.site import site_context

NOINDEX_KEYS = {"q", "sort", "north", "south", "east", "west", "featured", "new", "permit", "furnishing", "amenity",
                "bedrooms", "bathrooms", "min_price", "max_price", "min_area", "max_area", "locality"}
VIEWS = ("grid", "list", "map")


def active_nav(args):
    if args.get("listing_type") == "Rent":
        return "rent"
    if args.get("listing_type") == "Sale":
        return "buy"
    if args.get("development_status") == "Under Development":
        return "projects"
    if args.get("usage") == "Commercial" or args.get("category") in ("offices", "shops", "warehouses", "commercial"):
        return "commercial"


def canonical(args, page, view, default="grid"):
    from urllib.parse import urlencode

    keep = {k: v for k, v in sorted(args.items()) if k not in ("sort", "north", "south", "east", "west")}
    if cint(page) > 1:
        keep["page"] = cint(page)
    if view != default:
        keep["view"] = view
    url = frappe.utils.get_url("/properties")
    return url + ("?" + urlencode(keep) if keep else "")


def get_context(context):
    context.no_cache = 1
    form = frappe.form_dict
    args = catalog.parse_args(form)
    default_view = catalog.default_view()
    view = form.get("view") if form.get("view") in VIEWS else default_view
    from thinknxg_estate.portal import themes

    if view == "map" and not themes.current_theme()[0].enable_map_view:
        view = default_view if default_view != "map" else "grid"
    page = max(cint(form.get("page")), 1)
    searching = bool(args) or cint(form.get("page")) > 0 or form.get("view") in VIEWS
    site_context(context, active=active_nav(args) if searching else None)
    site = context.site
    context.mode = "results" if searching else "home"
    context.args = args
    context.view = view
    context.default_view = default_view
    context.saved = saved_listing_names()
    context.new_after = str(frappe.utils.add_days(frappe.utils.nowdate(), -30))
    settings = frappe.get_cached_doc("RE Portal Settings")
    context.facets = catalog.facets()
    context.price_bounds = context.facets["price"]
    context.category_cards = catalog.category_cards()
    base_url = frappe.utils.get_url("/properties")

    if context.mode == "home":
        home = catalog.home_data()
        context.home = home
        theme = site.theme
        context.title = _(theme.seo_title) if theme.seo_title else f"{site.title}: {_('Find properties to rent and buy')}"
        description = _(theme.seo_description) if theme.seo_description else (
            site.tagline or _("Discover exceptional properties and request a viewing online."))
        image = theme.og_image or next((r.cover for r in home["featured"] if r.cover), None)
        context.metatags = _meta(context.title, description, base_url, image)
        context.canonical = base_url
        context.jsonld = json.dumps({"@context": "https://schema.org", "@graph": [
            {"@type": "WebSite", "name": site.title, "url": base_url,
             "potentialAction": {"@type": "SearchAction", "target": base_url + "?q={search_term_string}",
                                 "query-input": "required name=search_term_string"}},
            {"@type": "Organization", "name": site.title, "url": frappe.utils.get_url(),
             "logo": frappe.utils.get_url("/assets/thinknxg_estate/images/thinknxg_estate_logo.svg")}]})
        return context

    result = run_search(page=page, **args)
    context.results = result["results"]
    context.total = result["total"]
    context.page = result["page"]
    context.total_pages = max(-(-result["total"] // result["page_size"]), 1)
    context.chips = catalog.chips(args)
    context.sorts = catalog.sort_options()
    context.sort = args.get("sort") or "relevance"
    context.cards_html = catalog.render_cards(result["results"], "list" if view == "list" else "grid", context.saved)
    heading = seo_title(args, result["total"])
    context.heading = heading
    context.title = f"{heading} | {site.title}"
    description = _("{0} listings: {1}. Compare prices, photos and locations, and request a viewing online.").format(
        result["total"], heading.lower())
    image = next((r.cover for r in result["results"] if r.cover), None)
    context.metatags = _meta(context.title, description, canonical(args, page, view, default_view), image)
    if view != default_view or (set(args) & NOINDEX_KEYS and len(args) > 2) or page > 3:
        context.metatags["robots"] = "noindex, follow"
    context.canonical = canonical(args, page, default_view if view in ("grid", "list") else view, default_view)
    context.jsonld = json.dumps({"@context": "https://schema.org", "@type": "ItemList", "name": heading,
        "numberOfItems": result["total"],
        "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": frappe.utils.get_url("/" + r.route),
                             "name": r.title} for i, r in enumerate(result["results"])]})
    context.filters_active = len([c for c in context.chips if c["key"] not in ("q",)])
    context.page_links = catalog.page_links(page, context.total_pages)
    context.qs_base = catalog.query_string(args, view)
    context.sel = {k: csv(args.get(k)) for k in catalog.MULTI_KEYS}
    context.map_lat = settings.get("map_default_lat") or 23.588
    context.map_lng = settings.get("map_default_lng") or 58.3829
    context.map_zoom = settings.get("map_default_zoom") or 11
    context.facet_json = json.dumps({"price": context.price_bounds, "localities": context.facets["localities"]})
    return context


def _meta(title, description, url, image=None):
    meta = {"title": title, "description": description, "og:title": title, "og:description": description,
            "og:type": "website", "og:url": url, "twitter:card": "summary_large_image" if image else "summary"}
    if image:
        meta["og:image"] = frappe.utils.get_url(image)
    return meta
