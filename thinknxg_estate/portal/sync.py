"""
Keeps public Listings in step with Property and Unit records.

A unit gets a published Listing when all of these hold:
- its Property is live (Property.is_live),
- the unit is marked for the website (Unit.published_to_portal),
- the unit is Vacant or Reserved,
- the unit has an annual rent.

A property with no units (a villa or shop let as one) gets its own Listing when it is live,
marked for the website, not under a lease, and has an annual rent.

When a rule stops holding the listing is unpublished, never deleted, and the sync never
overwrites a manager's photos, description or price on an existing Listing.
"""

import frappe
from frappe import _
from frappe.utils import nowdate

ELIGIBLE_STATUSES = ("Vacant", "Reserved")


class bulk_listing_sync:
    """Context manager for syncing many listings at once: per-listing website-search indexing is
    skipped and one full reindex is queued at the end."""

    def __enter__(self):
        self.outer = frappe.flags.estate_bulk_listing_sync
        frappe.flags.estate_bulk_listing_sync = True
        return self

    def __exit__(self, *exc):
        frappe.flags.estate_bulk_listing_sync = self.outer
        if not self.outer and not exc[0] and frappe.get_meta("Listing").index_web_pages_for_search:
            frappe.enqueue("frappe.search.website_search.build_index_for_all_routes", queue="long",
                           job_id="thinknxg_estate_listing_reindex", deduplicate=True,
                           enqueue_after_commit=True)
        return False


PROPERTY_TRIGGERS = ("is_live", "published_to_portal", "current_lease", "annual_rent", "status")


def sync_property_on_update(doc, method=None):
    """doc_events hook: Property on_update -> re-sync its units (or itself) when a rule input changes."""
    if not any(doc.has_value_changed(f) for f in PROPERTY_TRIGGERS):
        return
    _sync_property(doc.name, doc.is_live)


def sync_unit_on_update(doc, method=None):
    """doc_events hook: Unit on_update -> re-check this unit's listing eligibility."""
    if not doc.property:
        return
    is_live = frappe.db.get_value("Property", doc.property, "is_live")
    _sync_unit(doc.name, doc.status, is_live)
    # The first unit added to a property ends its whole-property listing.
    _sync_standalone(doc.property)


def _sync_property(property_name, is_live):
    units = frappe.get_all("Unit", filters={"property": property_name}, fields=["name", "status"])
    with bulk_listing_sync():
        for u in units:
            _sync_unit(u.name, u.status, is_live)
        _sync_standalone(property_name)


def _existing_listing(filters):
    """Most relevant existing Listing for a unit or property, if any (published one wins ties)."""
    rows = frappe.get_all(
        "Listing", filters=filters, fields=["name", "is_published"],
        order_by="is_published desc, modified desc", limit=1,
    )
    return rows[0] if rows else None


def _unpublish(existing, reason):
    if existing and existing.is_published:
        frappe.db.set_value("Listing", existing.name, "is_published", 0)
        frappe.get_doc("Listing", existing.name).add_comment("Comment", reason)


def _publish(existing, make):
    if existing:
        if not existing.is_published:
            frappe.db.set_value("Listing", existing.name, {"is_published": 1, "published_on": nowdate()})
        return
    listing = make()
    listing.is_published = 1
    listing.published_on = nowdate()
    listing.flags.ignore_permissions = True
    listing.insert(ignore_permissions=True)


def _new_listing(title, property_name, rent):
    city, area = frappe.db.get_value("Property", property_name, ["city", "area"])
    listing = frappe.new_doc("Listing")
    listing.title = title
    listing.property_ref = property_name
    listing.listing_type = "Rent"
    listing.headline_price = rent
    listing.price_period = "Per Year"  # matches annual_rent's period
    listing.city = city
    listing.locality = area
    for p in frappe.get_all("Property Photo", filters={"parent": property_name},
                            fields=["image", "caption"], order_by="is_cover desc, idx asc"):
        listing.append("photos", {"image": p.image, "caption": p.caption})
    return listing


def _sync_unit(unit_name, unit_status, property_is_live):
    unit = frappe.db.get_value("Unit", unit_name, ["published_to_portal", "annual_rent", "unit_title", "property"],
                               as_dict=True)
    existing = _existing_listing({"unit": unit_name})
    if not (property_is_live and unit.published_to_portal and unit_status in ELIGIBLE_STATUSES):
        _unpublish(existing, _("Auto-unpublished: property not live, unit not shown on the website, "
                               "or unit not Vacant/Reserved."))
        return
    if not unit.annual_rent:
        if existing and existing.is_published:
            _unpublish(existing, _("Auto-unpublished: Unit.annual_rent is blank."))
        else:
            frappe.log_error(title="thinkNXG Estate: listing auto-publish skipped",
                             message=f"Unit {unit_name} is eligible but has no annual_rent set.")
        return

    def make():
        listing = _new_listing(unit.unit_title or unit_name, unit.property, unit.annual_rent)
        listing.unit = unit_name
        return listing

    _publish(existing, make)


def _sync_standalone(property_name):
    """Whole-property listing for a property with no units."""
    existing = _existing_listing({"property_ref": property_name, "unit": ["is", "not set"]})
    if frappe.db.exists("Unit", {"property": property_name}):
        _unpublish(existing, _("Auto-unpublished: the property now has units, which are listed separately."))
        return
    prop = frappe.db.get_value(
        "Property", property_name,
        ["is_live", "published_to_portal", "current_lease", "annual_rent", "status", "property_name"],
        as_dict=True)
    eligible = (prop.is_live and prop.published_to_portal and not prop.current_lease
                and prop.status in (None, "", "Active") and prop.annual_rent)
    if not eligible:
        _unpublish(existing, _("Auto-unpublished: property not live, not shown on the website, "
                               "leased, or without an annual rent."))
        return
    _publish(existing, lambda: _new_listing(prop.property_name or property_name, property_name,
                                            prop.annual_rent))


def backfill_all():
    """Safety-net backfill: re-run Property -> Listing sync for every Property.

    Catches any Units/Properties whose eligibility changed without going
    through the normal on_update hooks (bulk SQL updates, data imports,
    console scripts, etc. all bypass on_update). Runs nightly via the
    scheduler; also exposed via run_backfill() for on-demand manual use.
    """
    properties = frappe.get_all("Property", fields=["name", "is_live"])
    with bulk_listing_sync():
        for p in properties:
            _sync_property(p.name, p.is_live)
    frappe.db.commit()
    frappe.logger("thinknxg_estate").info(
        f"Listing backfill complete: checked {len(properties)} properties."
    )
    return {"ok": True, "properties_checked": len(properties)}


@frappe.whitelist()
def run_backfill():
    """Manually triggerable version of backfill_all(), restricted to System Managers."""
    if "System Manager" not in frappe.get_roles():
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    return backfill_all()
