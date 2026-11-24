"""Generate the Phase 7 Script Reports (JSON + JS filters + Python). Run from repo root."""
import json
import os
import textwrap

APP = "thinknxg_estate"
TS = "2026-11-24 14:00:00.000000"
STAFF = ["RE Manager", "Property Manager", "Accounts User", "System Manager"]
CRM = ["RE Manager", "RE Sales Manager", "System Manager"]
MAINT = ["RE Manager", "Property Manager", "Maintenance Supervisor", "System Manager"]

COMPANY = '{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" }'
FROM = ('{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", reqd: 1, '
        'default: frappe.datetime.year_start() }')
TO = '{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.year_end() }'
PROPERTY = '{ fieldname: "property", label: __("Property"), fieldtype: "Link", options: "Property" }'
CITY = '{ fieldname: "city", label: __("City"), fieldtype: "Data" }'

REPORTS = {
	# name: (module folder, ref doctype, roles, [js filters], python body)
	"Property Register": ("estate_property", "Property", STAFF + ["Leasing Officer"], [COMPANY, CITY], '''
def execute(filters=None):
	f = frappe._dict(filters or {})
	cond, values = _conditions(f)
	rows = frappe.db.sql(f"""
		select p.name as property, p.property_name, p.property_type, p.city, p.area, p.company,
		       p.owner_ref, o.owner_name,
		       count(u.name) as units,
		       sum(u.status = 'Occupied') as occupied, sum(u.status = 'Vacant') as vacant,
		       sum(u.status = 'Reserved') as reserved,
		       coalesce(sum(u.annual_rent), 0) as rent_potential,
		       coalesce(sum(case when u.status = 'Occupied' then u.annual_rent else 0 end), 0) as rent_occupied
		from `tabProperty` p
		left join `tabUnit` u on u.property = p.name
		left join `tabProperty Owner` o on o.name = p.owner_ref
		where 1=1 {cond}
		group by p.name order by p.property_name""", values, as_dict=True)
	for r in rows:
		r.occupancy = flt(flt(r.occupied) * 100 / r.units, 1) if r.units else 0
	columns = [
		col("Property", "property", "Link", "Property", 120), col("Name", "property_name", "Data", None, 180),
		col("Type", "property_type", "Data", None, 130), col("City", "city", "Data", None, 100),
		col("Area", "area", "Data", None, 110), col("Owner", "owner_name", "Data", None, 150),
		col("Units", "units", "Int", None, 70), col("Occupied", "occupied", "Int", None, 80),
		col("Vacant", "vacant", "Int", None, 70), col("Reserved", "reserved", "Int", None, 80),
		col("Occupancy %", "occupancy", "Percent", None, 100),
		col("Rent Potential (Annual)", "rent_potential", "Currency", None, 150),
		col("Rent Occupied (Annual)", "rent_occupied", "Currency", None, 150),
	]
	return columns, rows


def _conditions(f):
	cond, values = [], {}
	if f.company:
		cond.append("p.company = %(company)s"); values["company"] = f.company
	if f.city:
		cond.append("p.city like %(city)s"); values["city"] = f"%{f.city}%"
	return "".join(" and " + c for c in cond), values
'''),
	"Unit Availability": ("estate_property", "Unit", STAFF + ["Leasing Officer", "RE Sales Manager", "RE Sales Agent"],
	                      [COMPANY, PROPERTY, '{ fieldname: "available_by", label: __("Available By"), fieldtype: "Date" }',
	                       '{ fieldname: "unit_type", label: __("Unit Type"), fieldtype: "Select", options: "\\nStudio\\n1BR\\n2BR\\n3BR\\n4BR+\\nPenthouse\\nShop\\nOffice\\nWarehouse" }'], '''
def execute(filters=None):
	f = frappe._dict(filters or {})
	values = {"available_by": f.available_by or nowdate()}
	cond = ""
	if f.company:
		cond += " and u.company = %(company)s"; values["company"] = f.company
	if f.property:
		cond += " and u.property = %(property)s"; values["property"] = f.property
	if f.unit_type:
		cond += " and u.unit_type = %(unit_type)s"; values["unit_type"] = f.unit_type
	rows = frappe.db.sql(f"""
		select u.name as unit, u.unit_title, u.property, p.property_name, p.city, u.unit_type, u.bedrooms,
		       u.area_sqm, u.furnishing, u.status, u.annual_rent, lc.name as current_lease,
		       lc.end_date as lease_end,
		       (select count(*) from `tabListing` l where l.unit = u.name and l.is_published = 1) as listed
		from `tabUnit` u join `tabProperty` p on p.name = u.property
		left join `tabLease Contract` lc on lc.name = u.current_lease
		where (u.status in ('Vacant', 'Reserved')
		       or (u.status = 'Occupied' and lc.end_date <= %(available_by)s)) {cond}
		order by u.status desc, lc.end_date, p.property_name, u.unit_no""", values, as_dict=True)
	for r in rows:
		r.available_from = r.lease_end if r.status == "Occupied" else nowdate()
		r.listed = "Yes" if r.listed else "No"
	columns = [
		col("Unit", "unit", "Link", "Unit", 110), col("Title", "unit_title", "Data", None, 150),
		col("Property", "property_name", "Data", None, 160), col("City", "city", "Data", None, 100),
		col("Type", "unit_type", "Data", None, 80), col("Beds", "bedrooms", "Int", None, 60),
		col("Area (sqm)", "area_sqm", "Float", None, 90), col("Furnishing", "furnishing", "Data", None, 120),
		col("Status", "status", "Data", None, 90), col("Available From", "available_from", "Date", None, 120),
		col("Annual Rent", "annual_rent", "Currency", None, 120), col("Listed", "listed", "Data", None, 70),
		col("Current Lease", "current_lease", "Link", "Lease Contract", 140),
	]
	return columns, rows
'''),
	"Tenant Register": ("estate_leasing", "Tenant", STAFF + ["Leasing Officer"], [COMPANY,
	                    '{ fieldname: "only_active", label: __("Only Tenants with an Active Lease"), fieldtype: "Check", default: 1 }'], '''
def execute(filters=None):
	f = frappe._dict(filters or {})
	values, cond = {}, ""
	if f.company:
		cond += " and lc.company = %(company)s"; values["company"] = f.company
	join = "join" if cint(f.get("only_active", 1)) else "left join"
	rows = frappe.db.sql(f"""
		select t.name as tenant, t.tenant_name, t.tenant_type, t.nationality, t.mobile, t.email,
		       lc.name as lease, lc.unit, lc.property, lc.start_date, lc.end_date, lc.status as lease_status,
		       lc.total_contract_value, lc.rent_schedule, lc.security_deposit
		from `tabTenant` t
		{join} `tabLease Contract` lc on lc.tenant = t.name and lc.docstatus = 1
		       and lc.status in ('Active', 'Expiring') {cond}
		where t.disabled = 0
		order by t.tenant_name""", values, as_dict=True)
	for r in rows:
		r.outstanding = flt(frappe.db.sql("""
			select coalesce(sum(amount - paid_amount), 0) from `tabRent Installment`
			where parent = %s and status in ('Pending', 'Invoiced', 'Overdue', 'Partially Paid')
			  and due_date <= %s""", (r.rent_schedule, nowdate()))[0][0]) if r.rent_schedule else 0
		r.deposit_held = flt(frappe.db.get_value("Security Deposit", {"name": r.security_deposit,
		                                                              "status": "Held"}, "amount")) if r.security_deposit else 0
	columns = [
		col("Tenant", "tenant", "Link", "Tenant", 110), col("Name", "tenant_name", "Data", None, 170),
		col("Type", "tenant_type", "Data", None, 90), col("Nationality", "nationality", "Data", None, 100),
		col("Mobile", "mobile", "Data", None, 120), col("Email", "email", "Data", None, 170),
		col("Lease", "lease", "Link", "Lease Contract", 140), col("Unit", "unit", "Link", "Unit", 100),
		col("Start", "start_date", "Date", None, 100), col("End", "end_date", "Date", None, 100),
		col("Status", "lease_status", "Data", None, 80),
		col("Contract Value", "total_contract_value", "Currency", None, 120),
		col("Outstanding Rent", "outstanding", "Currency", None, 120),
		col("Deposit Held", "deposit_held", "Currency", None, 110),
	]
	return columns, rows
'''),
	"Deposit Register": ("estate_finance", "Security Deposit", STAFF, [COMPANY,
	                     '{ fieldname: "status", label: __("Status"), fieldtype: "Select", options: "\\nHeld\\nPartially Refunded\\nRefunded\\nForfeited\\nDraft" }'], '''
def execute(filters=None):
	f = frappe._dict(filters or {})
	flt_ = {"docstatus": ["<", 2]}
	if f.company:
		flt_["company"] = f.company
	if f.status:
		flt_["status"] = f.status
	rows = frappe.get_all("Security Deposit", filters=flt_, fields=[
		"name as deposit", "tenant", "lease_contract", "company", "received_date", "status", "amount",
		"deduction_amount", "refunded_amount", "deduction_reason", "journal_entry", "refund_payment_entry"],
		order_by="received_date desc")
	for r in rows:
		r.tenant_name = frappe.db.get_value("Tenant", r.tenant, "tenant_name")
		r.lease_status = frappe.db.get_value("Lease Contract", r.lease_contract, "status")
		r.held = flt(r.amount) if r.status == "Held" else 0
	columns = [
		col("Deposit", "deposit", "Link", "Security Deposit", 110), col("Tenant", "tenant_name", "Data", None, 160),
		col("Lease", "lease_contract", "Link", "Lease Contract", 140), col("Lease Status", "lease_status", "Data", None, 100),
		col("Received", "received_date", "Date", None, 100), col("Status", "status", "Data", None, 120),
		col("Amount", "amount", "Currency", None, 110), col("Held", "held", "Currency", None, 110),
		col("Deducted", "deduction_amount", "Currency", None, 110),
		col("Refunded", "refunded_amount", "Currency", None, 110),
		col("Deduction Reason", "deduction_reason", "Data", None, 180),
		col("Journal Entry", "journal_entry", "Link", "Journal Entry", 130),
	]
	totals = {"amount": sum(flt(r.amount) for r in rows), "held": sum(r.held for r in rows)}
	summary = [{"label": _("Deposits held"), "value": totals["held"], "datatype": "Currency", "indicator": "Blue"},
	           {"label": _("Deposits recorded"), "value": totals["amount"], "datatype": "Currency"}]
	return columns, rows, None, None, summary
'''),
	"Property Profitability": ("estate_finance", "Property", STAFF, [COMPANY, FROM, TO, PROPERTY], '''
def execute(filters=None):
	f = frappe._dict(filters or {})
	values = {"from_date": f.from_date, "to_date": f.to_date}
	pcond = ""
	if f.company:
		pcond += " and p.company = %(company)s"; values["company"] = f.company
	if f.property:
		pcond += " and p.name = %(property)s"; values["property"] = f.property
	props = frappe.db.sql(f"select p.name, p.property_name, p.city from `tabProperty` p where 1=1 {pcond} "
	                      "order by p.property_name", values, as_dict=True)
	rows = []
	for p in props:
		v = dict(values, property=p.name)
		billed, collected = frappe.db.sql("""
			select coalesce(sum(ri.amount), 0), coalesce(sum(ri.paid_amount), 0)
			from `tabRent Installment` ri join `tabRent Schedule` rs on rs.name = ri.parent
			join `tabLease Contract` lc on lc.name = rs.lease_contract
			where lc.property = %(property)s and lc.docstatus = 1
			  and ri.status != 'Cancelled' and ri.due_date between %(from_date)s and %(to_date)s""", v)[0]
		expenses = frappe.db.sql("""
			select coalesce(sum(amount), 0) from `tabExpense Property`
			where property = %(property)s and docstatus = 1
			  and expense_date between %(from_date)s and %(to_date)s""", v)[0][0]
		maintenance = frappe.db.sql("""
			select coalesce(sum(total_cost), 0) from `tabMaintenance Job`
			where property = %(property)s and docstatus = 1 and billable_to in ('Owner', 'Company')
			  and coalesce(completion_date, scheduled_date) between %(from_date)s and %(to_date)s""", v)[0][0]
		net = flt(collected) - flt(expenses) - flt(maintenance)
		rows.append({"property": p.name, "property_name": p.property_name, "city": p.city,
		             "rent_billed": flt(billed), "rent_collected": flt(collected),
		             "collection_rate": flt(flt(collected) * 100 / flt(billed), 1) if flt(billed) else 0,
		             "expenses": flt(expenses), "maintenance": flt(maintenance), "net_income": net,
		             "margin": flt(net * 100 / flt(collected), 1) if flt(collected) else 0})
	columns = [
		col("Property", "property", "Link", "Property", 120), col("Name", "property_name", "Data", None, 180),
		col("City", "city", "Data", None, 100), col("Rent Billed", "rent_billed", "Currency", None, 130),
		col("Rent Collected", "rent_collected", "Currency", None, 130),
		col("Collection %", "collection_rate", "Percent", None, 100),
		col("Expenses", "expenses", "Currency", None, 120), col("Maintenance", "maintenance", "Currency", None, 120),
		col("Net Income", "net_income", "Currency", None, 130), col("Margin %", "margin", "Percent", None, 90),
	]
	chart = {"data": {"labels": [r["property_name"] for r in rows],
	                  "datasets": [{"name": _("Net Income"), "values": [r["net_income"] for r in rows]}]},
	         "type": "bar"}
	return columns, rows, None, chart
'''),
	"Lead Source Analysis": ("estate_crm", "RE Lead", CRM, [FROM, TO], '''
def execute(filters=None):
	f = frappe._dict(filters or {})
	rows = frappe.db.sql("""
		select coalesce(l.source, '(not set)') as source, count(*) as leads,
		       sum(l.status in ('Qualified', 'Converted')) as qualified,
		       sum(l.deal is not null and l.deal != '') as with_deal,
		       sum(d.pipeline_stage = 'Won') as won,
		       coalesce(sum(case when d.pipeline_stage = 'Won' then d.expected_value end), 0) as won_value
		from `tabRE Lead` l left join `tabRE Deal` d on d.name = l.deal
		where date(l.creation) between %(from_date)s and %(to_date)s
		group by coalesce(l.source, '(not set)') order by leads desc""",
		{"from_date": f.from_date, "to_date": f.to_date}, as_dict=True)
	for r in rows:
		r.qualified_rate = flt(flt(r.qualified) * 100 / r.leads, 1) if r.leads else 0
		r.win_rate = flt(flt(r.won) * 100 / r.leads, 1) if r.leads else 0
	columns = [
		col("Source", "source", "Data", None, 150), col("Leads", "leads", "Int", None, 80),
		col("Qualified", "qualified", "Int", None, 90), col("Qualified %", "qualified_rate", "Percent", None, 100),
		col("Deals", "with_deal", "Int", None, 80), col("Won", "won", "Int", None, 70),
		col("Lead → Won %", "win_rate", "Percent", None, 110), col("Won Value", "won_value", "Currency", None, 130),
	]
	chart = {"data": {"labels": [r.source for r in rows],
	                  "datasets": [{"name": _("Leads"), "values": [r.leads for r in rows]},
	                               {"name": _("Won"), "values": [flt(r.won) for r in rows]}]},
	         "type": "bar"}
	return columns, rows, None, chart
'''),
	"Site Visit Conversion": ("estate_crm", "Site Visit", CRM, [FROM, TO,
	                          '{ fieldname: "agent", label: __("Agent"), fieldtype: "Link", options: "RE Agent" }'], '''
def execute(filters=None):
	f = frappe._dict(filters or {})
	values = {"from_date": f.from_date, "to_date": f.to_date}
	cond = ""
	if f.agent:
		cond = " and sv.agent = %(agent)s"; values["agent"] = f.agent
	rows = frappe.db.sql(f"""
		select coalesce(sv.agent, '(unassigned)') as agent, a.agent_name, count(*) as visits,
		       sum(sv.outcome = 'Interested') as interested, sum(sv.outcome = 'Considering') as considering,
		       sum(sv.outcome = 'Not Interested') as not_interested, sum(sv.outcome = 'No Show') as no_show,
		       sum(coalesce(sv.outcome, '') = '') as pending,
		       count(distinct case when d.pipeline_stage = 'Won' then d.name end) as deals_won
		from `tabSite Visit` sv left join `tabRE Deal` d on d.name = sv.deal
		left join `tabRE Agent` a on a.name = sv.agent
		where date(sv.visit_datetime) between %(from_date)s and %(to_date)s {cond}
		group by coalesce(sv.agent, '(unassigned)') order by visits desc""", values, as_dict=True)
	for r in rows:
		held = flt(r.visits) - flt(r.no_show) - flt(r.pending)
		r.interest_rate = flt(flt(r.interested) * 100 / held, 1) if held else 0
		r.conversion = flt(flt(r.deals_won) * 100 / r.visits, 1) if r.visits else 0
	columns = [
		col("Agent", "agent", "Link", "RE Agent", 110), col("Name", "agent_name", "Data", None, 150),
		col("Visits", "visits", "Int", None, 70), col("Interested", "interested", "Int", None, 90),
		col("Considering", "considering", "Int", None, 100), col("Not Interested", "not_interested", "Int", None, 110),
		col("No Show", "no_show", "Int", None, 80), col("Outcome Pending", "pending", "Int", None, 120),
		col("Interest %", "interest_rate", "Percent", None, 90), col("Deals Won", "deals_won", "Int", None, 90),
		col("Visit → Won %", "conversion", "Percent", None, 110),
	]
	return columns, rows
'''),
	"Broker Commission Statement": ("estate_crm", "Commission Entry", CRM + ["Accounts User", "RE Sales Agent"],
	                                [FROM, TO, '{ fieldname: "agent", label: __("Agent / Broker"), fieldtype: "Link", options: "RE Agent" }',
	                                 '{ fieldname: "status", label: __("Status"), fieldtype: "Select", options: "\\nDraft\\nApproved\\nPaid" }'], '''
def execute(filters=None):
	f = frappe._dict(filters or {})
	values = {"from_date": f.from_date, "to_date": f.to_date}
	cond = ""
	if f.agent:
		cond += " and ce.agent = %(agent)s"; values["agent"] = f.agent
	if f.status:
		cond += " and ce.status = %(status)s"; values["status"] = f.status
	# sales agents only ever see their own statement
	from thinknxg_estate.core.permissions import _restricted_agent
	own = _restricted_agent(frappe.session.user)
	if own is not None:
		cond += " and ce.agent in %(own)s"; values["own"] = tuple(own or [""])
	rows = frappe.db.sql(f"""
		select ce.name as entry, ce.agent, a.agent_name, a.agent_type, a.brokerage_name,
		       date(ce.creation) as date, ce.deal, ce.lease_contract, lc.unit, lc.tenant_name,
		       ce.base_amount, ce.commission_amount, ce.status, ce.journal_entry
		from `tabCommission Entry` ce join `tabRE Agent` a on a.name = ce.agent
		left join `tabLease Contract` lc on lc.name = ce.lease_contract
		where ce.docstatus < 2 and date(ce.creation) between %(from_date)s and %(to_date)s {cond}
		order by a.agent_name, ce.creation""", values, as_dict=True)
	columns = [
		col("Entry", "entry", "Link", "Commission Entry", 110), col("Agent", "agent_name", "Data", None, 150),
		col("Type", "agent_type", "Data", None, 120), col("Brokerage", "brokerage_name", "Data", None, 140),
		col("Date", "date", "Date", None, 100), col("Deal", "deal", "Link", "RE Deal", 130),
		col("Lease", "lease_contract", "Link", "Lease Contract", 140), col("Unit", "unit", "Link", "Unit", 100),
		col("Tenant", "tenant_name", "Data", None, 140), col("Base Amount", "base_amount", "Currency", None, 120),
		col("Commission", "commission_amount", "Currency", None, 120), col("Status", "status", "Data", None, 90),
	]
	paid = sum(flt(r.commission_amount) for r in rows if r.status == "Paid")
	due = sum(flt(r.commission_amount) for r in rows if r.status == "Approved")
	summary = [{"label": _("Commission paid"), "value": paid, "datatype": "Currency", "indicator": "Green"},
	           {"label": _("Approved, not yet paid"), "value": due, "datatype": "Currency", "indicator": "Orange"}]
	return columns, rows, None, None, summary
'''),
	"Vendor Performance": ("estate_maintenance", "Maintenance Job", MAINT + ["Accounts User"], [COMPANY, FROM, TO], '''
def execute(filters=None):
	f = frappe._dict(filters or {})
	values = {"from_date": f.from_date, "to_date": f.to_date}
	cond = ""
	if f.company:
		cond = " and mj.company = %(company)s"; values["company"] = f.company
	rows = frappe.db.sql(f"""
		select coalesce(mj.supplier, mj.employee, '(unassigned)') as vendor, mj.assigned_type,
		       count(*) as jobs, sum(mj.docstatus = 1) as submitted,
		       sum(mj.completion_date is not null) as completed,
		       avg(case when mj.completion_date is not null
		                then datediff(mj.completion_date, date(mr.creation)) end) as avg_days,
		       sum(mr.priority = 'Emergency') as emergencies,
		       coalesce(sum(mj.material_cost), 0) as material_cost,
		       coalesce(sum(mj.labor_cost), 0) as labor_cost, coalesce(sum(mj.total_cost), 0) as total_cost
		from `tabMaintenance Job` mj left join `tabMaintenance Request` mr on mr.name = mj.maintenance_request
		where mj.docstatus < 2 and coalesce(mj.scheduled_date, date(mj.creation)) between %(from_date)s and %(to_date)s
		      {cond}
		group by coalesce(mj.supplier, mj.employee, '(unassigned)'), mj.assigned_type
		order by jobs desc""", values, as_dict=True)
	for r in rows:
		r.avg_days = flt(r.avg_days, 1) if r.avg_days is not None else None
		r.completion_rate = flt(flt(r.completed) * 100 / r.jobs, 1) if r.jobs else 0
		r.avg_cost = flt(flt(r.total_cost) / r.jobs, 3) if r.jobs else 0
	columns = [
		col("Vendor / Technician", "vendor", "Data", None, 180), col("Type", "assigned_type", "Data", None, 90),
		col("Jobs", "jobs", "Int", None, 70), col("Completed", "completed", "Int", None, 90),
		col("Completion %", "completion_rate", "Percent", None, 100),
		col("Avg Days to Complete", "avg_days", "Float", None, 140), col("Emergencies", "emergencies", "Int", None, 100),
		col("Material", "material_cost", "Currency", None, 110), col("Labour", "labor_cost", "Currency", None, 110),
		col("Total Cost", "total_cost", "Currency", None, 120), col("Avg Cost per Job", "avg_cost", "Currency", None, 130),
	]
	return columns, rows
'''),
}

