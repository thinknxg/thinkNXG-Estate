"""Administrator actions for the portal theme module (Portal Theme and Portal Theme Settings forms).
Every method needs the RE Manager or System Manager role."""

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from thinknxg_estate.portal import themes


def _guard():
    frappe.only_for(themes.ADMIN_ROLES)


@frappe.whitelist()
def templates():
    """The built-in templates, for the gallery."""
    _guard()
    out = []
    for name, tpl in themes.TEMPLATES.items():
        v = tpl["values"]
        out.append({"name": name, "label": tpl["label"], "description": tpl["description"],
                    "swatches": [v["primary_color"], v["accent_color"], v["background_color"], v["surface_color"]],
                    "dark": v["tone"] == "Dark", "hero": v["hero_style"], "cards": v["card_style"]})
    return out


@frappe.whitelist()
def gallery():
    """Everything the settings page shows: templates, saved themes and which one is live."""
    _guard()
    live = themes.active_theme_name()
    rows = frappe.get_all("Portal Theme", fields=["name", "template", "is_live", "modified", "published_on", "description"],
                          order_by="is_live desc, modified desc")
    for r in rows:
        r["has_previous"] = bool(frappe.db.get_value("Portal Theme", r["name"], "previous_snapshot"))
        r["live"] = r["name"] == live
    return {"templates": templates(), "themes": rows, "live": live}


@frappe.whitelist()
def create_from_template(template, theme_name=None):
    _guard()
    if template not in themes.TEMPLATES:
        frappe.throw(_("Unknown template."))
    base = theme_name or themes.TEMPLATES[template]["label"]
    name, i = base, 2
    while frappe.db.exists("Portal Theme", name):
        name = f"{base} {i}"
        i += 1
    doc = frappe.get_doc({"doctype": "Portal Theme", "theme_name": name, "template": template}).insert()
    return doc.name


@frappe.whitelist()
def apply_template(theme, template=None, keep_content=1):
    """Reset a theme's design to a template. With keep_content the section titles, links, branding
    and text stay; the section order and switches also reset because they belong to the template."""
    _guard()
    doc = frappe.get_doc("Portal Theme", theme)
    doc.check_permission("write")
    if template:
        if template not in themes.TEMPLATES:
            frappe.throw(_("Unknown template."))
        doc.template = template
    doc.fill_from_template(overwrite=True)
    if not cint(keep_content):
        for f in themes.FREE_FIELDS:
            doc.set(f, "")
        doc.set("links", [])
    doc.save()
    return doc.name


@frappe.whitelist()
def duplicate(theme, new_name):
    _guard()
    new_name = (new_name or "").strip()
    if not new_name:
        frappe.throw(_("Enter a name for the copy."))
    if frappe.db.exists("Portal Theme", new_name):
        frappe.throw(_("A theme named {0} already exists.").format(new_name))
    src = frappe.get_doc("Portal Theme", theme)
    doc = frappe.copy_doc(src)
    doc.theme_name = new_name
    doc.is_live = 0
    doc.insert()
    return doc.name


@frappe.whitelist()
def publish(theme):
    """Make a theme live. The theme is validated and a resolved copy stored; visitors see that copy."""
    _guard()
    return _publish(theme)


def publish_as_system(theme):
    """Publish without a role check (first-time setup only)."""
    return _publish(theme, check=False)


def _publish(theme, check=True):
    doc = frappe.get_doc("Portal Theme", theme)
    if check:
        doc.check_permission("write")
    doc.run_method("validate")  # contrast, links and CSS are re-checked
    snapshot = themes.snapshot_of(doc)

    previous = themes.active_theme_name()
    if previous and previous != doc.name:
        frappe.db.set_value("Portal Theme", previous, "is_live", 0, update_modified=False)
        themes.clear_cache(previous)
    doc.db_set({"previous_snapshot": doc.published_snapshot or "", "published_snapshot": snapshot, "is_live": 1,
                "published_on": now_datetime(), "published_by": frappe.session.user})
    frappe.db.set_single_value("Portal Theme Settings", {"active_theme": doc.name, "published_on": now_datetime(),
                                                         "published_by": frappe.session.user})
    frappe.clear_document_cache("Portal Theme Settings", "Portal Theme Settings")
    themes.clear_cache(doc.name)
    doc.add_comment("Info", _("Published by {0}").format(frappe.session.user))
    clear_site_cache()
    return {"live": doc.name}


@frappe.whitelist()
def revert(theme):
    """Go back to the copy that was live before the last publish of this theme."""
    _guard()
    doc = frappe.get_doc("Portal Theme", theme)
    doc.check_permission("write")
    if not doc.previous_snapshot:
        frappe.throw(_("There is no earlier published version of this theme."))
    doc.db_set({"published_snapshot": doc.previous_snapshot, "previous_snapshot": doc.published_snapshot or "",
                "published_on": now_datetime(), "published_by": frappe.session.user})
    themes.clear_cache(doc.name)
    doc.add_comment("Info", _("Reverted to the previous published version by {0}").format(frappe.session.user))
    clear_site_cache()
    return {"live": themes.active_theme_name()}


@frappe.whitelist()
def preview_links(theme):
    """Pages to preview, with the preview parameter attached."""
    _guard()
    if not frappe.db.exists("Portal Theme", theme):
        frappe.throw(_("Theme not found."))
    from urllib.parse import quote

    q = "theme_preview=" + quote(theme)
    first = frappe.db.get_value("Listing", {"is_published": 1}, "route")
    pages = [("home", _("Home"), f"/properties?{q}"),
             ("search", _("Search results"), f"/properties?listing_type=Rent&{q}"),
             ("map", _("Map"), f"/properties?view=map&{q}")]
    if first:
        pages.append(("property", _("Property page"), f"/{first}?{q}"))
    pages.append(("account", _("Account"), f"/properties/account?{q}"))
    return [{"key": k, "label": label, "url": url} for k, label, url in pages]


def clear_site_cache():
    from thinknxg_estate.portal.api import catalog

    catalog.clear_cache()
