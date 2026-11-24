"""Fold legacy Custom Fields / Property Setters on the platform's own DocTypes into
the DocType JSON of thinknxg_estate. Fields on external DocTypes (User, Purchase
Invoice) are written to the unified app's fixtures/custom_field.json instead.

Run: python3 fold_custom_fields.py <src_dir> <app_dir>
"""
import ast
import glob
import json
import os
import sys

SRC, APP = sys.argv[1], sys.argv[2]
FIX = f"{SRC}/re_core/re_core/fixtures"

dt_json = {}
for f in glob.glob(f"{APP}/*/doctype/*/*.json"):
    d = json.load(open(f))
    if d.get("doctype") == "DocType":
        dt_json[d["name"]] = (f, d)

custom, setters = {}, []
for fname in ("custom_field.json", "property_custom_fields.json", "property_unit_pdc_fields.json"):
    for doc in json.load(open(f"{FIX}/{fname}")):
        if doc["doctype"] == "Custom Field":
            custom[doc["name"]] = doc  # later files win; they are the newer exports
        elif doc["doctype"] == "Property Setter":
            setters.append(doc)

# re_voice created its custom fields in code (install.py CUSTOM_FIELDS)
src = open(f"{SRC}/RE-Voice/re_voice/install.py").read()
tree = ast.parse(src)
voice_fields = next(ast.literal_eval(n.value) for n in tree.body
                    if isinstance(n, ast.Assign) and n.targets[0].id == "CUSTOM_FIELDS")
for dt, fieldname, fieldtype, label, insert_after, read_only in voice_fields:
    doc = {"doctype": "Custom Field", "dt": dt, "fieldname": fieldname, "fieldtype": fieldtype,
           "label": label, "insert_after": insert_after, "read_only": read_only}
    if fieldname == "score_band":
        doc["options"] = "\nHot\nWarm\nCold"
    if fieldname == "sentiment":
        doc["options"] = "\nPositive\nNeutral\nNegative"
    custom[f"{dt}-{fieldname}"] = doc

KEEP = ("fieldname", "fieldtype", "label", "options", "default", "reqd", "read_only", "hidden",
        "in_list_view", "in_standard_filter", "description", "depends_on", "fetch_from",
        "fetch_if_empty", "allow_on_submit", "unique", "bold", "collapsible", "precision",
        "length", "no_copy", "print_hide", "mandatory_depends_on", "read_only_depends_on",
        "search_index", "permlevel", "translatable", "in_global_search", "non_negative")

external, folded = [], []
by_dt = {}
for doc in custom.values():
    by_dt.setdefault(doc["dt"], []).append(doc)

for dt, docs in by_dt.items():
    if dt not in dt_json:
        external.extend(docs)
        continue
    path, d = dt_json[dt]
    existing = {f["fieldname"] for f in d["fields"]}
    pending = [c for c in docs if c["fieldname"] not in existing]
    # insert in dependency order: a field may sit after another custom field
    guard = 0
    while pending and guard < 100:
        guard += 1
        for c in list(pending):
            names = [f["fieldname"] for f in d["fields"]]
            anchor = c.get("insert_after")
            if anchor and anchor not in names and any(p["fieldname"] == anchor for p in pending):
                continue
            field = {k: c[k] for k in KEEP if c.get(k) not in (None, "", 0) or k in ("fieldname", "fieldtype")}
            pos = names.index(anchor) + 1 if anchor in names else len(names)
            d["fields"].insert(pos, field)
            if "field_order" in d:
                d["field_order"] = [f["fieldname"] for f in d["fields"]]
            pending.remove(c)
            folded.append(f"{dt}.{c['fieldname']}")
    json.dump(d, open(path, "w"), indent=1, ensure_ascii=False)
    open(path, "a").write("\n")

for ps in setters:
    path, d = dt_json[ps["doc_type"]]
    for f in d["fields"]:
        if f["fieldname"] == ps["field_name"]:
            f[ps["property"]] = ps["value"]
            folded.append(f"{ps['doc_type']}.{ps['field_name']}.{ps['property']}={ps['value']!r}")
    json.dump(d, open(path, "w"), indent=1, ensure_ascii=False)
    open(path, "a").write("\n")

os.makedirs(f"{APP}/fixtures", exist_ok=True)
clean = []
for c in sorted(external, key=lambda x: (x["dt"], x["fieldname"])):
    c = {k: v for k, v in c.items() if k not in ("creation", "modified", "owner", "modified_by")}
    c["module"] = "thinkNXG Estate"
    c["name"] = f"{c['dt']}-{c['fieldname']}"
    clean.append(c)
json.dump(clean, open(f"{APP}/fixtures/custom_field.json", "w"), indent=1, ensure_ascii=False)
print("folded:", len(folded))
for x in folded:
    print("  ", x)
print("external custom fields:", [c["name"] for c in clean])
json.dump({"folded": folded, "external": [c["name"] for c in clean],
           "legacy_custom_field_names": sorted(custom)},
          open(f"{APP}/patches/legacy_custom_fields.json", "w") if os.path.isdir(f"{APP}/patches")
          else open(f"/home/claude/build/legacy_custom_fields.json", "w"), indent=1)
