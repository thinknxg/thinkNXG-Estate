import frappe
from frappe import _
from frappe.utils import nowdate
from frappe.website.website_generator import WebsiteGenerator


class Listing(WebsiteGenerator):
    website = frappe._dict(
        condition_field="is_published",
        page_title_field="title",
        template="templates/generators/listing.html",
    )

    def allow_website_search_indexing(self):
        # Bulk syncs (backfill, upgrade patch, imports) index once at the end instead of queueing
        # one job per listing, which would hit the background queue's safety limit.
        if frappe.flags.estate_bulk_listing_sync:
            return False
        return super().allow_website_search_indexing()

    def autoname(self):
        # Titles repeat (two villas with the same name); keep the readable name but make it unique.
        self.name = _unique("Listing", "name", self.scrub(self.title) or "listing")

    def validate(self):
        if not self.route:
            self.route = _unique("Listing", "route", "property/" + (self.scrub(self.title) or "listing"),
                                 exclude=self.name)
        if not self.unit and not self.property_ref:
            frappe.throw(_("Choose the unit being listed, or the property if it is let as a whole."))
        if self.unit:
            self._copy_from_unit()
        else:
            self._copy_from_property()
        if self.is_published:
            self._check_available()
            if not self.published_on:
                self.published_on = nowdate()
            key = {"unit": self.unit} if self.unit else {"property_ref": self.property_ref, "unit": ["is", "not set"]}
            other = frappe.db.exists("Listing", {**key, "is_published": 1, "name": ["!=", self.name]})
            if other:
                frappe.throw(_("{0} already has a published listing ({1}).")
                             .format(self.unit or self.property_ref, other))

    def on_update(self):
        # Publishing by hand also marks the unit or property as shown on the website, so the
        # nightly sync (which honours that flag) keeps the listing up instead of taking it down.
        if self.is_published:
            doctype, name = ("Unit", self.unit) if self.unit else ("Property", self.property_ref)
            if not frappe.db.get_value(doctype, name, "published_to_portal"):
                frappe.db.set_value(doctype, name, "published_to_portal", 1, update_modified=False)

    def _copy_from_unit(self):
        unit = frappe.db.get_value(
            "Unit", self.unit, ["property", "unit_type", "bedrooms", "bathrooms", "area_sqm", "furnishing",
                                "usage"], as_dict=True)
        if not unit:
            return
        self.property_ref = unit.property
        for field in ("unit_type", "bedrooms", "bathrooms", "area_sqm", "furnishing"):
            self.set(field, unit.get(field))
        self._copy_property_facets(unit.usage)

    def _copy_from_property(self):
        prop = frappe.db.get_value(
            "Property", self.property_ref,
            ["property_type", "bedrooms", "bathrooms", "area_sqm", "furnishing", "city", "area"], as_dict=True)
        if not prop:
            return
        self.unit_type = prop.property_type
        for field in ("bedrooms", "bathrooms", "area_sqm", "furnishing"):
            self.set(field, prop.get(field))
        self.city = self.city or prop.city
        self.locality = self.locality or prop.area
        self._copy_property_facets()

    def _copy_property_facets(self, unit_usage=None):
        """Usage and development status come from the property so the website can filter on them."""
        usage, status = frappe.db.get_value("Property", self.property_ref, ["usage", "status"]) or (None, None)
        self.usage = unit_usage or usage
        self.development_status = status if status == "Under Development" else "Ready"

    def _check_available(self):
        if self.unit:
            status = frappe.db.get_value("Unit", self.unit, "status")
            if status not in ("Vacant", "Reserved"):
                frappe.throw(
                    _("Unit {0} is {1}; only Vacant or Reserved units can be published.")
                    .format(self.unit, status))
            return
        if frappe.db.exists("Unit", {"property": self.property_ref}):
            frappe.throw(_("Property {0} has units; list each unit instead of the whole property.")
                         .format(self.property_ref))
        if frappe.db.get_value("Property", self.property_ref, "current_lease"):
            frappe.throw(_("Property {0} is under a lease and cannot be published.").format(self.property_ref))

    def get_context(self, context):
        import json

        from thinknxg_estate.portal.api import catalog
        from thinknxg_estate.portal.site import site_context

        context.no_cache = 1
        site_context(context, active={"Rent": "rent", "Sale": "buy"}.get(self.listing_type))
        site = context.site
        settings = frappe.get_cached_doc("RE Portal Settings")
        context.contact_whatsapp = settings.contact_whatsapp
        context.contact_email = settings.contact_email
        context.gallery = [p.image for p in self.photos if p.image]
        context.captions = [p.caption for p in self.photos if p.image]
        context.cover = context.gallery[0] if context.gallery else None
        names = listing_amenities(self.property_ref)
        context.amenities = [{"name": a, "icon": catalog.amenity_icon(a)} for a in names]
        prop = frappe.db.get_value(
            "Property", self.property_ref,
            ["latitude", "longitude", "address_line", "property_name", "usage", "no_of_floors", "parking_slots",
             "ejari_number"], as_dict=True) or frappe._dict()
        context.update({k: prop.get(k) for k in ("latitude", "longitude", "address_line")})
        unit = (frappe.db.get_value("Unit", self.unit, ["unit_no", "floor", "parking_slots"], as_dict=True)
                if self.unit else None) or frappe._dict()
        context.floor = unit.get("floor")
        context.parking = unit.get("parking_slots") or prop.get("parking_slots")
        context.building = prop.get("property_name")
        context.total_floors = prop.get("no_of_floors")
        context.place = ", ".join(p for p in (self.locality, self.city) if p)

        similar = catalog.similar_listings(self.name, 4)
        from thinknxg_estate.portal.api.visitor import saved_listing_names

        saved = saved_listing_names()
        context.saved = saved
        context.similar_html = catalog.render_cards(similar, "grid", saved)
        context.similar_count = len(similar)
        context.min_viewing_date = frappe.utils.add_days(frappe.utils.nowdate(), 1)
        context.map_tile_url = site.map_tile_url
        context.map_attribution = site.map_attribution
        context.is_visitor = site.visitor
        context.visitor = frappe._dict()
        if site.visitor:
            from thinknxg_estate.core.listing_portal_api.listing_portal import get_current_portal_user

            context.visitor = frappe._dict(get_current_portal_user() or {})
            context.visitor.email = frappe.session.user
        context.is_saved = self.name in saved
        context.can_request_lease = bool(self.unit and self.listing_type == "Rent")
        context.new_after = str(frappe.utils.add_days(frappe.utils.nowdate(), -30))

        # Search-engine metadata: title, description, canonical, Open Graph and Schema.org markup
        title = self.meta_title or f"{self.title} – {context.place}" if context.place else (self.meta_title or self.title)
        description = (self.meta_description or catalog.excerpt(self.description, 155)
                       or _("{0} {1} in {2}.").format(_(self.unit_type or _("Property")),
                                                      _("for rent") if self.listing_type == "Rent" else _("for sale"),
                                                      context.place or site.title))
        url = frappe.utils.get_url("/" + self.route)
        context.title = f"{title} | {site.title}"
        context.canonical = url
        context.metatags = {"title": context.title, "description": description, "og:title": context.title,
                            "og:description": description, "og:type": "website", "og:url": url,
                            "twitter:card": "summary_large_image" if context.cover else "summary"}
        if context.cover:
            context.metatags["og:image"] = frappe.utils.get_url(context.cover)
        offer = {"@type": "Offer", "price": float(self.headline_price or 0), "priceCurrency": site.currency,
                 "availability": "https://schema.org/InStock", "url": url}
        if self.listing_type == "Rent" and self.price_period:
            offer["priceSpecification"] = {"@type": "UnitPriceSpecification", "price": float(self.headline_price or 0),
                                           "priceCurrency": site.currency,
                                           "unitText": {"Per Year": "YEAR", "Per Month": "MONTH"}.get(self.price_period, "YEAR")}
        residence = {"@type": "Residence" if (self.usage or "Residential") == "Residential" else "Accommodation",
                     "name": self.title, "url": url, "description": description,
                     "image": [frappe.utils.get_url(g) for g in context.gallery[:6]],
                     "address": {"@type": "PostalAddress", "addressLocality": self.city or "",
                                 "streetAddress": prop.get("address_line") or self.locality or ""},
                     "numberOfBedrooms": self.bedrooms or 0, "numberOfBathroomsTotal": self.bathrooms or 0}
        if self.area_sqm:
            residence["floorSize"] = {"@type": "QuantitativeValue", "value": float(self.area_sqm), "unitCode": "MTK"}
        if prop.get("latitude") and prop.get("longitude"):
            residence["geo"] = {"@type": "GeoCoordinates", "latitude": prop.latitude, "longitude": prop.longitude}
        crumbs = [(_("Properties"), frappe.utils.get_url("/properties"))]
        if self.listing_type:
            crumbs.append((_("For rent") if self.listing_type == "Rent" else _("For sale"),
                           frappe.utils.get_url(f"/properties?listing_type={self.listing_type}")))
        if self.city:
            crumbs.append((self.city, frappe.utils.get_url("/properties?city=" + frappe.utils.quote(self.city))))
        crumbs.append((self.title, url))
        context.crumbs = crumbs
        context.jsonld = json.dumps({"@context": "https://schema.org", "@graph": [
            {"@type": ["Product", "RealEstateListing"], "name": self.title, "url": url, "description": description,
             "image": residence["image"], "offers": offer, "about": residence},
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": name, "item": link} for i, (name, link) in enumerate(crumbs)]}]})
        return context


def _unique(doctype, field, base, exclude=None):
    value, n = base, 1
    while True:
        filters = [[field, "=", value]]
        if exclude:
            filters.append(["name", "!=", exclude])
        if not frappe.db.exists(doctype, filters):
            break
        n += 1
        value = f"{base}-{n}"
    return value


def listing_amenities(property_name):
    if not property_name:
        return []
    return frappe.get_all("Property Amenity", filters={"parent": property_name}, pluck="amenity")


def unpublish_unit_listings(doc, method=None):
    """doc_events hook: Lease Contract on_submit -> take the unit (or whole property) off the market."""
    filters = {"unit": doc.unit} if doc.unit else {"property_ref": doc.property, "unit": ["is", "not set"]}
    for name in frappe.get_all("Listing",
                               filters={**filters, "is_published": 1},
                               pluck="name"):
        frappe.db.set_value("Listing", name, "is_published", 0)
        frappe.get_doc("Listing", name).add_comment(
            "Comment", _("Auto-unpublished: lease {0} submitted.").format(doc.name))
