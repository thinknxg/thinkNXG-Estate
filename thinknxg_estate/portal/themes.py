"""Theme engine for the public property site.

A Portal Theme record holds the choices an administrator makes (colours, layout, sections,
branding). This module turns a theme into what the site needs: a resolved settings dict, a block
of CSS variables, and the layout switches the templates read.

* Four built-in templates give every field a starting value. Empty fields on a theme fall back to
  its template, so a theme never renders half-styled.
* "Publish" stores a resolved copy (the snapshot) on the theme; visitors see the snapshot, so
  unsaved edits and drafts never reach the live site. Authorised users can preview a draft.
"""

import json
import re

import frappe
from frappe import _
from frappe.utils import cint

ADMIN_ROLES = ("RE Manager", "System Manager")
PREVIEW_COOKIE = "eb_theme_preview"
SECTION_KEYS = ("hero", "categories", "featured", "locations", "projects", "premium", "trust", "cta")

TEXT_FIELDS = (
    "primary_color", "accent_color", "background_color", "surface_color", "text_color", "heading_color",
    "tone", "font_style", "font_scale", "corner_style", "button_style", "shadow_style", "header_style",
    "hero_style", "card_style", "results_columns", "filters_layout", "default_view", "detail_layout")
CHECK_FIELDS = ("header_sticky", "show_hero_stats", "show_popular_searches", "enable_map_view",
                "enable_compare", "show_similar", "show_recently_viewed", "show_powered_by")
FREE_FIELDS = ("brand_name", "tagline", "logo", "favicon", "footer_text", "hero_headline", "hero_subtext",
               "hero_image", "cta_title", "cta_text", "cta_primary_label", "cta_primary_url",
               "cta_secondary_label", "cta_secondary_url", "seo_title", "seo_description", "og_image")

LIGHT = dict(background_color="#f8fafc", surface_color="#ffffff", text_color="#334155",
             heading_color="#0f1b2d", tone="Light")


def _sections(*rows):
    return [{"section_key": k, "enabled": cint(on)} for k, on in rows]


TEMPLATES = {
    "Classic": {
        "label": "Classic Navy",
        "description": "Deep navy hero, teal accents, rounded cards and a left filter sidebar. Balanced and familiar.",
        "values": dict(LIGHT, primary_color="#0b1f3a", accent_color="#0d9488", font_style="Modern sans",
                       font_scale="Default", corner_style="Soft", button_style="Rounded", shadow_style="Soft",
                       header_style="Light", hero_style="Centered", card_style="Classic", results_columns="2",
                       filters_layout="Sidebar", default_view="Grid", detail_layout="Sidebar",
                       header_sticky=1, show_hero_stats=1, show_popular_searches=1, enable_map_view=1,
                       enable_compare=1, show_similar=1, show_recently_viewed=1, show_powered_by=1),
        "sections": _sections(("hero", 1), ("categories", 1), ("featured", 1), ("locations", 1), ("projects", 1),
                              ("premium", 1), ("trust", 1), ("cta", 1)),
    },
    "Modern": {
        "label": "Modern Light",
        "description": "Bright and airy. Split hero with a photo, pill buttons, round corners and a slim list of sections.",
        "values": dict(LIGHT, background_color="#ffffff", surface_color="#ffffff", text_color="#3b4658",
                       heading_color="#101828", primary_color="#14213d", accent_color="#0f766e",
                       font_style="System", font_scale="Default", corner_style="Round", button_style="Pill",
                       shadow_style="Soft", header_style="Light", hero_style="Split", card_style="Classic",
                       results_columns="3", filters_layout="Drawer", default_view="Grid", detail_layout="Stacked",
                       header_sticky=1, show_hero_stats=0, show_popular_searches=1, enable_map_view=1,
                       enable_compare=1, show_similar=1, show_recently_viewed=1, show_powered_by=1),
        "sections": _sections(("hero", 1), ("featured", 1), ("categories", 1), ("locations", 1), ("trust", 1),
                              ("cta", 1), ("projects", 0), ("premium", 0)),
    },
    "Luxury": {
        "label": "Dark Luxury",
        "description": "Charcoal and gold with serif headings and image-led cards, for premium and high-end portfolios.",
        "values": dict(tone="Dark", background_color="#0d1117", surface_color="#161c26", text_color="#c3ccd9",
                       heading_color="#ffffff", primary_color="#10141c", accent_color="#c9a24b",
                       font_style="Serif headings", font_scale="Default", corner_style="Sharp", button_style="Square",
                       shadow_style="None", header_style="Dark", hero_style="Centered", card_style="Immersive",
                       results_columns="3", filters_layout="Sidebar", default_view="Grid", detail_layout="Sidebar",
                       header_sticky=1, show_hero_stats=1, show_popular_searches=1, enable_map_view=1,
                       enable_compare=1, show_similar=1, show_recently_viewed=1, show_powered_by=1),
        "sections": _sections(("hero", 1), ("premium", 1), ("featured", 1), ("locations", 1), ("projects", 1),
                              ("cta", 1), ("categories", 0), ("trust", 0)),
    },
    "Marketplace": {
        "label": "Marketplace",
        "description": "Dense and search-first. Compact hero, three columns, list view by default, built for large inventories.",
        "values": dict(LIGHT, background_color="#f1f5f9", primary_color="#1e293b", accent_color="#2563eb",
                       font_style="System", font_scale="Compact", corner_style="Soft", button_style="Rounded",
                       shadow_style="None", header_style="Dark", hero_style="Compact", card_style="Compact",
                       results_columns="3", filters_layout="Sidebar", default_view="List", detail_layout="Sidebar",
                       header_sticky=1, show_hero_stats=0, show_popular_searches=1, enable_map_view=1,
                       enable_compare=1, show_similar=1, show_recently_viewed=1, show_powered_by=1),
        "sections": _sections(("hero", 1), ("categories", 1), ("featured", 1), ("locations", 1), ("cta", 1),
                              ("projects", 0), ("premium", 0), ("trust", 0)),
    },
}
TEMPLATE_NAMES = tuple(TEMPLATES)

