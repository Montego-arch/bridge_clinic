import frappe
from frappe.utils import get_url, now_datetime
from datetime import timedelta


DEFAULT_ESCALATION_EMAILS = [
    "ithelpdesk@thebridgeclinic.com",
    "financehelpdesk@thebridgeclinic.com",
]

# Utility to get all user emails for a given role
def get_emails_by_role(role):
    users = frappe.get_all(
        "Has Role",
        filters={"role": role},
        fields=["parent"],
    )
    emails = []
    for u in users:
        email = frappe.db.get_value("User", u.parent, "email")
        if email and email not in emails:
            emails.append(email)
    return emails


def send_email(recipients, subject, message):
    """Wrapper for Frappe email send"""
    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message,
    )


def get_requester_email(reference_name):
    """Fetch requester email based on linked document"""
    if not reference_name:
        return None
    requester = frappe.db.get_value("Material Request", reference_name, "owner")
    return frappe.db.get_value("User", requester, "email") if requester else None


# -------------------------
# Notification Functions
# -------------------------

def notify_on_rfq_submit(doc, method):
    requester_email = get_requester_email(doc.material_request)
    admin_emails = get_emails_by_role("Admin Officer")

    subject = f"Request for Quotation {doc.name} Submitted"
    message = f"""
        <p>RFQ <b>{doc.name}</b> has been submitted for Material Request <b>{doc.material_request}</b>.</p>
        <p><a href='{get_url(doc.get_url())}'>View RFQ</a></p>
    """

    recipients = (admin_emails or []) + ([requester_email] if requester_email else [])
    send_email(recipients, subject, message)


def notify_on_sq_creation(doc, method):
    requester_email = get_requester_email(doc.material_request)
    admin_emails = get_emails_by_role("Admin Officer")

    subject = f"Supplier Quotation {doc.name} Created"
    message = f"""
        <p>Supplier Quotation <b>{doc.name}</b> has been created for Material Request <b>{doc.material_request}</b>.</p>
    """

    recipients = (admin_emails or []) + ([requester_email] if requester_email else [])
    send_email(recipients, subject, message)


def notify_on_sq_submit(doc, method):
    business_manager_emails = get_emails_by_role("Business Manager")

    subject = f"Supplier Quotation {doc.name} Submitted for Approval"
    message = f"""
        <p>Supplier Quotation <b>{doc.name}</b> has been submitted for your review.</p>
    """

    send_email(business_manager_emails, subject, message)


def notify_on_payment_request_creation(doc, method):
    requester_email = get_requester_email(doc.reference_name)
    accounts_emails = get_emails_by_role("Accounts User")

    subject = f"Payment Request {doc.name} Created"
    message = f"""
        <p>Payment Request <b>{doc.name}</b> has been created for Purchase Order <b>{doc.reference_name}</b>.</p>
    """

    recipients = (accounts_emails or []) + ([requester_email] if requester_email else [])
    send_email(recipients, subject, message)


def notify_on_po_creation(doc, method):
    requester_email = get_requester_email(doc.ref_sq)
    accounts_emails = get_emails_by_role("Accounts User")

    subject = f"Purchase Order {doc.name} Created"
    message = f"""
        <p>Purchase Order <b>{doc.name}</b> has been created from Supplier Quotation <b>{doc.ref_sq}</b>.</p>
    """

    recipients = (accounts_emails or []) + ([requester_email] if requester_email else [])
    send_email(recipients, subject, message)


def notify_on_mr_submit(doc, method):
    requester_email = doc.owner
    line_manager_email = frappe.db.get_value("Employee", {"user_id": requester_email}, "reports_to")

    subject = f"Material Request {doc.name} Submitted"
    message = f"""
        <p>Dear {frappe.utils.get_fullname(requester_email)},</p>
        <p>Your Material Request <b>{doc.name}</b> has been submitted.</p>
        <p><a href='{get_url(doc.get_url())}'>View Request</a></p>
    """

    send_email([requester_email, line_manager_email], subject, message)


def notify_on_mr_approval(doc, method):
    requester_email = doc.owner

    subject = f"Material Request {doc.name} Approved"
    message = f"""
        <p>Your Material Request <b>{doc.name}</b> has been approved by your line manager.</p>
        <p><a href='{get_url(doc.get_url())}'>View Request</a></p>
    """

    send_email([requester_email], subject, message)




def notify_on_sq_approval(doc, method):
    requester_email = get_requester_email(doc.material_request)

    subject = f"Supplier Quotation {doc.name} Approved"
    message = f"""
        <p>Your Supplier Quotation <b>{doc.name}</b> has been approved by the Business Manager.</p>
    """

    send_email([requester_email], subject, message)



def notify_on_po_approval(doc, method):
    next_approver = frappe.db.get_value("Workflow Action", {"reference_name": doc.name, "status": "Pending"}, "user")
    requester_email = get_requester_email(doc.ref_sq)

    subject = f"Purchase Order {doc.name} Approved and Forwarded"
    message = f"""
        <p>Purchase Order <b>{doc.name}</b> has been approved and sent to the next approver.</p>
    """

    send_email([requester_email, next_approver], subject, message)




def escalate_stuck_approvals():
    cutoff = now_datetime() - timedelta(days=3)
    stuck_actions = frappe.get_all("Workflow Action",
        filters={"status": "Pending", "modified": ("<", cutoff)},
        fields=["reference_doctype", "reference_name", "user"]
    )

    for action in stuck_actions:
        doc_url = get_url(f"/app/{frappe.scrub(action.reference_doctype)}/{action.reference_name}")
        requester = frappe.db.get_value("Material Request", {"name": action.reference_name}, "owner")

        recipients = DEFAULT_ESCALATION_EMAILS + [requester]
        subject = f"⚠️ Approval Pending for {action.reference_doctype} {action.reference_name}"
        message = f"""
            <p>The document <b>{action.reference_doctype} {action.reference_name}</b> has been pending approval for more than 3 days.</p>
            <p><a href='{doc_url}'>View Document</a></p>
        """

        send_email(recipients, subject, message)
