frappe.query_reports["Unit Availability"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
		{ fieldname: "property", label: __("Property"), fieldtype: "Link", options: "Property" },
		{ fieldname: "available_by", label: __("Available By"), fieldtype: "Date" },
		{ fieldname: "unit_type", label: __("Unit Type"), fieldtype: "Select", options: "\nStudio\n1BR\n2BR\n3BR\n4BR+\nPenthouse\nShop\nOffice\nWarehouse" },
	],
};