FONTS = {
    "Modern sans": ('"InterVariable", "Inter", system-ui, -apple-system, "Segoe UI", Tahoma, sans-serif', None),
    "System": ('system-ui, -apple-system, "Segoe UI", Roboto, Tahoma, sans-serif', None),
    "Serif headings": ('"InterVariable", "Inter", system-ui, -apple-system, "Segoe UI", Tahoma, sans-serif',
                       'Georgia, "Times New Roman", "Noto Naskh Arabic", serif'),
}
CORNERS = {"Sharp": (4, 3), "Soft": (16, 12), "Round": (24, 16)}
BUTTONS = {"Rounded": "12px", "Pill": "999px", "Square": "4px"}
SCALES = {"Compact": "15px", "Default": "16px", "Large": "17px"}
SHADOWS = {
    "None": ("none", "none", "0 10px 30px -14px rgba(0,0,0,.35)"),
    "Soft": ("0 1px 2px rgba(11,31,58,.05)", "0 1px 2px rgba(11,31,58,.04), 0 10px 30px -12px rgba(11,31,58,.18)",
             "0 2px 4px rgba(11,31,58,.05), 0 24px 48px -16px rgba(11,31,58,.28)"),
    "Raised": ("0 2px 6px rgba(11,31,58,.10)", "0 4px 10px rgba(11,31,58,.08), 0 18px 36px -10px rgba(11,31,58,.30)",
               "0 6px 14px rgba(11,31,58,.12), 0 30px 60px -16px rgba(11,31,58,.40)"),
}


# ---------------------------------------------------------------- colour helpers

HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def rgb(value):
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def to_hex(color):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(c))) for c in color)


def mix(a, b, weight):
    """Colour `a` blended towards `b` by `weight` (0 keeps a, 1 gives b)."""
    ca, cb = rgb(a), rgb(b)
    return to_hex(tuple(x + (y - x) * weight for x, y in zip(ca, cb)))


