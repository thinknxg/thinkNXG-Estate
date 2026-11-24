"""One public website: /listings is retired in favour of /properties, which reads Listing records.

/properties used to publish a unit whenever its property was live; /listings also required the
unit's "Published to Portal" flag. The merged site uses both rules, so units that are already
published as Listings get the flag set here and nothing visible today disappears. A backfill
then creates Listings for anything /listings showed that had no Listing yet, including whole
properties with no units."""

import frappe


def execute():
    units = frappe.get_all("Listing", filters={"is_published": 1, "unit": ["is", "set"]}, pluck="unit")
    if units:
        frappe.db.set_value("Unit", {"name": ["in", units], "published_to_portal": 0},
                            "published_to_portal", 1, update_modified=False)

    from thinknxg_estate.portal.sync import backfill_all

    backfill_all()
