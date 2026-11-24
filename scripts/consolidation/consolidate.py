"""One-shot consolidation of re_core, re_crm, re_portal, re_voice into thinknxg_estate.

Copies every source file into the unified app layout and rewrites:
  * python import paths / dotted method paths (hooks, enqueue, frappe.call)
  * asset URLs (/assets/re_core/... -> /assets/thinknxg_estate/...)
  * module names inside DocType / Report / Chart / Card / Workspace JSON
It also emits LEGACY_METHOD_MAP (old dotted path -> new dotted path) for every
whitelisted function, used by hooks.override_whitelisted_methods so existing
API clients, Meta webhooks and portal feed URLs keep working.

Run:  python3 consolidate.py <src_dir> <out_app_dir>
"""

import json
import os
import re
import shutil
import sys

SRC, OUT = sys.argv[1], sys.argv[2]
APP = "thinknxg_estate"

LEGACY = {
    "re_core": f"{SRC}/re_core/re_core",
    "re_crm": f"{SRC}/re_crm/re_crm",
    "re_portal": f"{SRC}/RE-Portal/re_portal",
    "re_voice": f"{SRC}/RE-Voice/re_voice",
}
# legacy app -> (legacy module folder inside the app, new non-doctype package)
INNER = {"re_core": "re_core", "re_crm": "re_crm", "re_portal": "re_portal", "re_voice": "re_voice"}
PKG = {"re_core": "core", "re_crm": "crm", "re_portal": "portal", "re_voice": "voice"}

MODULES = {
    "Estate Property": ["Property", "Unit", "Property Owner", "Amenity", "Property Amenity",
                        "Property Photo", "Property Document", "Property Unit Charge",
                        "Utility Account", "Property Settings"],
    "Estate Leasing": ["Tenant", "Tenant KYC Document", "Tenant Portal Session", "Lease Contract",
                       "Lease Charge", "Move In Out Inspection", "Inspection Item"],
    "Estate Finance": ["Rent Schedule", "Rent Installment", "Rent Installment Payment",
                       "Post Dated Cheque", "Security Deposit", "Rent Credit Balance",
                       "Owner Statement", "Owner Statement Line", "Tenancy Bulk Payment",
                       "Tenancy Bulk Payment Row", "Partial Payment Table", "Expense Property"],
    "Estate Maintenance": ["Maintenance Request", "Maintenance Job"],
    "Estate CRM": ["RE Lead", "RE Deal", "RE Agent", "Commission Entry", "Commission Slab",
                   "Lead Source RE", "Reservation", "Site Visit", "RE CRM Settings",
                   "WhatsApp Settings", "WhatsApp Message Log", "Property Enquiry",
                   "Site Visit Booking", "Saved Search", "Property Wishlist"],
    "Estate Portal": ["Listing", "Listing Photo", "Listing Inquiry", "Listing Feed Settings",
                      "Portal Chat Session", "Portal Chat Settings", "RE Portal Settings"],
    "Estate Voice": ["AI Settings", "Command Entity", "Conversation Session", "Customer Thread",
                     "Lead Score Log", "Lead Score Model", "Sentiment Reading", "Thread Message",
                     "Voice Command", "Voice Intent", "Voice Locale Profile", "Voice Message",
                     "Voice Usage Log", "WhatsApp Template", "WhatsApp Webhook Log"],
}
HOME_MODULE = "thinkNXG Estate"  # workspaces, number cards, charts, chart sources
REPORT_MODULE = {
    "owner_statement": "Estate Finance", "re_outstanding_rent": "Estate Finance",
    "re_rent_collection": "Estate Finance", "re_pdc_status": "Estate Finance",
    "rent_roll": "Estate Finance", "re_lease_expiry": "Estate Leasing",
    "re_maintenance_overview": "Estate Maintenance", "agent_leaderboard": "Estate CRM",
    "voice_command_analytics": "Estate Voice",
}


