"""Synthetic portfolio for load and performance testing. Never run on a production site.

    bench --site LOAD_SITE execute thinknxg_estate.setup.load_data.seed \
        --kwargs "{'properties': 50, 'units_per_property': 20, 'leases': 400, 'leads': 1000}"

Creates owners, properties (with map coordinates around Muscat), units with rent charges, live
listings for vacant units, tenants with submitted leases (rent schedules, deposits, PDC drafts),
and CRM leads. Records are tagged "LOADTEST" in their names so they are easy to find and remove.
Refuses to run unless the site config has `allow_load_test_data: 1`."""

import random

import frappe
from frappe.utils import add_days, add_months, nowdate

AREAS = [("Qurum", 23.6140, 58.4720), ("Al Khuwair", 23.5960, 58.4090), ("Madinat Sultan Qaboos", 23.5880, 58.4280),
         ("Al Mouj", 23.6290, 58.2780), ("Bausher", 23.5530, 58.3990), ("Ruwi", 23.5990, 58.5450),
         ("Seeb", 23.6700, 58.1890), ("Azaiba", 23.5940, 58.3700)]
UNIT_TYPES = [("Studio", 0, 1, 45, 3600), ("1BR", 1, 1, 70, 5400), ("2BR", 2, 2, 110, 7800),
              ("3BR", 3, 3, 160, 10800), ("4BR+", 4, 4, 240, 15600)]


def _guard():
	if not frappe.conf.get("allow_load_test_data"):
		frappe.throw("Set allow_load_test_data: 1 in this site's site_config.json to seed load-test data.")


def seed(properties=50, units_per_property=20, leases=400, leads=1000, seed_value=7):
	_guard()
	random.seed(seed_value)
	frappe.flags.mute_emails = True
	frappe.flags.estate_bulk_load = True  # no per-lead scoring jobs; nightly scoring covers them
	company = frappe.db.get_value("Company", {}, "name")
	from thinknxg_estate.portal.sync import bulk_listing_sync

	units = []
	outer = bulk_listing_sync().__enter__()
	for p in range(properties):
		area, lat, lng = random.choice(AREAS)
		if frappe.db.exists("Property", {"property_name": ["like", f"LOADTEST % Residence {p:03d}"]}):
			continue  # re-run after a partial seed: keep what is there
		owner_name = f"LOADTEST Owner {p:03d}"
		owner = (frappe.get_doc("Property Owner", owner_name) if frappe.db.exists("Property Owner", owner_name)
		         else frappe.get_doc({"doctype": "Property Owner", "owner_name": owner_name,
		                              "company": company}).insert(ignore_permissions=True))
		prop = frappe.get_doc({
			"doctype": "Property", "property_name": f"LOADTEST {area} Residence {p:03d}",
			"property_type": "Apartment Building", "ownership_type": "Landlord", "country": "Oman",
			"company": company, "owner_ref": owner.name, "city": "Muscat", "area": area,
			"latitude": lat + random.uniform(-0.01, 0.01), "longitude": lng + random.uniform(-0.01, 0.01),
		}).insert(ignore_permissions=True)
		for u in range(units_per_property):
			kind, beds, baths, sqm, rent = random.choice(UNIT_TYPES)
			units.append(frappe.get_doc({
				"doctype": "Unit", "property": prop.name, "unit_no": f"{p:03d}-{u + 101}", "unit_type": kind,
				"status": "Vacant", "bedrooms": beds, "bathrooms": baths, "area_sqm": sqm,
				"furnishing": random.choice(["Unfurnished", "Semi Furnished", "Fully Furnished"]),
				"published_to_portal": 1,
				"charges": [{"charge_type": "Rent", "description": "Rent", "amount": rent, "frequency": "Annual"}],
			}).insert(ignore_permissions=True))
		prop.reload()
		prop.is_live = 1
		prop.save(ignore_permissions=True)  # publishes the vacant units as Listings
		frappe.db.commit()
	outer.__exit__(None, None, None)

	units = [frappe.get_doc("Unit", n) for n in frappe.get_all(
		"Unit", filters={"status": "Vacant", "property": ["in", frappe.get_all(
			"Property", filters={"property_name": ["like", "LOADTEST %"]}, pluck="name")]}, pluck="name")]
	random.shuffle(units)
	for i, unit in enumerate(units[:leases]):
		tenant = frappe.get_doc({"doctype": "Tenant", "tenant_name": f"LOADTEST Tenant {unit.name}",
		                         "mobile": f"+9689{random.randint(0, 9999999):07d}"}).insert(ignore_permissions=True)
		start = add_days(nowdate(), -random.randint(0, 300))
		lease = frappe.get_doc({
			"doctype": "Lease Contract", "tenant": tenant.name, "unit": unit.name, "start_date": start,
			"end_date": add_days(add_months(start, 12), -1), "payment_frequency": "Quarterly",
			"security_deposit_amount": 500,
			"charges": [{"charge_type": "Rent", "description": "Base Rent",
			             "amount": frappe.db.get_value("Unit", unit.name, "annual_rent")}],
		}).insert(ignore_permissions=True)
		lease.submit()
		if i % 50 == 49:
			frappe.db.commit()

	sources = frappe.get_all("Lead Source RE", pluck="name") or [None]
	from thinknxg_estate.portal.sync import bulk_listing_sync

	for i in range(frappe.db.count("RE Lead", {"full_name": ["like", "LOADTEST %"]}), leads):
		kind, beds, *_rest, rent = random.choice(UNIT_TYPES)
		frappe.get_doc({
			"doctype": "RE Lead", "full_name": f"LOADTEST Lead {i:04d}", "mobile": f"+9687{i:07d}",
			"source": random.choice(sources), "interest_type": "Rent",
			"budget_min": rent * 0.8, "budget_max": rent * 1.2, "preferred_location": random.choice(AREAS)[0],
			"bedrooms_required": beds,
		}).insert(ignore_permissions=True)
		if i % 100 == 99:
			frappe.db.commit()
	frappe.db.commit()
	loadtest = {"property_name": ["like", "LOADTEST %"]}
	return {"properties": frappe.db.count("Property", loadtest),
	        "units": frappe.db.count("Unit", {"property": ["in", frappe.get_all("Property", loadtest, pluck="name")]}),
	        "leases": frappe.db.count("Lease Contract", {"docstatus": 1, "tenant_name": ["like", "LOADTEST %"]}),
	        "leads": frappe.db.count("RE Lead", {"full_name": ["like", "LOADTEST %"]}),
	        "listings": frappe.db.count("Listing", {"is_published": 1})}
