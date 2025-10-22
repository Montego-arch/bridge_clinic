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
            pr.name AS "pr_id",
            pr.transaction_date AS "pr_date",
            pr.party_type AS "party_type",
            pr.party AS "party_name",
            CONCAT_WS(' / ', pr.bank, pr.bank_account_no) AS "bank_info",
            pr.grand_total AS "amount",
            CASE 
                WHEN pr.status = 'Paid' THEN 'Paid'
                ELSE 'Not Paid'
            END AS "status"
        FROM `tabPayment Request` pr
        WHERE pr.transaction_date BETWEEN %(from_date)s AND %(to_date)s
        ORDER BY pr.transaction_date ASC
    """, {"from_date": from_date, "to_date": to_date}, as_dict=True)

    # --- Safely calculate totals ---
    total_paid = sum(d.get("amount", 0) for d in data if d.get("status") == "Paid")
    total_unpaid = sum(d.get("amount", 0) for d in data if d.get("status") == "Not Paid")

    # --- Append a blank separator row ---
    if data:
        data.append({
            "pr_id": "",
            "pr_date": "",
            "party_type": "",
            "party_name": "",
            "bank_info": "",
            "amount": "",
            "status": ""
        })
        # --- Append totals row ---
        data.append({
            "pr_id": "",
            "pr_date": "",
            "party_type": "",
            "party_name": "",
            "bank_info": "TOTALS",
            "amount": total_paid + total_unpaid,
            "status": ""
        })
        data.append({
            "pr_id": "",
            "pr_date": "",
            "party_type": "",
            "party_name": "",
            "bank_info": f"Paid Total",
            "amount": total_paid,
            "status": "Paid"
        })
        data.append({
            "pr_id": "",
            "pr_date": "",
            "party_type": "",
            "party_name": "",
            "bank_info": f"Unpaid Total",
            "amount": total_unpaid,
            "status": "Not Paid"
        })

    columns = [
        {"label": "PR ID", "fieldname": "pr_id", "fieldtype": "Link", "options": "Payment Request", "width": 150},
        {"label": "PR Date", "fieldname": "pr_date", "fieldtype": "Date", "width": 120},
        {"label": "Party Type", "fieldname": "party_type", "fieldtype": "Data", "width": 120},
        {"label": "Party Name", "fieldname": "party_name", "fieldtype": "Data", "width": 200},
        {"label": "Bank Name/Account", "fieldname": "bank_info", "fieldtype": "Data", "width": 200},
        {"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 150},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
    ]

    return columns, data