def scrub(s):
    return s.lower().replace(" ", "_").replace("-", "_")


DT_MODULE = {dt: m for m, dts in MODULES.items() for dt in dts}
DT_FOLDER = {scrub(dt): scrub(m) for dt, m in DT_MODULE.items()}
ALL_MODULES = [HOME_MODULE] + list(MODULES)

# ----------------------------------------------------------------- path rewriting
REWRITES = []  # (old dotted prefix, new dotted prefix); longest first


def add(old, new):
    REWRITES.append((old.rstrip("."), new.rstrip(".")))


for legacy, inner in INNER.items():
    for folder, mod in DT_FOLDER.items():
        add(f"{legacy}.{inner}.doctype.{folder}", f"{APP}.{mod}.doctype.{folder}")
    for rpt, mod in REPORT_MODULE.items():
        add(f"{legacy}.{inner}.report.{rpt}", f"{APP}.{scrub(mod)}.report.{rpt}")
        add(f"{legacy}.report.{rpt}", f"{APP}.{scrub(mod)}.report.{rpt}")
    add(f"{legacy}.{inner}.dashboard_chart_source", f"{APP}.thinknxg_estate.dashboard_chart_source")
    add(f"{legacy}.www", f"{APP}.www")
    # remaining non-doctype code inside the legacy module folder (re_core.re_core.api, ...)
    add(f"{legacy}.{inner}.", f"{APP}.{PKG[legacy]}.")
    add(f"{legacy}.", f"{APP}.{PKG[legacy]}.")
REWRITES.sort(key=lambda p: -len(p[0]))

DOTTED = re.compile(r"\b(re_core|re_crm|re_portal|re_voice)((?:\.[A-Za-z_][A-Za-z0-9_]*)+)")


def rewrite_dotted(text):
    def sub(m):
        whole = m.group(0)
        for old, new in REWRITES:
            if whole == old or whole.startswith(old + "."):
                return new + whole[len(old):]
        return whole
    return DOTTED.sub(sub, text)


ASSET = re.compile(r"/assets/(re_core|re_crm|re_portal|re_voice)/")


def rewrite_text(text):
    text = ASSET.sub(f"/assets/{APP}/", text)
    text = rewrite_dotted(text)
    # "from re_core import x" / "import re_core" style (no dotted tail)
    text = re.sub(r"\bfrom (re_core|re_crm|re_portal|re_voice) import\b",
                  lambda m: f"from {APP}.{PKG[m.group(1)]} import", text)
    return text


# ----------------------------------------------------------------- destination mapping
SKIP_FILES = {  # one-off console scripts and duplicated / orphan artefacts (see audit report)
    "re_core": {"check_actual_perm.py", "check_domain.py", "check_links.py", "check_perms.py",
                "list_doctypes.py", "rename_fix.py", "rename_test.py", "fix_workspace.py",
                "build_workspace.py", "hooks.py", "modules.txt", "patches.txt"},
}
SKIP_COMMON = {"hooks.py", "modules.txt", "patches.txt", "__pycache__"}


