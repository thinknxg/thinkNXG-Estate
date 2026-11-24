"""Schema additions made during consolidation (documented in the integration report)."""
import glob
import json
import sys

APP = sys.argv[1]


def path_of(name):
    for f in glob.glob(f"{APP}/*/doctype/*/*.json"):
        if json.load(open(f)).get("name") == name:
            return f


def add(doctype, after, fields):
    p = path_of(doctype)
    d = json.load(open(p))
    names = [f["fieldname"] for f in d["fields"]]
    pos = names.index(after) + 1 if after in names else len(names)
    for fd in fields:
        if fd["fieldname"] in names:
            continue
        d["fields"].insert(pos, fd)
        pos += 1
    if "field_order" in d:
        d["field_order"] = [f["fieldname"] for f in d["fields"]]
    d["modified"] = "2026-11-24 12:00:00.000000"
    json.dump(d, open(p, "w"), indent=1, ensure_ascii=False)
    open(p, "a").write("\n")


RE_LEAD = lambda: {"fieldname": "re_lead", "fieldtype": "Link", "options": "RE Lead",
                   "label": "CRM Lead", "in_standard_filter": 1,
                   "description": "The unified CRM lead for this visitor."}

add("Property Settings", "welcome_email_template", [
    {"fieldname": "enable_access_code_portal", "fieldtype": "Check", "label": "Enable Access-Code Tenant Portal",
     "default": "0",
     "description": "Lets tenants sign in to /tenant-self-service with mobile number + access code "
                    "(no email account). Off by default; the standard tenant portal at /tenant-portal "
                    "uses regular website logins."},
    {"fieldname": "allow_tenant_self_termination", "fieldtype": "Check",
     "label": "Allow Tenants to Terminate Leases Online", "default": "0",
     "description": "When off, a tenant's termination from the portal is recorded as a request for "
                    "the leasing team instead of terminating the lease immediately."},
])
add("Property Enquiry", "customer", [
    {"fieldname": "full_name", "fieldtype": "Data", "label": "Name", "in_list_view": 1},
    {"fieldname": "mobile", "fieldtype": "Data", "options": "Phone", "label": "Mobile"},
    {"fieldname": "email", "fieldtype": "Data", "options": "Email", "label": "Email"},
])
add("Property Enquiry", "linked_lead", [RE_LEAD()])
add("Site Visit Booking", "lead", [RE_LEAD()])
add("Saved Search", "lead", [RE_LEAD()])
add("Property Wishlist", "lead", [RE_LEAD()])
print("ok")
