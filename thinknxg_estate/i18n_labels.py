"""Strings shown in the desk that the translation extractor cannot find on its own (module names,
which Frappe translates at runtime). Listed here so they reach locale/main.pot."""

from frappe import _


def module_labels():
	return [
		_("Estate Property"), _("Estate Leasing"), _("Estate Finance"), _("Estate Maintenance"),
		_("Estate CRM"), _("Estate Portal"), _("Estate Voice"), _("thinkNXG Estate"),
	]


def field_label_contexts():
	"""Field labels whose real-estate meaning differs from Frappe's generic translation (for example
	"Property" is an asset, not a building, elsewhere). Forms look labels up with the DocType as
	context, so these apply on Estate forms only."""
	return [
		_("Area", context="Listing"),
		_("Interest", context="Listing Inquiry"),
		_("Interest", context="RE Deal"),
		_("Interest", context="RE Lead"),
		_("Property", context="Expense Property"),
		_("Property", context="Lease Contract"),
		_("Property", context="Listing"),
		_("Property", context="Maintenance Job"),
		_("Property", context="Maintenance Request"),
		_("Property", context="Move In Out Inspection"),
		_("Property", context="Property"),
		_("Property", context="Property Document"),
		_("Property", context="Property Enquiry"),
		_("Property", context="Property Wishlist"),
		_("Property", context="Site Visit Booking"),
		_("Property", context="Tenancy Bulk Payment"),
		_("Property", context="Unit"),
		_("Property", context="Utility Account"),
		_("Property Type", context="Property"),
		_("Unit", context="Lease Contract"),
		_("Unit", context="Listing"),
		_("Unit", context="Listing Inquiry"),
		_("Unit", context="Maintenance Job"),
		_("Unit", context="Maintenance Request"),
		_("Unit", context="Move In Out Inspection"),
		_("Unit", context="Owner Statement Line"),
		_("Unit", context="Property Enquiry"),
		_("Unit", context="Property Photo"),
		_("Unit", context="Property Wishlist"),
		_("Unit", context="RE Deal"),
		_("Unit", context="Reservation"),
		_("Unit", context="Site Visit"),
		_("Unit", context="Site Visit Booking"),
		_("Unit", context="Tenancy Bulk Payment"),
		_("Unit", context="Unit"),
		_("Unit", context="Utility Account"),
	]
