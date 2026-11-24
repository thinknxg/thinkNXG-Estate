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
            "Unit", self.unit, ["property", "unit_type", "bedrooms", "bathrooms", "area_sqm", "furnishing"],
            as_dict=True)
        if not unit:
            return
        self.property_ref = unit.property
        for field in ("unit_type", "bedrooms", "bathrooms", "area_sqm", "furnishing"):
            self.set(field, unit.get(field))

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
        context.no_cache = 1
        context.parents = [{"route": "properties", "label": _("Properties")}]
        settings = frappe.get_cached_doc("RE Portal Settings")
        context.currency = settings.currency_label or "OMR"
        context.contact_whatsapp = settings.contact_whatsapp
        context.cover = (self.photos[0].image if self.photos else None)
        context.gallery = [p.image for p in self.photos]
        context.amenities = listing_amenities(self.property_ref)
        prop = frappe.db.get_value(
            "Property", self.property_ref,
            ["latitude", "longitude", "address_line"], as_dict=True) or frappe._dict()
        context.update(prop)
        context.related = frappe.get_all(
            "Listing",
            filters={"is_published": 1, "name": ["!=", self.name], "listing_type": self.listing_type,
                     "city": self.city},
            fields=["title", "route", "headline_price", "price_period", "unit_type", "bedrooms", "locality"],
            order_by="featured desc, published_on desc", limit=3)
        for row in context.related:
            row["cover"] = frappe.db.get_value("Listing Photo", {"parent": frappe.db.get_value(
                "Listing", {"route": row.route}, "name")}, "image", order_by="idx asc")
        context.min_viewing_date = frappe.utils.add_days(frappe.utils.nowdate(), 1)
        context.map_tile_url = settings.get("map_tile_url") or "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        context.map_attribution = settings.get("map_attribution") or "&copy; OpenStreetMap contributors"
        user = frappe.session.user
        context.is_visitor = user != "Guest" and frappe.db.get_value("User", user, "user_type") == "Website User"
        context.visitor = frappe._dict()
        if context.is_visitor:
            from thinknxg_estate.core.listing_portal_api.listing_portal import get_current_portal_user
            from thinknxg_estate.portal.api.visitor import saved_listing_names

            context.visitor = frappe._dict(get_current_portal_user() or {})
            context.visitor.email = user
            context.is_saved = self.name in saved_listing_names()
        context.can_request_lease = bool(self.unit and self.listing_type == "Rent")
        context.metatags = {
            "title": self.meta_title or self.title,
            "description": self.meta_description or frappe.utils.strip_html(
                self.description or "")[:150],
        }
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
