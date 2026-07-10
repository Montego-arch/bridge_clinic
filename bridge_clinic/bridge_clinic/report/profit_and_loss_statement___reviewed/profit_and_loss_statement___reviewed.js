// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Profit and Loss Statement - Reviewed"] = $.extend(
	{},
	erpnext.financial_statements
);

erpnext.utils.add_dimensions("Profit and Loss Statement - Reviewed", 10);

frappe.query_reports["Profit and Loss Statement - Reviewed"]["filters"].push({
	fieldname: "accumulated_values",
	label: __("Accumulated Values"),
	fieldtype: "Check",
	default: 1,
});

frappe.query_reports["Profit and Loss Statement - Reviewed"]["filters"].push({
    "fieldname": "show_cost_centers_in_columns",
    "label": __("Show Cost Centers in Columns"),
    "fieldtype": "Check",
    "default": 0
});

frappe.query_reports["Profit and Loss Statement - Reviewed"]["filters"].push({
	"fieldname": "allocate_costs",
	"label": __("Allocate Shared Costs"),
	"fieldtype": "Check",
	"default": 0,
	"depends_on": "eval:doc.show_cost_centers_in_columns == 1"
});

frappe.query_reports["Profit and Loss Statement - Reviewed"]["filters"].push({
	"fieldname": "allocation_source_cost_center",
	"label": __("Allocation Source Cost Center"),
	"fieldtype": "Link",
	"options": "Cost Center",
	"depends_on": "eval:doc.allocate_costs",
	get_query: function () {
		return {
			filters: {
				company: frappe.query_report.get_filter_value("company")
			}
		};
	}
})