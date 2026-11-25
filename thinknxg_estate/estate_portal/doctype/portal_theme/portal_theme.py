import frappe
from frappe import _
from frappe.model.document import Document

from thinknxg_estate.portal import themes


class PortalTheme(Document):
    def before_insert(self):
        self.is_live = 0
        self.fill_from_template(overwrite=False)

    def validate(self):
        self.theme_name = (self.theme_name or "").strip()
        for field in ("primary_color", "accent_color", "background_color", "surface_color", "text_color", "heading_color"):
            value = self.get(field)
            if value and not themes.HEX.match(value):
                frappe.throw(_("{0} must be a hex colour such as #0b1f3a.").format(self.meta.get_label(field)))
        for row in self.links:
            if not themes.safe_url(row.url):
                frappe.throw(_("Row {0}: the link must start with /, https://, mailto: or tel:.").format(row.idx))
        self.hero_overlay = min(max(frappe.utils.cint(self.hero_overlay), 0), 90) if self.hero_overlay else 0
        self.tidy_sections()
        self.custom_css = themes.clean_css(self.custom_css)
        self.check_contrast()

    def tidy_sections(self):
        seen = set()
        for row in list(self.sections):
            if row.section_key in seen:
                self.remove(row)
            seen.add(row.section_key)
        if self.sections:
            for row in self.sections:
                if row.section_key == "hero":
                    row.enabled = 1  # the search lives in the hero
            heroes = [r for r in self.sections if r.section_key == "hero"]
            if not heroes:
                self.append("sections", {"section_key": "hero", "enabled": 1})
            self.sections.sort(key=lambda r: r.section_key != "hero")
            for i, row in enumerate(self.sections, 1):
                row.idx = i

    def check_contrast(self):
        errors, warnings = themes.contrast_problems(themes.resolve(self))
        if errors:
            frappe.throw("<br>".join(errors), title=_("Colours are hard to read"))
        for w in warnings:
            frappe.msgprint(w, indicator="orange", alert=True)

    def fill_from_template(self, overwrite=False, content=False):
        tpl = themes.template_values(self.template)
        for key, value in tpl["values"].items():
            if overwrite or self.get(key) in (None, "", 0):
                self.set(key, value)
        if overwrite or not self.sections:
            if overwrite or content or not self.sections:
                self.set("sections", [])
                for s in themes.default_sections(self.template):
                    self.append("sections", s)

    def on_update(self):
        themes.clear_cache(self.name)

    def on_trash(self):
        if self.is_live:
            frappe.throw(_("This is the live theme. Publish another theme first, then delete this one."))

    def after_delete(self):
        themes.clear_cache(self.name)