def luminance(color):
    def channel(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def readable_on(background):
    """White or near-black, whichever reads better on `background`."""
    return "#ffffff" if contrast(background, "#ffffff") >= contrast(background, "#0b1220") else "#0b1220"


def contrast_problems(t):
    """(errors, warnings) for a resolved theme: text must be readable on what it sits on."""
    errors, warnings = [], []

    def check(label, fg, bg, minimum, aa=4.5):
        ratio = contrast(fg, bg)
        if ratio < minimum:
            errors.append(_("{0}: contrast {1} is too low to read (needs at least {2}).").format(label, f"{ratio:.1f}", minimum))
        elif ratio < aa:
            warnings.append(_("{0}: contrast {1} is below the recommended {2}.").format(label, f"{ratio:.1f}", aa))

    check(_("Body text on page background"), t.text_color, t.background_color, 3)
    check(_("Headings on page background"), t.heading_color, t.background_color, 3)
    check(_("Body text on cards"), t.text_color, t.surface_color, 3)
    check(_("White text on the primary colour (hero, footer)"), "#ffffff", t.primary_color, 4.5, 4.5)
    link = t.accent_color if t.tone == "Dark" else mix(t.accent_color, "#000000", .14)
    check(_("Accent links on page background"), link, t.background_color, 2.5, 3)
    return errors, warnings


# ---------------------------------------------------------------- resolving

def template_values(name):
    return TEMPLATES.get(name) or TEMPLATES["Classic"]


def default_sections(template):
    return [dict(s, title="", subtitle="", item_limit=0, variant="") for s in template_values(template)["sections"]]


def resolve(doc):
    """A plain dict with every setting filled in: the theme's own values over its template's."""
    get = doc.get if hasattr(doc, "get") else (lambda k, d=None: getattr(doc, k, d))
    template = get("template") or "Classic"
    base = template_values(template)["values"]
    out = {"template": template, "name": get("name") or get("theme_name") or template}
    for key in TEXT_FIELDS:
        out[key] = get(key) or base.get(key)
    for key in CHECK_FIELDS:
        value = get(key)
        out[key] = cint(value) if value is not None else cint(base.get(key))
    for key in FREE_FIELDS:
        out[key] = get(key) or ""
    out["enable_map_view"] = cint(out["enable_map_view"])
    out["hero_overlay"] = min(max(cint(get("hero_overlay")) or 0, 0), 90) if get("hero_overlay") else 55
    out["custom_css"] = clean_css(get("custom_css") or "")

    rows = [r for r in (get("sections") or [])]
    sections = []
    seen = set()
    for r in rows:
        r = r if isinstance(r, dict) else r.as_dict()
        key = r.get("section_key")
        if key in SECTION_KEYS and key not in seen:
            seen.add(key)
            sections.append({"section_key": key, "enabled": cint(r.get("enabled")), "title": r.get("title") or "",
                             "subtitle": r.get("subtitle") or "", "item_limit": cint(r.get("item_limit")),
                             "variant": r.get("variant") or ""})
    if not sections:
        sections = default_sections(template)
    else:  # a section missing from the table keeps its template position, switched on
        for s in default_sections(template):
            if s["section_key"] not in seen:
                sections.append(s)
    # the hero always comes first
    sections.sort(key=lambda s: s["section_key"] != "hero")
    out["sections"] = sections

    links = []
    for r in (get("links") or []):
        r = r if isinstance(r, dict) else r.as_dict()
        if cint(r.get("enabled")) and r.get("label") and safe_url(r.get("url")):
            links.append({"group": r.get("link_group") or "Header", "label": r["label"], "url": r["url"],
                          "new_tab": cint(r.get("open_in_new_tab"))})
    out["links"] = links
    return frappe._dict(out)


def safe_url(url):
    url = (url or "").strip()
    return bool(url) and (url.startswith("/") and not url.startswith("//") or
                          re.match(r"^(https?://|mailto:|tel:)", url, re.I) is not None)


def clean_css(css):
    """Admin CSS may style the site but cannot pull in other sites or break out of the style tag."""
    css = css or ""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    if re.search(r"@import|@charset|</|<!--|expression\s*\(|javascript:|behavior\s*:|-moz-binding|url\s*\(\s*['\"]?\s*(?!data:image/|/(?!/))", css, re.I):
        frappe.throw(_("Custom CSS may not use @import, external url(...), scripts or HTML."))
    return css.strip()


def css_for(t):
    """The <style> content for a resolved theme: variables first, then the optional custom CSS."""
    dark = t.tone == "Dark"
    bg, card, text, heading = t.background_color, t.surface_color, t.text_color, t.heading_color
    primary, accent = t.primary_color, t.accent_color
    radius, radius_sm = CORNERS.get(t.corner_style, CORNERS["Soft"])
    sm, md, lg = SHADOWS.get(t.shadow_style, SHADOWS["Soft"])
    font, head = FONTS.get(t.font_style, FONTS["Modern sans"])
    accent_text = accent if dark else mix(accent, "#000000", .14)
    v = {
        "--eb-navy": primary, "--eb-navy-2": mix(primary, "#ffffff", .14),
        "--eb-teal": accent, "--eb-teal-2": accent_text,
        "--eb-teal-soft": mix(accent, bg, .78 if dark else .82),
        "--eb-bg": bg, "--eb-card": card, "--eb-text": text, "--eb-ink": heading, "--eb-strong": heading,
        "--eb-muted": mix(text, bg, .28), "--eb-line": mix(text, bg, .86), "--eb-line-2": mix(text, bg, .92),
        "--eb-hero-glow": mix(primary, accent, .42), "--eb-hero-end": mix(primary, accent, .26),
        "--eb-footer-bg": mix(primary, "#000000", .3),
        "--eb-on-accent": readable_on(accent), "--eb-on-primary": readable_on(primary),
        "--eb-radius": f"{radius}px", "--eb-radius-sm": f"{radius_sm}px",
        "--eb-btn-radius": BUTTONS.get(t.button_style, "12px"), "--eb-fs": SCALES.get(t.font_scale, "16px"),
        "--eb-shadow-sm": sm, "--eb-shadow": md, "--eb-shadow-lg": lg,
        "--eb-font": font, "--eb-font-head": head or "var(--eb-font)",
    }
    css = ":root{" + ";".join(f"{k}:{val}" for k, val in v.items()) + "}"
    if t.custom_css:
        css += "\n" + t.custom_css
    return css


def layout_attrs(t):
    """data-* attributes for <main>: the template CSS keys off these."""
    return {
        "data-template": t.template.lower(), "data-tone": t.tone.lower(), "data-hero": t.hero_style.lower(),
        "data-card": t.card_style.lower(), "data-cols": t.results_columns, "data-filters": t.filters_layout.lower(),
        "data-detail": t.detail_layout.lower(), "data-compare": "on" if t.enable_compare else "off",
        "data-map": "on" if t.enable_map_view else "off",
    }


# ---------------------------------------------------------------- active / preview

def can_manage(user=None):
    user = user or frappe.session.user
    return user != "Guest" and bool(set(ADMIN_ROLES) & set(frappe.get_roles(user)))


def snapshot_of(doc):
    return json.dumps(dict(resolve(doc)), default=str)


def active_theme_name():
    return frappe.db.get_single_value("Portal Theme Settings", "active_theme")


def load_active():
    """The published theme as a resolved dict (cached); the Classic template if none is published."""
    name = active_theme_name()
    if name:
        raw = frappe.cache.get_value(f"thinknxg_estate:theme:{name}")
        if raw is None:
            raw = frappe.db.get_value("Portal Theme", name, "published_snapshot") or ""
            frappe.cache.set_value(f"thinknxg_estate:theme:{name}", raw, expires_in_sec=3600)
        if raw:
            try:
                data = json.loads(raw)
                data["name"] = name
                return frappe._dict(data)
            except ValueError:
                pass
    return resolve({"template": "Classic", "name": "Classic"})


def clear_cache(name=None):
    if name:
        frappe.cache.delete_value(f"thinknxg_estate:theme:{name}")
    else:
        for n in frappe.get_all("Portal Theme", pluck="name"):
            frappe.cache.delete_value(f"thinknxg_estate:theme:{n}")


def current_theme():
    """(theme, preview_name). `?theme_preview=NAME` (and the cookie it sets) shows a draft to
    administrators only; everyone else always gets the published theme."""
    form = frappe.form_dict
    wanted = form.get("theme_preview")
    request = getattr(frappe.local, "request", None)
    if wanted is None and request is not None:
        wanted = request.cookies.get(PREVIEW_COOKIE)
    if wanted and can_manage() and frappe.db.exists("Portal Theme", wanted):
        t = resolve(frappe.get_doc("Portal Theme", wanted))
        return t, wanted
    return load_active(), None


def remember_preview():
    """Sets or clears the preview cookie when `theme_preview` is in the request (admins only)."""
    wanted = frappe.form_dict.get("theme_preview")
    if wanted is None or not can_manage():
        return
    cookies = getattr(frappe.local, "cookie_manager", None)
    if not cookies:
        return
    if wanted and frappe.db.exists("Portal Theme", wanted):
        cookies.set_cookie(PREVIEW_COOKIE, wanted, max_age=3600)
    else:
        cookies.delete_cookie(PREVIEW_COOKIE)
