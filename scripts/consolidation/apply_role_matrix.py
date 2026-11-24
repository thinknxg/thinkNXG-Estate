"""Role matrix for thinkNXG Estate: adds the brief's extra roles as DocPerms in DocType JSON.

Existing roles keep their permissions. New roles:
  Leasing Manager        Leasing Officer + cancel/amend/delete leases and inspections; finance read
  Broker                 same document access as RE Sales Agent (own leads/deals by ownership rule)
  Receptionist           front desk: capture leads, enquiries, visit requests and maintenance; read stock
  Maintenance Technician read requests, update requests and jobs (no submit, no costs approval)
Also fixes Owner Statement, which only System Manager could open.

Run from the repository root:  python3 scripts/consolidation/apply_role_matrix.py
"""
import glob
import json

APP = "thinknxg_estate"
TS = "2026-11-24 15:00:00.000000"
R, RW, RWC, RWCD = "r", "rw", "rwc", "rwcd"

FLAGS = {"r": "read", "w": "write", "c": "create", "d": "delete", "s": "submit", "x": "cancel", "a": "amend"}

EXPLICIT = {
	"Receptionist": {
		"Property": R, "Unit": R, "Listing": R, "Amenity": R, "Tenant": R,
		"RE Lead": RWC, "Listing Inquiry": RWC, "Property Enquiry": RWC, "Site Visit Booking": RWC,
		"Site Visit": R, "Lead Source RE": R, "RE Agent": R, "Maintenance Request": RWC,
	},
	"Maintenance Technician": {
		"Property": R, "Unit": R, "Maintenance Request": RW, "Maintenance Job": RW, "Move In Out Inspection": R,
	},
	"Leasing Manager": {
		"Lease Contract": "rwcdsxa", "Move In Out Inspection": "rwcdsxa", "Tenant": RWCD,
		"Rent Schedule": R, "Security Deposit": R, "Post Dated Cheque": R, "Reservation": "rwcsx",
		"Property": R, "Unit": RW, "Listing": RWC, "Property Owner": R, "RE Deal": RW, "Site Visit Booking": RW,
	},
	"RE Manager": {"Owner Statement": "rwcdsxa"},
	"Accounts User": {"Owner Statement": "rwcsx"},
	"Property Manager": {"Owner Statement": R},
}
COPY_FROM = {"Broker": "RE Sales Agent", "Leasing Manager": "Leasing Officer"}


def perm(role, flags):
	p = {"role": role, "permlevel": 0, "print": 1, "email": 1, "report": 1, "export": 1, "share": 1}
	for ch in flags:
		p[FLAGS[ch]] = 1
	return p


def main():
	changed = 0
	for path in glob.glob(f"{APP}/*/doctype/*/*.json"):
		d = json.load(open(path))
		if d.get("doctype") != "DocType" or d.get("istable"):
			continue
		perms = d.setdefault("permissions", [])
		have = {(p["role"], p.get("permlevel", 0)) for p in perms}
		add = []
		for new, src in COPY_FROM.items():
			for p in perms:
				if p["role"] == src and (new, p.get("permlevel", 0)) not in have:
					q = dict(p, role=new)
					q.pop("name", None)
					add.append(q)
					have.add((new, p.get("permlevel", 0)))
		for role, table in EXPLICIT.items():
			flags = table.get(d["name"])
			if not flags:
				continue
			existing = next((p for p in perms + add if p["role"] == role and p.get("permlevel", 0) == 0), None)
			if existing:
				for ch in flags:
					existing[FLAGS[ch]] = 1
			else:
				add.append(perm(role, flags))
				have.add((role, 0))
			if d.get("issingle"):
				for p in perms + add:
					if p["role"] == role:
						for k in ("report", "export"):
							p.pop(k, None)
		if add or any(d["name"] in t for t in EXPLICIT.values()):
			perms.extend(add)
			if not d.get("is_submittable"):
				for p in perms:
					for k in ("submit", "cancel", "amend"):
						p.pop(k, None)
			d["modified"] = TS
			json.dump(d, open(path, "w"), indent=1, ensure_ascii=False)
			open(path, "a").write("\n")
			changed += 1
	print("doctypes updated:", changed)


main()
