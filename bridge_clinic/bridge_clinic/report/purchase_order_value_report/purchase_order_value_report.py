# Copyright (c) 2025, Montego-Arch and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    if not filters:
        filters = {}

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    columns = get_columns()
    data = get_data(from_date, to_date)

    return columns, data


def get_columns():
    return [
        {"label": "PO ID", "fieldname": "po_id", "fieldtype": "Link", "options": "Purchase Order", "width": 150},
        {"label": "Cost Centre", "fieldname": "cost_center", "fieldtype": "Link", "options": "Cost Center", "width": 180},
        {"label": "Item Group", "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 150},
        {"label": "Supplier Group", "fieldname": "supplier_group", "fieldtype": "Link", "options": "Supplier Group", "width": 150},
        {"label": "Supplier Name", "fieldname": "supplier_name", "fieldtype": "Link", "options": "Supplier", "width": 180},
        {"label": "Head of Finance", "fieldname": "head_of_finance", "fieldtype": "Data", "width": 120},
        {"label": "Auditor", "fieldname": "auditor", "fieldtype": "Data", "width": 100},
        {"label": "MD/COO", "fieldname": "md_coo", "fieldtype": "Data", "width": 100},
        {"label": "Total Value", "fieldname": "total_value", "fieldtype": "Currency", "width": 150},
    ]


def get_data(from_date, to_date):
    if not from_date or not to_date:
        frappe.throw("Please select From Date and To Date")

    query = """
        (
            SELECT
                po.name AS po_id,
                poi.cost_center AS cost_center,
                i.item_group AS item_group,
                s.supplier_group AS supplier_group,
                po.supplier_name AS supplier_name,

                CASE 
                    WHEN po.workflow_state IN ('Pending Head of Finance Approval', 'Approved by Head of Finance', 'Paid', 'Received') 
                    THEN 'Yes' ELSE 'No'
                END AS head_of_finance,

                CASE 
                    WHEN po.workflow_state IN ('Pending Auditor Approval', 'Approved by Auditor', 'Paid', 'Received') 
                    THEN 'Yes' ELSE 'No'
                END AS auditor,

                CASE 
                    WHEN po.workflow_state IN ('Pending COO Approval', 'Pending MD Approval', 'Approved', 'Paid', 'Received') 
                    THEN 'Yes' ELSE 'No'
                END AS md_coo,

                po.total AS total_value

            FROM `tabPurchase Order` po
            LEFT JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
            LEFT JOIN `tabItem` i ON poi.item_code = i.name
            LEFT JOIN `tabSupplier` s ON po.supplier = s.name

            WHERE po.transaction_date BETWEEN %(from_date)s AND %(to_date)s
        )
        UNION ALL
        (
            SELECT
                'TOTAL' AS po_id,
                '' AS cost_center,
                '' AS item_group,
                '' AS supplier_group,
                '' AS supplier_name,
                '' AS head_of_finance,
                '' AS auditor,
                '' AS md_coo,
                SUM(po.grand_total) AS total_value
            FROM `tabPurchase Order` po
            WHERE po.transaction_date BETWEEN %(from_date)s AND %(to_date)s
        )
        ORDER BY 
            CASE WHEN po_id = 'TOTAL' THEN 1 ELSE 0 END, 
            po_id
    """

    return frappe.db.sql(query, {"from_date": from_date, "to_date": to_date}, as_dict=True)
