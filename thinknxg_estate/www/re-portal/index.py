import frappe

no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        from urllib.parse import quote

        target = "/re-portal" + ("?" + frappe.local.request.query_string.decode() if frappe.local.request.query_string else "")
        frappe.local.flags.redirect_location = "/login?redirect-to=" + quote(target, safe="")
        raise frappe.Redirect

    from thinknxg_estate.core.security import is_console_user

    if not is_console_user():
        # tenants and portal visitors have their own pages
        frappe.local.flags.redirect_location = ("/tenant-portal" if "Tenant" in frappe.get_roles() else
                                               "/app" if frappe.session.user != "Guest" and frappe.db.get_value("User", frappe.session.user, "user_type") == "System User"
                                               else "/properties")
        raise frappe.Redirect

    fullname = frappe.utils.get_fullname(frappe.session.user)
    parts = fullname.split()
    initials = "".join(p[0].upper() for p in parts[:2]) if parts else "U"

    roles = frappe.get_roles(frappe.session.user)
    primary_role = "System Manager" if "System Manager" in roles else (roles[0] if roles else "User")

    context.csrf_token = frappe.sessions.get_csrf_token()
    context.user_fullname = fullname
    context.user_initials = initials
    context.user_role = primary_role
    context.lang = frappe.local.lang or "en"
    context.is_rtl = context.lang.split("-")[0] in RTL_LANGUAGES
    context.console_translations = console_translations(context.lang)


RTL_LANGUAGES = ("ar", "he", "fa", "ur")
_MSGIDS = {}


def console_translations(lang):
    """{english: translated} for the strings the console script passes to __(), in this language.
    The msgids are read from this page once per process; English needs no table."""
    import os
    import re

    if not lang or lang.split("-")[0] == "en":
        return {}
    path = os.path.join(os.path.dirname(__file__), "index.html")
    mtime = os.path.getmtime(path)
    if _MSGIDS.get("mtime") != mtime:
        source = open(path, encoding="utf-8").read()
        found = re.findall(r"""__\((['"])((?:\\.|(?!\1).)*)\1\)""", source)
        _MSGIDS.update(mtime=mtime, ids=sorted({m.encode().decode("unicode_escape") if "\\" in m else m
                                               for _q, m in found}))
    out = {}
    # data values the console shows through __(): country names of the portfolio
    countries = frappe.get_all("Property", distinct=True, pluck="country")
    for msgid in list(_MSGIDS["ids"]) + [c for c in countries if c]:
        translated = frappe._(msgid, lang=lang)
        if translated != msgid:
            out[msgid] = translated
    return out
