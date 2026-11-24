"""Unified navigation for thinkNXG Estate: workspaces, extra KPI cards, sidebar, desktop icon.

Run: python3 build_navigation.py <app_dir>
"""
import json
import os
import shutil
import sys

APP = sys.argv[1]
HOME = f"{APP}/thinknxg_estate"
TS = "2026-11-24 12:00:00.000000"
MOD = "thinkNXG Estate"


def load(p):
    return json.load(open(p))


def dump(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")


def scrub(s):
    return s.lower().replace(" ", "_").replace("-", "_")


# ------------------------------------------------------------- additional KPI cards
CARDS = [
    ("RE Reserved Units", "Reserved Units", "Unit", [["Unit", "status", "=", "Reserved"]], "#7C5CFC"),
    ("RE Total Tenants", "Tenants", "Tenant", [["Tenant", "disabled", "=", 0]], "#2490EF"),
    ("RE Total Owners", "Owners", "Property Owner", [], "#0F766E"),
    ("RE Total Leads", "Leads", "RE Lead", [], "#2490EF"),
    ("RE New Enquiries", "New Enquiries", "Listing Inquiry", [["Listing Inquiry", "status", "=", "New"]], "#FFA00A"),
    ("RE Site Visits This Month", "Site Visits (This Month)", "Site Visit",
     [["Site Visit", "visit_datetime", "Timespan", "this month"]], "#0F766E"),
    ("RE Deals Won", "Deals Won", "RE Deal", [["RE Deal", "pipeline_stage", "=", "Won"]], "#29CD42"),
    ("RE Open Deals", "Open Deals", "RE Deal",
     [["RE Deal", "pipeline_stage", "not in", ["Won", "Lost"]]], "#7C5CFC"),
]
for name, label, dt, filters, color in CARDS:
    dump(f"{HOME}/number_card/{scrub(name)}/{scrub(name)}.json", {
        "creation": TS, "docstatus": 0, "doctype": "Number Card", "idx": 0, "modified": TS,
        "modified_by": "Administrator", "module": MOD, "name": name, "owner": "Administrator",
        "label": label, "document_type": dt, "function": "Count",
        "filters_json": json.dumps(filters), "is_public": 1, "is_standard": 1,
        "show_percentage_stats": 1, "stats_time_interval": "Monthly", "type": "Document Type",
        "color": color, "show_full_number": 0,
    })
    open(f"{HOME}/number_card/{scrub(name)}/__init__.py", "a").close()

# ------------------------------------------------------------- workspaces
WS = f"{HOME}/workspace"
RENAME = {
    "property_operations": "thinkNXG Estate",
    "re_finance": "Estate Finance",
    "re_maintenance": "Estate Maintenance",
    "re_crm": "Estate CRM",
}
if os.path.exists(f"{WS}/property_operations"):  # first run only
    for folder in ("re_core", "re_portal"):  # hub pages replaced by the unified sidebar
        shutil.rmtree(f"{WS}/{folder}")

    CARD_RENAMES = {
        "07 · CRM & Leasing Sales (re_crm)": "07 · CRM & Sales",
        "08 · Portal & Listings (RE-Portal)": "08 · Property Portal",
        "09 · Voice & Messaging (RE-Voice)": "09 · Communications",
    }

    for folder, new in RENAME.items():
        d = load(f"{WS}/{folder}/{folder}.json")
        d.update({"name": new, "label": new, "title": new, "module": MOD, "modified": TS,
                  "app": "thinknxg_estate", "public": 1})
        content = json.loads(d["content"])
        for block in content:
            data = block["data"]
            if block["type"] == "header" and "Property Operations" in data.get("text", ""):
                data["text"] = '<span class="h3"><b>thinkNXG Estate</b></span>'
            if block["type"] == "paragraph" and folder == "property_operations":
                data["text"] = ("One Platform. Every Property. Complete Control. Portfolio, leasing, "
                                "collections, maintenance, CRM and the property portal in one place.")
            if block["type"] == "card" and data.get("card_name") in CARD_RENAMES:
                data["card_name"] = CARD_RENAMES[data["card_name"]]
        for link in d.get("links", []):
            if link.get("label") in CARD_RENAMES:
                link["label"] = CARD_RENAMES[link["label"]]

        if folder == "property_operations":
            # CRM and people KPIs next to the operational ones
            idx = next(i for i, b in enumerate(content)
                       if b["type"] == "header" and "Operational alerts" in b["data"]["text"])
            extra = [{"id": f"estate-kpi-{i}", "type": "number_card",
                      "data": {"number_card_name": n, "col": 3}}
                     for i, n in enumerate(["RE Reserved Units", "RE Total Tenants", "RE Total Owners",
                                            "RE Total Leads", "RE New Enquiries",
                                            "RE Site Visits This Month", "RE Open Deals",
                                            "RE Deals Won"])]
            header = {"id": "estate-kpi-h", "type": "header",
                      "data": {"text": '<span class="h4"><b>People &amp; pipeline</b></span>', "col": 12}}
            content[idx:idx] = [header] + extra
            have = {c["number_card_name"] for c in d["number_cards"]}
            for _, n in [(0, x) for x in ["RE Reserved Units", "RE Total Tenants", "RE Total Owners",
                                         "RE Total Leads", "RE New Enquiries",
                                         "RE Site Visits This Month", "RE Open Deals", "RE Deals Won"]]:
                if n not in have:
                    d["number_cards"].append({"doctype": "Workspace Number Card", "parentfield": "number_cards",
                                              "parenttype": "Workspace", "number_card_name": n,
                                              "label": n.replace("RE ", "")})
            roles = {r["role"] for r in d["roles"]}
            for role in ("RE Sales Manager", "RE Sales Agent"):
                if role not in roles:
                    d["roles"].append({"doctype": "Has Role", "parentfield": "roles",
                                       "parenttype": "Workspace", "role": role})
        if folder == "re_crm":
            d["roles"] = [{"doctype": "Has Role", "parentfield": "roles", "parenttype": "Workspace", "role": r}
                          for r in ("RE Manager", "RE Sales Manager", "RE Sales Agent", "System Manager")]
            content = ([{"id": "crm-h", "type": "header",
                         "data": {"text": '<span class="h3"><b>Estate CRM</b></span>', "col": 12}}] +
                       [{"id": f"crm-k{i}", "type": "number_card", "data": {"number_card_name": n, "col": 3}}
                        for i, n in enumerate(["RE Total Leads", "RE New Enquiries",
                                               "RE Site Visits This Month", "RE Open Deals"])] +
                       [b for b in content if not (b["type"] == "header" and "RE CRM" in b["data"].get("text", ""))])
            d["number_cards"] = [{"doctype": "Workspace Number Card", "parentfield": "number_cards",
                                  "parenttype": "Workspace", "number_card_name": n, "label": n.replace("RE ", "")}
                                 for n in ["RE Total Leads", "RE New Enquiries", "RE Site Visits This Month",
                                           "RE Open Deals"]]
        d["content"] = json.dumps(content)
        target = scrub(new)
        os.makedirs(f"{WS}/{target}", exist_ok=True)
        dump(f"{WS}/{target}/{target}.json", d)
        open(f"{WS}/{target}/__init__.py", "a").close()
        if target != folder:
            shutil.rmtree(f"{WS}/{folder}")


# ------------------------------------------------------------- sidebar + desktop icon
L = lambda label, to, kind="DocType": {"type": "Link", "label": label, "link_to": to,
                                       "link_type": kind, "child": 1, "collapsible": 1}
W = lambda label, to, icon, default=0: {"type": "Link", "label": label, "link_to": to,
                                        "link_type": "Workspace", "icon": icon, "collapsible": 1,
                                        "default_workspace": default}
S = lambda label, icon: {"type": "Section Break", "label": label, "icon": icon, "indent": 1,
                         "keep_closed": 1, "collapsible": 1, "link_type": "DocType"}
items = [
    W("Dashboard", "thinkNXG Estate", "house", 1),
    W("Finance & Collections", "Estate Finance", "banknote"),
    W("Maintenance Dashboard", "Estate Maintenance", "wrench"),
    W("CRM Dashboard", "Estate CRM", "users-round"),
    S("Properties", "building-2"), L("Properties", "Property"), L("Units", "Unit"),
    L("Owners", "Property Owner"), L("Documents", "Property Document"), L("Amenities", "Amenity"),
    L("Utility Accounts", "Utility Account"),
    S("Tenants & Leases", "file-text"), L("Tenants", "Tenant"), L("Leases", "Lease Contract"),
    L("Inspections", "Move In Out Inspection"),
    S("Rent & Payments", "banknote"), L("Rent Schedules", "Rent Schedule"),
    L("Post Dated Cheques", "Post Dated Cheque"), L("Security Deposits", "Security Deposit"),
    L("Bulk Rent Payment", "Tenancy Bulk Payment"), L("Rent Credit Balances", "Rent Credit Balance"),
    L("Owner Statements", "Owner Statement"), L("Property Expenses", "Expense Property"),
    L("Sales Invoices", "Sales Invoice"), L("Payment Entries", "Payment Entry"),
    S("Maintenance", "wrench"), L("Requests", "Maintenance Request"), L("Jobs", "Maintenance Job"),
    S("Real Estate CRM", "users-round"), L("Leads", "RE Lead"), L("Opportunities", "RE Deal"),
    L("Pipeline", "/app/re-deal/view/kanban/Deal Pipeline", "URL"), L("Site Visits", "Site Visit"),
    L("Reservations", "Reservation"), L("Agents & Brokers", "RE Agent"),
    L("Commissions", "Commission Entry"), L("Lead Sources", "Lead Source RE"),
    S("Property Portal", "globe"), L("Listings", "Listing"), L("Enquiries", "Listing Inquiry"),
    L("Portal Chats", "Portal Chat Session"), L("Saved Searches", "Saved Search"),
    L("Wishlists", "Property Wishlist"), L("Portal Website", "/properties", "URL"),
    S("Communications", "mic"), L("Customer Threads", "Customer Thread"),
    L("Voice Messages", "Voice Message"), L("Voice Commands", "Voice Command"),
    L("WhatsApp Messages", "WhatsApp Message Log"), L("WhatsApp Templates", "WhatsApp Template"),
    L("Lead Scores", "Lead Score Log"), L("Sentiment", "Sentiment Reading"),
    S("Reports & Analytics", "chart-column"), L("Rent Roll", "Rent Roll", "Report"),
    L("Outstanding Rent", "RE Outstanding Rent", "Report"),
    L("Rent Collection", "RE Rent Collection", "Report"),
    L("Lease Expiry", "RE Lease Expiry", "Report"), L("PDC Status", "RE PDC Status", "Report"),
    L("Owner Statement", "Owner Statement", "Report"),
    L("Maintenance Overview", "RE Maintenance Overview", "Report"),
    L("Agent Leaderboard", "Agent Leaderboard", "Report"),
    L("Voice Command Analytics", "Voice Command Analytics", "Report"),
    L("Accounts Receivable", "Accounts Receivable", "Report"),
    S("Settings", "settings"), L("Property Settings", "Property Settings"),
    L("CRM Settings", "RE CRM Settings"), L("Portal Settings", "RE Portal Settings"),
    L("Portal Feeds", "Listing Feed Settings"), L("Portal Chat", "Portal Chat Settings"),
    L("WhatsApp Settings", "WhatsApp Settings"), L("AI Settings", "AI Settings"),
    L("Lead Scoring", "Lead Score Model"), L("Voice Locales", "Voice Locale Profile"),
]
for i, it in enumerate(items, 1):
    it.update({"doctype": "Sidebar Item", "parentfield": "items", "parenttype": "Sidebar", "idx": i})
    it.pop("default_workspace", None)
    if it["link_type"] == "URL":
        it["url"] = it.pop("link_to")
# v16: apps ship a module-level `Sidebar` (the Workspace Sidebar fixture route is deprecated)
dump(f"{HOME}/sidebar/thinknxg_estate/thinknxg_estate.json", {
    "app": "thinknxg_estate", "creation": TS, "docstatus": 0, "doctype": "Sidebar",
    "header_icon": "organization", "idx": 0, "items": items, "modified": TS,
    "modified_by": "Administrator", "module": MOD, "name": "thinkNXG Estate",
    "owner": "Administrator", "standard": 1, "title": "thinkNXG Estate",
})
for d in (f"{HOME}/sidebar", f"{HOME}/sidebar/thinknxg_estate"):
    open(f"{d}/__init__.py", "a").close()
# icon-grid sites import app-level desktop_icon/ files; Apps-mode sites use add_to_apps_screen
dump(f"{APP}/desktop_icon/thinknxg_estate.json", {
    "app": "thinknxg_estate", "bg_color": "blue", "creation": TS, "docstatus": 0,
    "doctype": "Desktop Icon", "hidden": 0, "icon": "organization", "icon_type": "Link", "idx": 0,
    "label": "thinkNXG Estate", "link_to": "thinkNXG Estate", "link_type": "Workspace Sidebar",
    "modified": TS, "modified_by": "Administrator", "name": "thinkNXG Estate", "owner": "Administrator",
    "restrict_removal": 0, "roles": [], "standard": 1,
})
for stale in ("workspace_sidebar.json", "desktop_icon.json"):
    if os.path.exists(f"{APP}/fixtures/{stale}"):
        os.remove(f"{APP}/fixtures/{stale}")
print("workspaces:", sorted(os.listdir(WS)))
print("sidebar items:", len(items))
