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
