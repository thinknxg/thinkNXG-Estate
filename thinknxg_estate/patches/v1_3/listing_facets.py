"""Fill the new Listing usage and development status columns from each listing's property, so the
redesigned /properties filters (Residential/Commercial, ready or under construction) work on
listings that existed before the upgrade."""

import frappe


def execute():
    frappe.reload_doc("estate_portal", "doctype", "listing")
    from thinknxg_estate.portal.sync import refresh_listing_facets

    refresh_listing_facets()