HEADER = '''"""{name} (thinkNXG Estate). Generated by scripts/consolidation/build_reports.py; edit freely."""

import frappe
from frappe import _
from frappe.utils import cint, flt, nowdate


def col(label, fieldname, fieldtype, options=None, width=120):
	c = {{"label": _(label), "fieldname": fieldname, "fieldtype": fieldtype, "width": width}}
	if options:
		c["options"] = options
	return c

'''

MODULES = {"estate_property": "Estate Property", "estate_leasing": "Estate Leasing",
           "estate_finance": "Estate Finance", "estate_crm": "Estate CRM",
           "estate_maintenance": "Estate Maintenance"}

for name, (folder, ref, roles, filters, body) in REPORTS.items():
	scrub = name.lower().replace(" ", "_")
	path = os.path.join(APP, folder, "report", scrub)
	os.makedirs(path, exist_ok=True)
	open(os.path.join(path, "__init__.py"), "w").close()
	with open(os.path.join(path, f"{scrub}.py"), "w") as fh:
		fh.write(HEADER.format(name=name) + textwrap.dedent(body).lstrip("\n"))
	with open(os.path.join(path, f"{scrub}.js"), "w") as fh:
		fh.write(f'frappe.query_reports["{name}"] = {{\n\tfilters: [\n'
		         + "".join(f"\t\t{x},\n" for x in filters) + "\t],\n};\n")
	with open(os.path.join(path, f"{scrub}.json"), "w") as fh:
		json.dump({
			"add_total_row": 1 if name in ("Property Profitability", "Deposit Register", "Vendor Performance",
			                               "Broker Commission Statement", "Property Register") else 0,
			"columns": [], "creation": TS, "disable_prepared_report": 0, "disabled": 0, "docstatus": 0,
			"doctype": "Report", "filters": [], "idx": 0, "is_standard": "Yes", "modified": TS,
			"modified_by": "Administrator", "module": MODULES[folder], "name": name, "owner": "Administrator",
			"prepared_report": 0, "ref_doctype": ref, "report_name": name, "report_type": "Script Report",
			"roles": [{"role": r} for r in dict.fromkeys(roles)],
		}, fh, indent=1)
		fh.write("\n")
	print("report", name)
