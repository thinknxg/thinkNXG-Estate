# Agent Leaderboard: pipeline activity and closed value per agent in a period.
import frappe
from frappe import _
from frappe.utils import flt, getdate, month_diff


def execute(filters=None):
    filters = frappe._dict(filters or {})
    conditions = {"from_date": filters.get("from_date") or "1900-01-01",
                  "to_date": filters.get("to_date") or "2999-12-31"}

    agents = frappe.get_all("RE Agent", filters={"is_active": 1},
                            fields=["name", "agent_name", "agent_type", "monthly_deal_target",
                                    "monthly_value_target"], order_by="name")
    months = (month_diff(filters.to_date, filters.from_date)
              if filters.get("from_date") and filters.get("to_date") else 0)
    data = []
    for agent in agents:
        params = dict(conditions, agent=agent.name)
        leads = frappe.db.sql("""
            SELECT COUNT(*) FROM `tabRE Lead`
            WHERE assigned_agent = %(agent)s
              AND DATE(creation) BETWEEN %(from_date)s AND %(to_date)s
        """, params)[0][0]
        visits = frappe.db.sql("""
            SELECT COUNT(*) FROM `tabSite Visit`
            WHERE agent = %(agent)s
              AND DATE(visit_datetime) BETWEEN %(from_date)s AND %(to_date)s
        """, params)[0][0]
        deals, won, won_value = frappe.db.sql("""
            SELECT COUNT(*),
                   SUM(CASE WHEN pipeline_stage = 'Won' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN pipeline_stage = 'Won'
                            THEN COALESCE(expected_value, 0) ELSE 0 END)
            FROM `tabRE Deal`
            WHERE assigned_agent = %(agent)s
              AND DATE(creation) BETWEEN %(from_date)s AND %(to_date)s
        """, params)[0]
        commission = frappe.db.sql("""
            SELECT COALESCE(SUM(commission_amount), 0) FROM `tabCommission Entry`
            WHERE agent = %(agent)s AND docstatus = 1
              AND DATE(creation) BETWEEN %(from_date)s AND %(to_date)s
        """, params)[0][0]
        # Won value should reflect the lease, not the estimate, where linked
        lease_value = frappe.db.sql("""
            SELECT COALESCE(SUM(lc.total_contract_value), 0)
            FROM `tabRE Deal` d
            JOIN `tabLease Contract` lc ON lc.name = d.lease_contract
            WHERE d.assigned_agent = %(agent)s AND d.pipeline_stage = 'Won'
              AND DATE(d.creation) BETWEEN %(from_date)s AND %(to_date)s
        """, params)[0][0]

        deals, won = int(deals or 0), int(won or 0)
        data.append({
            "agent": agent.name, "agent_name": agent.agent_name,
            "leads": int(leads or 0), "site_visits": int(visits or 0),
            "deals": deals, "won": won,
            "win_rate": flt(won * 100 / deals, 1) if deals else 0,
            "won_value": flt(lease_value or won_value or 0, 3),
            "commission": flt(commission, 3),
            "agent_type": agent.agent_type,
        })
        row = data[-1]
        if months:
            row["deal_target"] = int(agent.monthly_deal_target or 0) * months
            row["value_target"] = flt(agent.monthly_value_target) * months
            row["deal_achievement"] = flt(won * 100 / row["deal_target"], 1) if row["deal_target"] else None
            row["value_achievement"] = (flt(row["won_value"] * 100 / row["value_target"], 1)
                                        if row["value_target"] else None)

    data.sort(key=lambda r: r["won_value"], reverse=True)
    chart = {
        "data": {
            "labels": [d["agent_name"] for d in data],
            "datasets": [{"name": _("Won Value"),
                          "values": [d["won_value"] for d in data]}],
        },
        "type": "bar",
    }
    return get_columns(), data, None, chart


def get_columns():
    return [
        {"label": _("Agent"), "fieldname": "agent", "fieldtype": "Link",
         "options": "RE Agent", "width": 110},
        {"label": _("Name"), "fieldname": "agent_name", "fieldtype": "Data", "width": 150},
        {"label": _("Leads"), "fieldname": "leads", "fieldtype": "Int", "width": 80},
        {"label": _("Site Visits"), "fieldname": "site_visits", "fieldtype": "Int", "width": 95},
        {"label": _("Deals"), "fieldname": "deals", "fieldtype": "Int", "width": 80},
        {"label": _("Won"), "fieldname": "won", "fieldtype": "Int", "width": 70},
        {"label": _("Win Rate %"), "fieldname": "win_rate", "fieldtype": "Percent", "width": 95},
        {"label": _("Won Value"), "fieldname": "won_value", "fieldtype": "Currency", "width": 130},
        {"label": _("Commission"), "fieldname": "commission", "fieldtype": "Currency", "width": 120},
        {"label": _("Type"), "fieldname": "agent_type", "fieldtype": "Data", "width": 120},
        {"label": _("Deal Target"), "fieldname": "deal_target", "fieldtype": "Int", "width": 100},
        {"label": _("Deals vs Target %"), "fieldname": "deal_achievement", "fieldtype": "Percent", "width": 130},
        {"label": _("Value Target"), "fieldname": "value_target", "fieldtype": "Currency", "width": 130},
        {"label": _("Value vs Target %"), "fieldname": "value_achievement", "fieldtype": "Percent", "width": 130},
    ]
