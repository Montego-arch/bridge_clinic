# Copyright (c) 2026, Montego-Arch and contributors
# For license information, please see license.txt

import frappe
import json
from frappe import _
from frappe.utils import getdate, nowdate


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": _("Timestamp"),
            "fieldname": "creation",
            "fieldtype": "Datetime",
            "width": 165,
        },
        {
            "label": _("User"),
            "fieldname": "owner",
            "fieldtype": "Link",
            "options": "User",
            "width": 200,
        },
        {
            "label": _("Full Name"),
            "fieldname": "full_name",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": _("Document Type"),
            "fieldname": "ref_doctype",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": _("Document"),
            "fieldname": "docname",
            "fieldtype": "Dynamic Link",
            "options": "ref_doctype",
            "width": 180,
        },
        {
            "label": _("Action"),
            "fieldname": "action",
            "fieldtype": "Data",
            "width": 110,
        },
        {
            "label": _("Summary"),
            "fieldname": "summary",
            "fieldtype": "Data",
            "width": 380,
        },
    ]


def get_data(filters):
    conditions, values = build_conditions(filters)

    rows = frappe.db.sql(
        """
        SELECT
            v.name,
            v.creation,
            v.owner,
            COALESCE(u.full_name, v.owner) AS full_name,
            v.ref_doctype,
            v.docname,
            v.data
        FROM
            `tabVersion` v
        LEFT JOIN
            `tabUser` u ON u.name = v.owner
        WHERE
            {conditions}
        ORDER BY
            v.creation DESC
        LIMIT 5000
        """.format(conditions=conditions),
        values,
        as_dict=True,
    )

    result = []
    for row in rows:
        action, summary = parse_version_data(row.get("data"))
        result.append(
            {
                "creation": row["creation"],
                "owner": row["owner"],
                "full_name": row["full_name"],
                "ref_doctype": row["ref_doctype"],
                "docname": row["docname"],
                "action": action,
                "summary": summary,
            }
        )

    return result


def build_conditions(filters):
    conditions = ["1 = 1"]
    values = {}

    # --- User filter ---
    if filters.get("user"):
        conditions.append("v.owner = %(user)s")
        values["user"] = filters["user"]

    # --- Date range ---
    from_date = filters.get("from_date") or getdate(nowdate())
    to_date = filters.get("to_date") or getdate(nowdate())
    conditions.append("DATE(v.creation) BETWEEN %(from_date)s AND %(to_date)s")
    values["from_date"] = from_date
    values["to_date"] = to_date

    # --- Document Type filter ---
    if filters.get("ref_doctype"):
        conditions.append("v.ref_doctype = %(ref_doctype)s")
        values["ref_doctype"] = filters["ref_doctype"]

    return " AND ".join(conditions), values


def parse_version_data(data_str):
    """
    Parse the Version.data JSON and return a human-readable
    (action, summary) tuple.

    Version data structure:
    {
        "changed":     [[fieldname, old_val, new_val], ...],
        "added":       [[childtable, {row_dict}], ...],
        "removed":     [[childtable, {row_dict}], ...],
        "row_changed": [[childtable, row_name, row_idx, [[field, old, new], ...]], ...]
    }
    """
    if not data_str:
        return "Edit", ""

    try:
        data = json.loads(data_str)
    except (ValueError, TypeError):
        return "Edit", ""

    parts = []
    action = "Edit"

    # --- Field-level changes ---
    changed = data.get("changed") or []
    if changed:
        # Check for docstatus change to determine the real action
        for field, old_val, new_val in changed:
            if field == "docstatus":
                if str(new_val) == "1":
                    action = "Submit"
                elif str(new_val) == "2":
                    action = "Cancel"
                elif str(new_val) == "0" and str(old_val) in ("1", "2"):
                    action = "Amend"

        field_names = [f[0] for f in changed if f[0] != "docstatus"]
        if field_names:
            parts.append("Changed: " + ", ".join(field_names))

    # --- Rows added ---
    added = data.get("added") or []
    if added:
        tables = {}
        for entry in added:
            table = entry[0] if isinstance(entry, (list, tuple)) else entry
            tables[table] = tables.get(table, 0) + 1
        parts.append(
            "Added rows: "
            + ", ".join("{} ({})".format(t, n) for t, n in tables.items())
        )

    # --- Rows removed ---
    removed = data.get("removed") or []
    if removed:
        tables = {}
        for entry in removed:
            table = entry[0] if isinstance(entry, (list, tuple)) else entry
            tables[table] = tables.get(table, 0) + 1
        parts.append(
            "Removed rows: "
            + ", ".join("{} ({})".format(t, n) for t, n in tables.items())
        )

    # --- Child row field changes ---
    row_changed = data.get("row_changed") or []
    if row_changed:
        tables = {}
        for entry in row_changed:
            table = entry[0] if isinstance(entry, (list, tuple)) else entry
            tables[table] = tables.get(table, 0) + 1
        parts.append(
            "Row edits: "
            + ", ".join("{} ({})".format(t, n) for t, n in tables.items())
        )

    return action, " | ".join(parts)
