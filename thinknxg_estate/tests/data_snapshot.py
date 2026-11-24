"""Row counts for every platform table (bench --site SITE execute thinknxg_estate.tests.data_snapshot.run).
Used to prove that the legacy upgrade does not lose or duplicate business data."""
import json

import frappe

DOCTYPES = [
	"Property", "Unit", "Property Owner", "Amenity", "Property Amenity", "Property Photo", "Property Document",
	"Property Unit Charge", "Utility Account", "Tenant", "Tenant KYC Document", "Tenant Portal Session",
	"Lease Contract", "Lease Charge", "Move In Out Inspection", "Inspection Item", "Rent Schedule",
	"Rent Installment", "Rent Installment Payment", "Post Dated Cheque", "Security Deposit",
	"Rent Credit Balance", "Owner Statement", "Owner Statement Line", "Tenancy Bulk Payment",
	"Tenancy Bulk Payment Row", "Partial Payment Table", "Expense Property", "Maintenance Request",
	"Maintenance Job", "RE Lead", "RE Deal", "RE Agent", "Commission Entry", "Commission Slab",
	"Lead Source RE", "Reservation", "Site Visit", "WhatsApp Message Log", "Property Enquiry",
	"Site Visit Booking", "Saved Search", "Property Wishlist", "Listing", "Listing Photo",
	"Listing Inquiry", "Portal Chat Session", "Command Entity", "Conversation Session", "Customer Thread",
	"Lead Score Log", "Sentiment Reading", "Thread Message", "Voice Command", "Voice Intent",
	"Voice Locale Profile", "Voice Message", "Voice Usage Log", "WhatsApp Template", "WhatsApp Webhook Log",
	"Customer", "Lead", "Supplier", "Sales Invoice", "Payment Entry", "Journal Entry",
]


def run(path=None):
	counts = {dt: frappe.db.sql(f"select count(*) from `tab{dt}`")[0][0] for dt in DOCTYPES
	          if frappe.db.table_exists(dt)}
	# a content checksum on the core financial table, not only a count
	counts["_rent_installment_amount_sum"] = float(
		frappe.db.sql("select coalesce(sum(amount),0) from `tabRent Installment`")[0][0])
	counts["_lease_value_sum"] = float(
		frappe.db.sql("select coalesce(sum(total_contract_value),0) from `tabLease Contract`")[0][0])
	counts["_unit_custom_values"] = frappe.db.sql(
		"select count(*) from `tabUnit` where ifnull(ownership_type,'')!='' or ifnull(published_to_portal,0)=1")[0][0]
	if path:
		with open(path, "w") as f:
			json.dump(counts, f, indent=1, sort_keys=True)
	return counts
