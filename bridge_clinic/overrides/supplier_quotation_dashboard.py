from frappe import _

def get_data(data=None, **kwargs):
	return {
		"fieldname": "supplier_quotation",
		"non_standard_fieldnames": {
			"Auto Repeat": "reference_document",
			"Material Request": "items.material_request",
			"Purchase Order": "ref_sq",
		},
		"internal_links": {
			"Material Request": ["items", "material_request"],
			"Purchase Order": ["ref_sq", "ref_sq"],
			"Request for Quotation": ["items", "request_for_quotation"],
			"Project": ["items", "project"],
		},
		"transactions": [
			{"label": _("Related"), "items": ["Purchase Order", "Quotation"]},
			{"label": _("Reference"), "items": ["Material Request", "Request for Quotation", "Project"]},
			{"label": _("Subscription"), "items": ["Auto Repeat"]},
		],
	}
