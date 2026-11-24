"""Property matching for CRM leads.

Every available unit is scored 0-100 against the lead's requirements, and each match carries
the reasons behind its score, so an agent can explain a recommendation to the customer.

Availability: Vacant and Reserved units, plus occupied units whose current lease ends before
the lead's preferred move-in date ("available from ...").
Price: annual rent for Rent leads; the published sale price for Buy leads.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from thinknxg_estate.core.security import desk_staff_only

WEIGHTS = {"budget": 35, "type": 20, "bedrooms": 15, "location": 15, "amenities": 10, "area": 5}
RESIDENTIAL_TYPES = {"Studio", "1BR", "2BR", "3BR", "4BR+", "Penthouse"}
TYPE_MAP = {
	# lead preference -> (unit types, property types) that satisfy it
	"Apartment": (RESIDENTIAL_TYPES, {"Apartment Building", "Mixed Use"}),
	"Villa": (RESIDENTIAL_TYPES, {"Villa", "Villa Compound"}),
	"Office": ({"Office"}, None),
	"Shop": ({"Shop"}, None),
	"Warehouse": ({"Warehouse"}, None),
	"Land": (None, {"Land"}),
}


def lead_requirements(lead):
	doc = frappe.get_doc("RE Lead", lead) if isinstance(lead, str) else lead
	return frappe._dict(
		interest_type=doc.get("interest_type") or "Rent",
		property_type=doc.get("preferred_property_type"),
		location=(doc.get("preferred_location") or "").strip(),
		budget_min=flt(doc.get("budget_min")),
		budget_max=flt(doc.get("budget_max")),
		bedrooms=cint(doc.get("bedrooms_required")),
		min_area=flt(doc.get("min_area_sqm")),
		possession_date=doc.get("possession_date"),
		amenities=[row.amenity for row in (doc.get("required_amenities") or [])],
	)


def _candidates(req):
	units = frappe.db.sql("""
		select u.name, u.unit_no, u.unit_title, u.unit_type, u.status, u.bedrooms, u.bathrooms,
		       u.area_sqm, u.annual_rent, u.furnishing, u.property, u.current_lease,
		       p.property_name, p.property_type, p.city, p.area as locality
		from `tabUnit` u join `tabProperty` p on p.name = u.property
		where u.status in ('Vacant', 'Reserved', 'Occupied')""", as_dict=True)
	sale_prices = {}
	if req.interest_type == "Buy":
		for row in frappe.get_all("Listing", {"is_published": 1, "listing_type": "Sale"},
		                          ["unit", "headline_price"]):
			sale_prices[row.unit] = flt(row.headline_price)
	lease_end = {}
	occupied = [u.current_lease for u in units if u.status == "Occupied" and u.current_lease]
	if occupied:
		for row in frappe.get_all("Lease Contract", {"name": ["in", occupied]}, ["name", "end_date"]):
			lease_end[row.name] = row.end_date
	amenities = {}
	for row in frappe.get_all("Property Amenity", {"parenttype": "Property"}, ["parent", "amenity"]):
		amenities.setdefault(row.parent, set()).add(row.amenity)

	out = []
	for u in units:
		available_from = None
		if u.status == "Occupied":
			end = lease_end.get(u.current_lease)
			if not (req.possession_date and end and getdate(end) < getdate(req.possession_date)):
				continue
			available_from = end
		price = sale_prices.get(u.name) if req.interest_type == "Buy" else flt(u.annual_rent)
		if req.interest_type == "Buy" and not price:
			continue  # not on the market for sale
		u.price, u.available_from, u.amenities = price, available_from, amenities.get(u.property, set())
		out.append(u)
	return out


def score_unit(u, req):
	score, reasons = 0.0, []
	# budget
	if req.budget_max or req.budget_min:
		if not u.price:
			return None, []
		if req.budget_max and u.price > req.budget_max * 1.25:
			return None, []
		if (not req.budget_max or u.price <= req.budget_max) and u.price >= req.budget_min * 0.75:
			score += WEIGHTS["budget"]
			reasons.append(_("within budget"))
		elif req.budget_max and u.price <= req.budget_max * 1.1:
			score += WEIGHTS["budget"] * 0.5
			reasons.append(_("slightly above budget"))
		elif u.price < req.budget_min * 0.75:
			score += WEIGHTS["budget"] * 0.4
			reasons.append(_("below budget range"))
	else:
		score += WEIGHTS["budget"] * 0.5
	# type
	if req.property_type in TYPE_MAP:
		unit_types, property_types = TYPE_MAP[req.property_type]
		type_ok = unit_types is None or u.unit_type in unit_types
		if type_ok and (property_types is None or u.property_type in property_types):
			score += WEIGHTS["type"]
			reasons.append(_(req.property_type).lower())
		elif unit_types and u.unit_type in unit_types:
			score += WEIGHTS["type"] * 0.5
		else:
			return None, []
	else:
		score += WEIGHTS["type"] * 0.5
	# bedrooms
	if req.bedrooms:
		if cint(u.bedrooms) >= req.bedrooms:
			score += WEIGHTS["bedrooms"]
			reasons.append(_("{0} bedrooms").format(cint(u.bedrooms)))
		elif cint(u.bedrooms) == req.bedrooms - 1:
			score += WEIGHTS["bedrooms"] * 0.3
		else:
			return None, []
	else:
		score += WEIGHTS["bedrooms"] * 0.5
	# location
	if req.location:
		needle = req.location.lower()
		if needle in (u.locality or "").lower() or needle in (u.city or "").lower() \
				or needle in (u.property_name or "").lower():
			score += WEIGHTS["location"]
			reasons.append(_("in {0}").format(u.locality or u.city))
	else:
		score += WEIGHTS["location"] * 0.5
	# amenities
	if req.amenities:
		have = len(set(req.amenities) & u.amenities)
		score += WEIGHTS["amenities"] * have / len(req.amenities)
		if have:
			reasons.append(_("{0} of {1} amenities").format(have, len(req.amenities)))
	else:
		score += WEIGHTS["amenities"] * 0.5
	# area
	if req.min_area:
		if flt(u.area_sqm) >= req.min_area:
			score += WEIGHTS["area"]
			reasons.append(_("{0} sqm").format(flt(u.area_sqm, 0)))
	else:
		score += WEIGHTS["area"] * 0.5
	# availability
	if u.status == "Reserved":
		score -= 10
		reasons.append(_("currently reserved"))
	if u.available_from:
		reasons.append(_("available from {0}").format(frappe.utils.formatdate(u.available_from)))
	return max(round(score), 0), reasons


def match_units(lead, limit=10, min_score=40):
	req = lead_requirements(lead)
	results = []
	for u in _candidates(req):
		score, reasons = score_unit(u, req)
		if score is None or score < min_score:
			continue
		results.append({
			"unit": u.name, "unit_title": u.unit_title or u.unit_no, "property": u.property,
			"property_name": u.property_name, "city": u.city, "locality": u.locality,
			"unit_type": u.unit_type, "bedrooms": u.bedrooms, "area_sqm": u.area_sqm,
			"price": u.price, "status": u.status, "available_from": u.available_from,
			"score": score, "reasons": reasons,
		})
	results.sort(key=lambda r: (-r["score"], flt(r["price"])))
	return results[:cint(limit) or 10]


@frappe.whitelist()
@desk_staff_only
def get_matching_units(lead, limit=10):
	frappe.has_permission("RE Lead", "read", doc=lead, throw=True)
	return match_units(lead, limit=limit)


def recommend_on_qualify(doc, method=None):
	"""RE Lead on_update: when a lead becomes Qualified, record the best matches on its
	timeline (and optionally send them on WhatsApp)."""
	if doc.status != "Qualified" or not doc.has_value_changed("status"):
		return
	from thinknxg_estate.utils import enabled

	if not enabled("RE CRM Settings", "recommend_on_qualify", default=1):
		return
	matches = match_units(doc, limit=3)
	if not matches:
		doc.add_comment("Comment", _("No available unit matches this lead's requirements yet."))
		return
	lines = [f"{m['unit_title']} — {m['property_name']} ({m['locality'] or m['city']}): "
	         f"{frappe.utils.fmt_money(m['price'])} · {m['score']}% · {', '.join(m['reasons'])}"
	         for m in matches]
	doc.add_comment("Comment", _("Recommended properties:") + "<br>" + "<br>".join(lines))
	if enabled("RE CRM Settings", "wa_send_recommendations") and doc.mobile:
		from thinknxg_estate.channels.whatsapp import send_text

		body = _("Hi {0}, here are properties that match what you're looking for:").format(doc.full_name)
		body += "\n" + "\n".join(f"• {m['unit_title']}, {m['locality'] or m['city']}: "
		                         f"{frappe.utils.fmt_money(m['price'])}" for m in matches)
		send_text(doc.mobile, body, reference_doctype="RE Lead", reference_name=doc.name,
		          purpose="Property Recommendations",
		          variables=[doc.full_name, "; ".join(f"{m['unit_title']} ({m['locality'] or m['city']})" for m in matches)])
