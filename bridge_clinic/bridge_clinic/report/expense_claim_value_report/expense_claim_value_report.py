# Copyright (c) 2025, Montego-Arch and contributors
# For license information, please see license.txt



# Copyright (c) 2025, Montego-Arch and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    if not filters:
        filters = {}

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    # Main query: Join Expense Claim → Expense Claim Detail → Expense Claim Type
    data = frappe.db.sql("""
        SELECT
            ec.employee_name AS requester_name,
            ec.name AS reference,
            ecd.expense_type AS expense_claim_type,
            ect.custom_expense_limit_amount AS limit_amount,
            CASE 
                WHEN ec.workflow_state IN ('Approved by Line Manager', 'Approved by HR', 'Approved by MD/COO', 'Paid') THEN 'Yes' 
                ELSE 'No' 
            END AS line_manager,
            CASE 
                WHEN ec.workflow_state IN ('Approved by HR', 'Approved by MD/COO', 'Paid') THEN 'Yes' 
                ELSE 'No' 
            END AS hr,
            CASE 
                WHEN ec.workflow_state IN ('Approved by MD/COO', 'Paid') THEN 'Yes' 
                ELSE 'No' 
            END AS md_coo
        FROM `tabExpense Claim` ec
        INNER JOIN `tabExpense Claim Detail` ecd ON ecd.parent = ec.name
        LEFT JOIN `tabExpense Claim Type` ect ON ecd.expense_type = ect.name
        WHERE ec.posting_date BETWEEN %(from_date)s AND %(to_date)s
        ORDER BY ec.posting_date ASC
    """, {"from_date": from_date, "to_date": to_date}, as_dict=True)

    # Compute totals for approved / paid / pending
    totals = frappe.db.sql("""
        SELECT
            SUM(CASE WHEN ec.workflow_state IN ('Approved by Line Manager', 'Approved by HR', 'Approved by MD/COO', 'Paid') 
                THEN ec.total_sanctioned_amount ELSE 0 END) AS total_approved,
            SUM(CASE WHEN ec.workflow_state = 'Paid' THEN ec.total_sanctioned_amount ELSE 0 END) AS total_paid,
            SUM(CASE WHEN ec.workflow_state = 'Pending HR' THEN ec.total_sanctioned_amount ELSE 0 END) AS total_pending_hr,
            SUM(CASE WHEN ec.workflow_state = 'Pending MD' THEN ec.total_sanctioned_amount ELSE 0 END) AS total_pending_md
        FROM `tabExpense Claim` ec
        WHERE ec.posting_date BETWEEN %(from_date)s AND %(to_date)s
    """, {"from_date": from_date, "to_date": to_date}, as_dict=True)[0]

    # Append totals at bottom
    if data:
        data.append({
            "requester_name": "TOTALS",
            "reference": "",
            "expense_claim_type": "",
            "limit_amount": "",
            "line_manager": "",
            "hr": "",
            "md_coo": "",
        })
        data.append({
            "requester_name": "",
            "reference": "",
            "expense_claim_type": "",
            "limit_amount": "",
            "line_manager": f"Total Approved: {totals.total_approved or 0:,.2f}",
            "hr": f"Total Paid: {totals.total_paid or 0:,.2f}",
            "md_coo": f"Pending MD/COO: {totals.total_pending_md or 0:,.2f}",
        })

    columns = [
        {"label": "Requester Name", "fieldname": "requester_name", "fieldtype": "Data", "width": 180},
        {"label": "Reference", "fieldname": "reference", "fieldtype": "Link", "options": "Expense Claim", "width": 150},
        {"label": "Expense Claim Type", "fieldname": "expense_claim_type", "fieldtype": "Data", "width": 200},
        {"label": "Limit", "fieldname": "limit_amount", "fieldtype": "Currency", "width": 150},
        {"label": "Line Manager", "fieldname": "line_manager", "fieldtype": "Data", "width": 100},
        {"label": "HR", "fieldname": "hr", "fieldtype": "Data", "width": 100},
        {"label": "MD/COO", "fieldname": "md_coo", "fieldtype": "Data", "width": 100},
    ]

    return columns, data
