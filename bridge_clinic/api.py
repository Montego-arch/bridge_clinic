import frappe
from frappe.utils import nowdate


def create_payment_request_for_expense(doc, method):
    """
    When an Expense Claim is submitted, create a draft Payment Request.
    """
    try:
        # Avoid duplicates
        existing = frappe.db.exists("Payment Request", {
            "reference_doctype": "Expense Claim",
            "reference_name": doc.name
        })
        if existing:
            return

        pr = frappe.new_doc("Payment Request")
        pr.payment_request_type = "Outward"
        pr.reference_doctype = "Expense Claim"
        pr.reference_name = doc.name
        pr.party_type = "Employee"
        pr.party = doc.employee
        pr.transaction_date = nowdate()
        pr.company = doc.company
        # pr.currency = doc.currency or frappe.get_cached_value("Company", doc.company, "default_currency")
        pr.grand_total = doc.total_sanctioned_amount

        # optional but good practice
        if frappe.db.exists("Mode of Payment", "Bank"):
            pr.mode_of_payment = "Bank"

        pr.insert(ignore_permissions=True)

        frappe.msgprint(
            f"Payment Request <b>{0}</b> created successfully.",
            alert=True,
            indicator="green"
        )

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Expense Claim Payment Request Creation Failed")
        raise




def notify_expense_payment_made(doc, method):
    """
    When a Payment Entry is submitted, check if it is linked to an Expense Claim.
    If yes, notify the employee that payment has been made.
    """
    try:
        if not getattr(doc, "references", None):
            return

        for ref in doc.references:
            if ref.reference_doctype == "Expense Claim":
                exp_claim = frappe.get_doc("Expense Claim", ref.reference_name)
                employee = frappe.get_doc("Employee", exp_claim.employee)

                recipient = employee.user_id or employee.company_email
                if not recipient:
                    frappe.log_error(
                        f"No recipient (user_id or email) found for employee {employee.name}",
                        "Expense Claim Payment Notification Skipped"
                    )
                    continue

                subject = "Expense Claim Payment Processed"
                message = f"""
                    Dear {employee.employee_name},<br><br>
                    Your expense claim <b>{exp_claim.name}</b> 
                    has been paid with Payment Entry <b>{doc.name}</b>.<br><br>
                    <b>Amount:</b> {doc.paid_amount} {doc.paid_from_account_currency}<br><br>
                    Regards,<br>
                    Accounts Team
                """

                # Send Email
                frappe.sendmail(recipients=[recipient], subject=subject, message=message)

                # Send Desk Notification (if employee has system user)
                if employee.user_id:
                    frappe.publish_realtime(
                        event="msgprint",
                        message=f"Your expense claim {exp_claim.name} has been paid.",
                        user=employee.user_id,
                        doctype="Expense Claim",
                        docname=exp_claim.name,
                    )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Expense Claim Payment Notification Failed")



def create_rfq_from_material_request(doc, method):
    try:
        # avoid duplicates
        existing = frappe.db.exists("Request for Quotation", {
            "material_request": doc.name
        })
        if existing:
            return

        rfq = frappe.new_doc("Request for Quotation")
        rfq.transaction_date = nowdate()
        rfq.company = doc.company
        rfq.material_request = doc.name

        # copy MR items
        for item in doc.items:
            rfq.append("items", {
                "item_code": item.item_code,
                "qty": item.qty,
                "schedule_date": item.schedule_date or nowdate(),
                "material_request": doc.name,
                "material_request_item": item.name,
                "warehouse": item.warehouse,
                "conversion_factor": item.conversion_factor,
            })

        rfq.insert(ignore_permissions=True)

        frappe.msgprint(
            ("Request for Quotation <b>{0}</b> created successfully.").format(rfq.name),
            alert=True,
            indicator="green"
        )

        # doc.add_comment("Info", ("RFQ {0} created from this Material Request.").format(rfq.name))

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Failed to create RFQ from MR")
        raise


def create_po_from_rfq(doc, method):
    try:
        existing = frappe.db.exists("Purchase Order", {
            "custom_linked_rfq": doc.name  # ✅ use custom field
        })
        if existing:
            return

        po = frappe.new_doc("Purchase Order")
        po.company = doc.company
        po.transaction_date = nowdate()
        po.custom_linked_rfq = doc.name   # ✅ store RFQ link
        po.supplier = doc.suppliers[0].supplier if doc.suppliers else None

        for item in doc.items:
            po.append("items", {
                "item_code": item.item_code,
                "qty": item.qty,
                "schedule_date": item.schedule_date or nowdate(),
                "warehouse": item.warehouse,
                "conversion_factor": item.conversion_factor,
            })

        po.insert(ignore_permissions=True)

        frappe.msgprint(
            ("Purchase Order <b>{0}</b> created successfully.").format(po.name),
            alert=True,
            indicator="green"
        )

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Failed to create PO from RFQ")
        raise




def create_pi_from_pr(doc, method):
    """
    On submission of Purchase Receipt, generate a draft Purchase Invoice.
    """
    try:
        # Avoid duplicates
        existing = frappe.db.exists("Purchase Invoice", {"purchase_receipt": doc.name})
        if existing:
            return

        pi = frappe.new_doc("Purchase Invoice")
        pi.supplier = doc.supplier
        pi.company = doc.company
        pi.posting_date = nowdate()
        pi.purchase_receipt = doc.name

        for item in doc.items:
            pi.append("items", {
                "item_code": item.item_code,
                "qty": item.qty,
                "rate": item.rate,
                "amount": item.amount,
                "purchase_receipt": doc.name
            })

        pi.insert(ignore_permissions=True)

        frappe.msgprint(
            ("Purchase Invoice <b>{0}</b> created successfully.").format(pi.name),
            alert=True,
            indicator="green"
        )

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Failed to create PI from PR")
        raise




def create_payment_request_from_pi(doc, method):
    """
    On submission of Purchase Invoice, create a Payment Request in Draft
    only if no Paid Payment Request already exists.
    """
    try:
        # Check for existing PR linked to this PI
        pr_list = frappe.get_all(
            "Payment Request",
            filters={"reference_doctype": "Purchase Invoice", "reference_name": doc.name},
            fields=["name", "status"]
        )

        # If any PR is already Paid → stop
        if any(pr.status == "Paid" for pr in pr_list):
            return

        # If unpaid PR already exists → stop
        if any(pr.status in ("Initiated", "Draft", "Unpaid") for pr in pr_list):
            return

        pr = frappe.new_doc("Payment Request")
        pr.payment_request_type = "Outward"
        pr.reference_doctype = "Purchase Invoice"
        pr.reference_name = doc.name
        pr.party_type = "Supplier"
        pr.party = doc.supplier
        pr.transaction_date = nowdate()
        pr.grand_total = doc.grand_total
        pr.status = "Draft"

        if frappe.db.exists("Mode of Payment", "Bank"):
            pr.mode_of_payment = "Bank"

        pr.insert(ignore_permissions=True)

        frappe.msgprint(
            ("Payment Request <b>{0}</b> created successfully.").format(pr.name),
            alert=True,
            indicator="green"
        )

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Failed to create PR from PI")
        raise
