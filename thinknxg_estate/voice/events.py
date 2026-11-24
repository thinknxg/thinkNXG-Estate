"""Document hooks — rescore on the events that actually move a lead."""

import frappe


def on_site_visit_update(doc, method=None):
    if not doc.outcome:
        return
    lead = frappe.db.get_value("RE Deal", doc.deal, "lead")
    if lead and frappe.db.get_single_value("AI Settings", "enable_scoring"):
        frappe.enqueue("thinknxg_estate.voice.ai.scoring.recompute_lead_score", queue="long",
                       lead_name=lead, job_id=f"lead_score::{lead}", deduplicate=True,
                       enqueue_after_commit=True)


def on_lead_insert(doc, method=None):
    # Data Import and other bulk loads skip the per-lead job (thousands would overflow the
    # background queue); the nightly scoring run scores those leads.
    if frappe.flags.in_import or frappe.flags.in_migrate or frappe.flags.estate_bulk_load:
        return
    if frappe.db.get_single_value("AI Settings", "enable_scoring"):
        frappe.enqueue("thinknxg_estate.voice.ai.scoring.recompute_lead_score", queue="long",
                       lead_name=doc.name, job_id=f"lead_score::{doc.name}", deduplicate=True,
                       enqueue_after_commit=True)
