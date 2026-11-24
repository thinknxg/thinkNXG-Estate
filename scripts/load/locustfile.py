"""Load test for thinkNXG Estate.

Two kinds of user, in the proportions a property business sees:

* PublicVisitor (most traffic): browses /properties with filters, switches to the map, opens
  listings, compares, and now and then sends an enquiry.
* StaffUser: signs in to the desk, opens the staff console, the live dashboard, lease and lead
  lists, a report, and a lease record.

Run against a copy of production data, never production itself (enquiries create records):

    locust -f scripts/load/locustfile.py --host http://SITE --headless -u 100 -r 10 -t 5m \
        --csv results/run100

Each simulated visitor sends its own X-Forwarded-For address so per-visitor rate limits behave as
they would for real visitors. That only works through a test-only proxy that passes the header on;
the production nginx config replaces it with the real client address (see docs/LOAD_TEST.md).

Environment: STAFF_USER / STAFF_PASSWORD for the staff login.
"""

import os
import random
import re

from locust import HttpUser, between, events, task

STAFF_USER = os.environ.get("STAFF_USER", "load.manager@example.com")
STAFF_PASSWORD = os.environ.get("STAFF_PASSWORD", "")
CITIES = ["Muscat"]
TYPES = ["Studio", "1BR", "2BR", "3BR", "4BR+"]
ROUTES = []


@events.test_start.add_listener
def collect_routes(environment, **_kwargs):
	"""Listing routes to visit, read once from the public search API."""
	import requests

	host = environment.host
	for page in range(1, 8):
		r = requests.get(f"{host}/api/method/thinknxg_estate.portal.api.listings.search",
		                 params={"page": page, "page_size": 30},
		                 headers={"X-Forwarded-For": f"10.255.0.{page}"}, timeout=30)
		ROUTES.extend(row["route"] for row in r.json()["message"]["results"])
	ROUTES[:] = sorted(set(ROUTES))


def _ip():
	return f"10.{random.randint(0, 254)}.{random.randint(0, 254)}.{random.randint(1, 254)}"


class PublicVisitor(HttpUser):
	weight = 9
	wait_time = between(3, 8)  # reading time between pages

	def on_start(self):
		self.client.headers["X-Forwarded-For"] = _ip()

	@task(5)
	def search(self):
		params = {}
		if random.random() < 0.6:
			params["unit_type"] = random.choice(TYPES)
		if random.random() < 0.4:
			params["max_price"] = random.choice([6000, 9000, 12000, 18000])
		if random.random() < 0.3:
			params["sort"] = random.choice(["newest", "price_asc", "price_desc"])
		if random.random() < 0.3:
			params["page"] = random.randint(2, 6)
		self.client.get("/properties", params=params, name="/properties [search]")

	@task(2)
	def map_view(self):
		self.client.get("/properties", params={"view": "map"}, name="/properties [map]")
		self.client.get("/api/method/thinknxg_estate.portal.api.listings.map_points",
		                params={"unit_type": random.choice(TYPES)}, name="map_points API")

	@task(6)
	def listing(self):
		if ROUTES:
			self.client.get("/" + random.choice(ROUTES), name="/property/[route]")

	@task(1)
	def compare(self):
		if len(ROUTES) > 3:
			r = self.client.get("/api/method/thinknxg_estate.portal.api.listings.search",
			                    params={"page_size": 3}, name="search API")
			names = ",".join(row["name"] for row in r.json()["message"]["results"])
			self.client.get("/properties/compare", params={"l": names}, name="/properties/compare")

	@task(1)
	def enquiry(self):
		if random.random() < 0.15 and ROUTES:
			page = self.client.get("/" + random.choice(ROUTES), name="/property/[route]")
			listing = re.search(r'listing: "([^"]+)"', page.text)
			self.client.post("/api/method/thinknxg_estate.portal.api.listings.submit_inquiry",
			                 data={"full_name": "Load Test Visitor", "mobile": f"+9689{random.randint(1000000, 9999999)}",
			                       "listing": listing.group(1) if listing else "", "message": "Load test",
			                       "form_ts": "2000-01-01 00:00:00"},
			                 name="submit_inquiry")


class StaffUser(HttpUser):
	weight = 1
	wait_time = between(5, 15)

	def on_start(self):
		self.client.headers["X-Forwarded-For"] = _ip()
		self.client.post("/api/method/login", data={"usr": STAFF_USER, "pwd": STAFF_PASSWORD}, name="login")
		r = self.client.get("/api/resource/Lease Contract", params={"limit_page_length": 50, "filters": '[["docstatus","=",1]]'},
		                    name="lease list (REST)")
		self.leases = [row["name"] for row in r.json().get("data", [])] if r.ok else []

	@task(3)
	def dashboard(self):
		self.client.get("/api/method/thinknxg_estate.core.dashboard.get_overview", name="dashboard overview API")

	@task(2)
	def console(self):
		self.client.get("/re-portal", name="/re-portal console")
		self.client.get("/api/method/thinknxg_estate.core.api.get_dashboard_stats", name="console stats API")
		self.client.get("/api/method/thinknxg_estate.core.api.get_sidebar_counts", name="console counts API")

	@task(3)
	def lists(self):
		self.client.get("/api/method/frappe.desk.reportview.get",
		                params={"doctype": "Lease Contract", "fields": '["name","tenant_name","unit","status","end_date"]',
		                        "order_by": "modified desc", "start": 0, "page_length": 20},
		                name="desk list: Lease Contract")
		self.client.get("/api/method/frappe.desk.reportview.get",
		                params={"doctype": "RE Lead", "fields": '["name","full_name","status","score_band"]',
		                        "order_by": "modified desc", "start": 0, "page_length": 20},
		                name="desk list: RE Lead")

	@task(2)
	def open_lease(self):
		if self.leases:
			self.client.get("/api/method/frappe.desk.form.load.getdoc",
			                params={"doctype": "Lease Contract", "name": random.choice(self.leases)},
			                name="desk form: Lease Contract")

	@task(1)
	def report(self):
		self.client.get("/api/method/frappe.desk.query_report.run", params={"report_name": "Rent Roll"},
		                name="report: Rent Roll")
