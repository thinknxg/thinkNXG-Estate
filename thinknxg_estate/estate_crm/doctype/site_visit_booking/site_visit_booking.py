import frappe
from frappe import _
from frappe.model.document import Document


class SiteVisitBooking(Document):
	def validate(self):
		if self.unit:
			self.property = frappe.db.get_value("Unit", self.unit, "property") or self.property
		if not self.property:
			frappe.throw(_("Choose the property (and unit, if it has units) to be viewed."))
