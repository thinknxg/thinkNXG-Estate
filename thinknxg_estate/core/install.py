import frappe


def after_install():
    _ensure_rent_item()
    _seed_amenities()


def _ensure_rent_item():
    """Create the non-stock service item used for rent invoicing and wire it into Property Settings.

    On a fresh thinkNXG ERP site the setup wizard has not created Item Groups / UOMs yet; in that
    case this is skipped and retried by after_migrate (and on first rent invoicing run)."""
    ensure_rent_item()


def ensure_rent_item():
    if not frappe.db.exists("Item", "Rental Charge"):
        item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
        uom = frappe.db.exists("UOM", "Nos") or frappe.db.get_value("UOM", {}, "name")
        if not (item_group and uom):
            return None
        item = frappe.new_doc("Item")
        item.item_code = "Rental Charge"
        item.item_name = "Rental Charge"
        item.item_group = item_group
        item.is_stock_item = 0
        item.is_sales_item = 1
        item.is_purchase_item = 0
        item.stock_uom = uom
        item.insert(ignore_permissions=True)

    settings = frappe.get_single("Property Settings")
    if not settings.rent_item:
        settings.rent_item = "Rental Charge"
        settings.save(ignore_permissions=True)
    return "Rental Charge"


def _seed_amenities():
    defaults = [
        "Covered Parking", "Swimming Pool", "Gym", "Central A/C", "Balcony",
        "Maid Room", "Security 24/7", "Elevator", "Kids Play Area", "Garden",
        "Built-in Wardrobes", "Pets Allowed",
    ]
    for name in defaults:
        if not frappe.db.exists("Amenity", name):
            frappe.get_doc({"doctype": "Amenity", "amenity_name": name}).insert(ignore_permissions=True)
