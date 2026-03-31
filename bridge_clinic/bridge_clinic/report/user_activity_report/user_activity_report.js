// Copyright (c) 2026, Montego-Arch and contributors
// For license information, please see license.txt
frappe.query_reports["User Activity Report"] = {
    filters: [
        {
            fieldname: "user",
            label: __("User"),
            fieldtype: "Link",
            options: "User",
            reqd: 0,
            width: "200px",
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_days(frappe.datetime.nowdate(), -7),
            reqd: 1,
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.nowdate(),
            reqd: 1,
        },
        {
            fieldname: "ref_doctype",
            label: __("Document Type"),
            fieldtype: "Link",
            options: "DocType",
        },
    ],

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data, default_formatter);

        if (column.fieldname === "action") {
            const color_map = {
                Submit: "green",
                Cancel: "red",
                Amend: "orange",
                Edit: "blue",
            };
            const color = color_map[data.action] || "gray";
            if (data.action) {
                value = `<span class="indicator-pill ${color}">${data.action}</span>`;
            }
        }

        return value;
    },
};