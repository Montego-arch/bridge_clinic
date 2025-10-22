# Copyright (c) 2025, Montego-Arch and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    if not filters:
        filters = {}

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    data = frappe.db.sql("""
        SELECT
            ec.employee_name AS "Requester Name:Data:180",
            ec.name AS "Reference:Link/Expense Claim:150",
            ec.expense_type AS "Expense Claim Type:Data:200",
            ec.total_sanctioned_amount AS "Limit:Currency:150",
            CASE WHEN ec.workflow_state IN ('Approved by Line Manager', 'Approved by HR', 'Approved by MD/COO', 'Paid')
                THEN 'Yes' ELSE 'No' END AS "Line Manager:Data:100",
            CASE WHEN ec.workflow_state IN ('Approved by HR', 'Approved by MD/COO', 'Paid')
                THEN 'Yes' ELSE 'No' END AS "HR:Data:100",
            CASE WHEN ec.workflow_state IN ('Approved by MD/COO', 'Paid')
                THEN 'Yes' ELSE 'No' END AS "MD/COO:Data:100"
        FROM `tabExpense Claim` ec
        WHERE ec.posting_date BETWEEN %(from_date)s AND %(to_date)s
        ORDER BY ec.posting_date ASC
    """, {"from_date": from_date, "to_date": to_date}, as_dict=True)

    # Calculate totals
    totals = frappe.db.sql("""
        SELECT
            SUM(CASE WHEN ec.workflow_state IN ('Approved', 'Paid') THEN ec.total_sanctioned_amount ELSE 0 END) AS total_approved,
            SUM(CASE WHEN ec.workflow_state = 'Paid' THEN ec.total_sanctioned_amount ELSE 0 END) AS total_paid,
            SUM(CASE WHEN ec.workflow_state = 'Pending HR' THEN ec.total_sanctioned_amount ELSE 0 END) AS total_pending_hr,
            SUM(CASE WHEN ec.workflow_state = 'Pending MD' THEN ec.total_sanctioned_amount ELSE 0 END) AS total_pending_md
        FROM `tabExpense Claim` ec
        WHERE ec.posting_date BETWEEN %(from_date)s AND %(to_date)s
    """, {"from_date": from_date, "to_date": to_date}, as_dict=True)[0]

    # Append totals row
    if data:
        data.append({
            "Requester Name": "TOTALS",
            "Reference": "",
            "Expense Claim Type": "",
            "Limit": "",
            "Line Manager": "",
            "HR": "",
            "MD/COO": "",
        })
        data.append({
            "Requester Name": "",
            "Reference": "",
            "Expense Claim Type": "",
            "Limit": "",
            "Line Manager": f"Total Approved: {totals.total_approved or 0:,.2f}",
            "HR": f"Total Paid: {totals.total_paid or 0:,.2f}",
            "MD/COO": f"Pending MD/COO: {totals.total_pending_md or 0:,.2f}",
        })

    columns = [
        {"label": "Requester Name", "fieldname": "Requester Name", "fieldtype": "Data", "width": 180},
        {"label": "Reference", "fieldname": "Reference", "fieldtype": "Link", "options": "Expense Claim", "width": 150},
        {"label": "Expense Claim Type", "fieldname": "Expense Claim Type", "fieldtype": "Data", "width": 200},
        {"label": "Limit", "fieldname": "Limit", "fieldtype": "Currency", "width": 150},
        {"label": "Line Manager", "fieldname": "Line Manager", "fieldtype": "Data", "width": 100},
        {"label": "HR", "fieldname": "HR", "fieldtype": "Data", "width": 100},
        {"label": "MD/COO", "fieldname": "MD/COO", "fieldtype": "Data", "width": 100},
    ]

    return columns, data