def dest_for(legacy, rel):
    """Map a path relative to the legacy app package to the new app path (or None)."""
    parts = rel.split("/")
    inner = INNER[legacy]
    if parts[-1] in SKIP_COMMON or parts[-1] in SKIP_FILES.get(legacy, set()):
        if len(parts) == 1:
            return None
    if parts[0] in ("fixtures", "desktop_icon"):
        return None  # fixtures are rebuilt by hand in the unified app
    if parts[0] in ("public", "templates", "www"):
        return "/".join(parts)
    if parts[0] == "report" and parts[1] == "__init__.py":
        return None
    if parts[0] == "report":  # re_voice shipped its report outside the module folder
        return f"{scrub(REPORT_MODULE[parts[1]])}/report/" + "/".join(parts[1:])
    if parts[0] == inner:
        sub = parts[1:]
        if not sub:
            return None
        if sub[0] in ("doctype", "report") and len(sub) == 2 and sub[1] == "__init__.py":
            return None
        if sub[0] == "doctype" and len(sub) > 1:
            return f"{DT_FOLDER[sub[1]]}/doctype/" + "/".join(sub[1:])
        if sub[0] == "report" and len(sub) > 1:
            return f"{scrub(REPORT_MODULE[sub[1]])}/report/" + "/".join(sub[1:])
        if sub[0] in ("dashboard_chart", "dashboard_chart_source", "number_card", "workspace"):
            return "thinknxg_estate/" + "/".join(sub)
        if sub == ["__init__.py"]:
            return f"{PKG[legacy]}/__init__.py"
        return f"{PKG[legacy]}/" + "/".join(sub)
    if parts == ["__init__.py"]:
        return f"{PKG[legacy]}/__init__.py"
    return f"{PKG[legacy]}/" + "/".join(parts)


MODULE_NAME_FIX = {"RE Core": None, "Re Core": None, "RE CRM": "Estate CRM",
                   "RE Portal": "Estate Portal", "RE Voice": "Estate Voice"}


def fix_json(path, data, dest):
    def module_for(doc):
        dt = doc.get("doctype")
        if dt == "DocType":
            return DT_MODULE[doc["name"]]
        if dt == "Report":
            return REPORT_MODULE[scrub(doc["name"])]
        return HOME_MODULE

    docs = data if isinstance(data, list) else [data]
    for doc in docs:
        if isinstance(doc, dict) and "module" in doc and doc.get("doctype"):
            doc["module"] = module_for(doc)
        if isinstance(doc, dict) and doc.get("app") in LEGACY:
            doc["app"] = APP
    return data


# ----------------------------------------------------------------- whitelist map
WL = re.compile(r"@frappe\.whitelist\([^)]*\)\s*\n(?:@[^\n]+\n)*\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)")


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    legacy_map = {}
    copied = 0
    for legacy, root in LEGACY.items():
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for fn in filenames:
                src = os.path.join(dirpath, fn)
                rel = os.path.relpath(src, root)
                if legacy == "re_core" and rel.startswith("demo_data/"):
                    dest = "core/" + rel
                else:
                    dest = dest_for(legacy, rel)
                if dest is None:
                    continue
                dst = os.path.join(OUT, dest)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if fn.endswith((".py", ".js", ".html", ".css", ".md", ".txt", ".json")):
                    text = open(src, encoding="utf-8").read()
                    if fn.endswith(".py"):
                        old_mod = (legacy + "." + rel[:-3].replace("/", ".")).replace(".__init__", "")
                        new_mod = (APP + "." + dest[:-3].replace("/", ".")).replace(".__init__", "")
                        for name in WL.findall(text):
                            legacy_map[f"{old_mod}.{name}"] = f"{new_mod}.{name}"
                    text = rewrite_text(text)
                    if fn.endswith(".json") and "/demo_data/" not in dst:
                        data = fix_json(src, json.loads(text), dest)
                        text = json.dumps(data, indent=1, ensure_ascii=False, sort_keys=False) + "\n"
                    open(dst, "w", encoding="utf-8").write(text)
                else:
                    shutil.copy2(src, dst)
                copied += 1
    # packages need __init__.py everywhere python lives
    for dirpath, dirnames, filenames in os.walk(OUT):
        rel = os.path.relpath(dirpath, OUT)
        if rel.split("/")[0] in ("public", "templates") or "/demo_data/data" in dirpath or "demo_data/files" in dirpath:
            continue
        if not os.path.exists(os.path.join(dirpath, "__init__.py")):
            open(os.path.join(dirpath, "__init__.py"), "w").close()
    json.dump(dict(sorted(legacy_map.items())), open(os.path.join(OUT, "legacy_method_map.json"), "w"), indent=1)
    print(f"copied {copied} files; {len(legacy_map)} whitelisted methods mapped")


main()
