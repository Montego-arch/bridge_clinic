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
            pr.name AS "PR ID:Link/Payment Request:150",
            pr.transaction_date AS "PR Date:Date:120",
            pr.party_type AS "Party Type:Data:120",
            pr.party AS "Party Name:Data:200",
            CONCAT_WS(' / ', pr.bank, pr.bank_account_no) AS "Bank Name/Account:Data:200",
            pr.grand_total AS "Amount:Currency:150",
            CASE 
                WHEN pr.status = 'Paid' THEN 'Paid'
                ELSE 'Not Paid'
            END AS "Status:Data:100"
        FROM `tabPayment Request` pr
        WHERE pr.transaction_date BETWEEN %(from_date)s AND %(to_date)s
        ORDER BY pr.transaction_date ASC
    """, {"from_date": from_date, "to_date": to_date}, as_dict=True)

    # Calculate totals
    total_paid = sum(d["Amount"] for d in data if d["Status"] == "Paid")
    total_unpaid = sum(d["Amount"] for d in data if d["Status"] == "Not Paid")

    # Add totals row
    if data:
        data.append({
            "PR ID": "",
            "PR Date": "",
            "Party Type": "",
            "Party Name": "",
            "Bank Name/Account": "TOTALS",
            "Amount": "",
            "Status": ""
        })
        data.append({
            "PR ID": "",
            "PR Date": "",
            "Party Type": "",
            "Party Name": "",
            "Bank Name/Account": f"Paid: {total_paid:,.2f}",
            "Amount": f"Not Paid: {total_unpaid:,.2f}",
            "Status": ""
        })

    columns = [
        {"label": "PR ID", "fieldname": "PR ID", "fieldtype": "Link", "options": "Payment Request", "width": 150},
        {"label": "PR Date", "fieldname": "PR Date", "fieldtype": "Date", "width": 120},
        {"label": "Party Type", "fieldname": "Party Type", "fieldtype": "Data", "width": 120},
        {"label": "Party Name", "fieldname": "Party Name", "fieldtype": "Data", "width": 200},
        {"label": "Bank Name/Account", "fieldname": "Bank Name/Account", "fieldtype": "Data", "width": 200},
        {"label": "Amount", "fieldname": "Amount", "fieldtype": "Currency", "width": 150},
        {"label": "Status", "fieldname": "Status", "fieldtype": "Data", "width": 100},
    ]

    return columns, data

