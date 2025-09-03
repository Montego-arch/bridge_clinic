import frappe
from frappe.utils import nowdate

def create_payment_request_for_expense(doc, method):
    """
    When an Expense Claim is submitted, create a draft Payment Request.
    """
    try:
        # Check if one already exists
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
        pr.mode_of_payment = "Bank"   # Change if you want different default
        pr.currency = doc.currency
        pr.grand_total = doc.total_sanctioned_amount
        pr.status = "Draft"
        pr.insert(ignore_permissions=True)

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Expense Claim Payment Request Creation Failed")
        raise




def notify_expense_payment_made(doc, method):
    """
    When a Payment Entry is submitted, check if it is linked to an Expense Claim.
    If yes, notify the employee that payment has been made.
    """
    try:
        for ref in doc.references:
            if ref.reference_doctype == "Expense Claim":
                exp_claim = frappe.get_doc("Expense Claim", ref.reference_name)
                employee = frappe.get_doc("Employee", exp_claim.employee)

                if employee.user_id:  # Employee linked to a system user
                    frappe.sendmail(
                        recipients=[employee.user_id],
                        subject="Expense Claim Payment Processed",
                        message=f"""
                        Dear {employee.employee_name},<br><br>
                        Your expense claim <b>{exp_claim.name}</b> 
                        has been paid with Payment Entry <b>{doc.name}</b>.<br><br>
                        Amount: {doc.paid_amount} {doc.paid_from_account_currency}<br><br>
                        Regards,<br>
                        Accounts Team
                        """
                    )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Expense Claim Payment Notification Failed")
