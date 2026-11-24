"""Unified thinkNXG Estate dashboard data (page: /app/estate-dashboard).

Every figure is computed from live records. Filters: company, property, city and a period.
Users restricted to certain companies through User Permissions only ever see those companies.
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_months, flt, get_first_day, get_last_day, nowdate

from thinknxg_estate.core.security import staff_only

OPEN_INSTALLMENT = ("Pending", "Invoiced", "Overdue", "Partially Paid")


def _allowed_companies(company=None):
	allowed = [p.get("doc") for p in (frappe.permissions.get_user_permissions(frappe.session.user).get("Company") or [])]
	if company:
		if allowed and company not in allowed:
			frappe.throw(_("You do not have access to company {0}.").format(company), frappe.PermissionError)
		return [company]
	return allowed or None


def _scope(company, property, city):
	"""SQL condition (on alias p = Property) and values for the filters."""
	cond, values = ["1=1"], {}
	companies = _allowed_companies(company)
	if companies:
		cond.append("p.company in %(companies)s")
		values["companies"] = tuple(companies)
	if property:
		cond.append("p.name = %(property)s")
		values["property"] = property
	if city:
		cond.append("p.city = %(city)s")
		values["city"] = city
	return " and ".join(cond), values


def _one(sql, values):
	return frappe.db.sql(sql, values)[0][0] or 0


@frappe.whitelist()
@staff_only
def get_overview(company=None, property=None, city=None, from_date=None, to_date=None):
	today = nowdate()
	from_date = from_date or str(get_first_day(add_months(today, -11)))
	to_date = to_date or str(get_last_day(today))
	where, v = _scope(company, property, city)
	v.update({"from_date": from_date, "to_date": to_date, "today": today,
	          "month_start": str(get_first_day(today)), "month_end": str(get_last_day(today)),
	          "expiry_horizon": add_days(today, 90)})
	unit_join = f"`tabUnit` u join `tabProperty` p on p.name = u.property where {where}"
	lease_join = f"`tabLease Contract` lc join `tabProperty` p on p.name = lc.property where {where} and lc.docstatus = 1"
	inst_join = (f"`tabRent Installment` ri join `tabRent Schedule` rs on rs.name = ri.parent "
	             f"join `tabLease Contract` lc on lc.name = rs.lease_contract "
	             f"join `tabProperty` p on p.name = lc.property where {where} and lc.docstatus = 1 "
	             f"and ri.status != 'Cancelled'")
	# CRM scope: by unit's property when the record names a unit, else company-wide only
	crm_unit_scope = where != "1=1"

	units = {r.status: r.n for r in frappe.db.sql(
		f"select u.status, count(*) as n from {unit_join} group by u.status", v, as_dict=True)}
	kpis = {
		"total_properties": _one(f"select count(*) from `tabProperty` p where {where}", v),
		"total_units": sum(units.values()),
		"occupied_units": units.get("Occupied", 0),
		"vacant_units": units.get("Vacant", 0),
		"reserved_units": units.get("Reserved", 0),
		"active_leases": _one(f"select count(*) from {lease_join} and lc.status in ('Active', 'Expiring')", v),
		"expiring_leases": _one(f"select count(*) from {lease_join} and lc.status in ('Active', 'Expiring') "
		                        "and lc.end_date between %(today)s and %(expiry_horizon)s", v),
		"total_tenants": _one(f"select count(distinct lc.tenant) from {lease_join} "
		                      "and lc.status in ('Active', 'Expiring')", v),
		"total_owners": _one(f"select count(distinct p.owner_ref) from `tabProperty` p where {where} "
		                     "and ifnull(p.owner_ref, '') != ''", v),
		"monthly_rent_billed": flt(_one(f"select sum(ri.amount) from {inst_join} "
		                                "and ri.due_date between %(month_start)s and %(month_end)s", v), 3),
		"monthly_rent_collected": flt(_one(f"select sum(ri.paid_amount) from {inst_join} "
		                                   "and ri.due_date between %(month_start)s and %(month_end)s", v), 3),
		"outstanding_rent": flt(_one(f"select sum(ri.amount - ri.paid_amount) from {inst_join} "
		                             f"and ri.status in {OPEN_INSTALLMENT} and ri.due_date <= %(today)s", v), 3),
		"open_maintenance": _one(f"select count(*) from `tabMaintenance Request` mr join `tabProperty` p "
		                         f"on p.name = mr.property where {where} "
		                         "and mr.status in ('Open', 'In Progress', 'On Hold')", v),
	}
	kpis["occupancy_rate"] = flt(kpis["occupied_units"] * 100 / kpis["total_units"], 1) if kpis["total_units"] else 0

	if crm_unit_scope:
		lead_sql = (f"from `tabRE Lead` l join `tabUnit` u on u.name = l.unit_of_interest "
		            f"join `tabProperty` p on p.name = u.property where {where}")
		deal_sql = (f"from `tabRE Deal` d join `tabUnit` u on u.name = d.unit "
		            f"join `tabProperty` p on p.name = u.property where {where}")
		visit_sql = (f"from `tabSite Visit` sv join `tabUnit` u on u.name = sv.unit "
		             f"join `tabProperty` p on p.name = u.property where {where}")
		enquiry_sql = (f"from `tabListing Inquiry` li join `tabUnit` u on u.name = li.unit "
		               f"join `tabProperty` p on p.name = u.property where {where}")
	else:
		lead_sql, deal_sql = "from `tabRE Lead` l where 1=1", "from `tabRE Deal` d where 1=1"
		visit_sql, enquiry_sql = "from `tabSite Visit` sv where 1=1", "from `tabListing Inquiry` li where 1=1"
	kpis.update({
		"total_leads": _one(f"select count(*) {lead_sql} and date(l.creation) between %(from_date)s and %(to_date)s", v),
		"new_enquiries": _one(f"select count(*) {enquiry_sql} and li.status = 'New'", v),
		"site_visits": _one(f"select count(*) {visit_sql} and date(sv.visit_datetime) between %(from_date)s "
		                    "and %(to_date)s", v),
		"deals_closed": _one(f"select count(*) {deal_sql} and d.pipeline_stage = 'Won' "
		                     "and date(d.modified) between %(from_date)s and %(to_date)s", v),
	})

	charts = {
		"occupancy_by_property": frappe.db.sql(f"""
			select p.property_name as label, sum(u.status = 'Occupied') as occupied, count(*) as units
			from {unit_join} group by p.name order by units desc limit 15""", v, as_dict=True),
		"rent_by_month": frappe.db.sql(f"""
			select date_format(ri.due_date, '%%Y-%%m') as label, sum(ri.amount) as billed,
			       sum(ri.paid_amount) as collected
			from {inst_join} and ri.due_date between %(from_date)s and %(to_date)s
			group by label order by label""", v, as_dict=True),
		"revenue_by_property": frappe.db.sql(f"""
			select p.property_name as label, sum(ri.paid_amount) as collected
			from {inst_join} and ri.due_date between %(from_date)s and %(to_date)s
			group by p.name order by collected desc limit 10""", v, as_dict=True),
		"property_types": frappe.db.sql(f"""
			select coalesce(p.property_type, '(not set)') as label, count(*) as value
			from `tabProperty` p where {where} group by label order by value desc""", v, as_dict=True),
		"lease_expiry_by_month": frappe.db.sql(f"""
			select date_format(lc.end_date, '%%Y-%%m') as label, count(*) as value from {lease_join}
			and lc.status in ('Active', 'Expiring') and lc.end_date between %(today)s and %(expiry_horizon_12)s
			group by label order by label""", dict(v, expiry_horizon_12=add_months(today, 12)), as_dict=True),
		"maintenance_by_status": frappe.db.sql(f"""
			select mr.status as label, count(*) as value from `tabMaintenance Request` mr
			join `tabProperty` p on p.name = mr.property where {where}
			group by mr.status order by value desc""", v, as_dict=True),
		"pipeline": frappe.db.sql(f"""
			select d.pipeline_stage as label, count(*) as value, coalesce(sum(d.expected_value), 0) as amount
			{deal_sql} group by d.pipeline_stage""", v, as_dict=True),
		"lead_funnel": [
			{"label": _("Leads"), "value": kpis["total_leads"]},
			{"label": _("Qualified"), "value": _one(f"select count(*) {lead_sql} and l.status in ('Qualified', 'Converted') "
			                                         "and date(l.creation) between %(from_date)s and %(to_date)s", v)},
			{"label": _("Site visits"), "value": kpis["site_visits"]},
			{"label": _("Won"), "value": kpis["deals_closed"]},
		],
		"agent_performance": frappe.db.sql(f"""
			select a.agent_name as label, count(*) as deals, sum(d.pipeline_stage = 'Won') as won
			{deal_sql.replace('where', 'join `tabRE Agent` a on a.name = d.assigned_agent where', 1)}
			and date(d.creation) between %(from_date)s and %(to_date)s
			group by a.name order by won desc, deals desc limit 10""", v, as_dict=True),
	}
	order = ["New", "Contacted", "Site Visit Scheduled", "Negotiation", "Reservation", "Won", "Lost"]
	charts["pipeline"].sort(key=lambda r: order.index(r.label) if r.label in order else 99)
	return {"kpis": kpis, "charts": charts,
	        "filters": {"company": company, "property": property, "city": city,
	                    "from_date": from_date, "to_date": to_date}}
