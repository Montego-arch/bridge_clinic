import frappe
from frappe.utils import get_url, now_datetime
from datetime import timedelta
from frappe.utils import get_url
from typing import List, Optional

# ============================================
#  CONFIG
# ============================================

DEBUG_MODE = False  # set True to enable frappe.msgprint debugging

DEFAULT_ESCALATION_EMAILS = [
    "ithelpdesk@thebridgeclinic.com",
    "financehelpdesk@thebridgeclinic.com",
]

# ============================================
#  CORE UTILITIES
# ============================================

def get_emails_by_role(role: str) -> List[str]:
    """Return all distinct user emails for a given role."""
    users = frappe.get_all("Has Role", filters={"role": role}, fields=["parent"])
    emails = {
        frappe.db.get_value("User", u.parent, "email")
        for u in users if frappe.db.get_value("User", u.parent, "email")
    }
    return list(emails)


def send_email(recipients: List[str], subject: str, message: str):
    """Wrapper for Frappe email send."""
    if recipients:
        frappe.sendmail(recipients=recipients, subject=subject, message=message)


def debug_log(context: str, recipients: List[str], subject: str):
    """Log email context for debugging."""
    if DEBUG_MODE:
        frappe.msgprint(f"""
            <b>[DEBUG]</b><br>
            Context: {context}<br>
            Recipients: {', '.join(recipients) if recipients else 'None'}<br>
            Subject: {subject}
        """)


def get_requester_email_from_material_request(mr_name: str) -> Optional[str]:
    """Get requester email from Material Request."""
    if not mr_name:
        return None
    requester = frappe.db.get_value("Material Request", mr_name, "owner")
    return frappe.db.get_value("User", requester, "email") if requester else None


def get_requester_email_from_sq(sq_name: str) -> Optional[str]:
    """Get requester email via Supplier Quotation → Material Request."""
    if not sq_name:
        return None
    mr = frappe.db.get_value("Supplier Quotation Item", {"parent": sq_name}, "material_request")
    return get_requester_email_from_material_request(mr) if mr else None


def get_linked_material_request(doc) -> Optional[str]:
    """Find a linked Material Request from a document's child items."""
    if hasattr(doc, "items"):
        for item in doc.items:
            if getattr(item, "material_request", None):
                return item.material_request
    return None


def get_next_workflow_approver(doctype: str, docname: str) -> Optional[str]:
    """Get next approver's user email for a given doc."""
    next_user = frappe.db.get_value(
        "Workflow Action", {"reference_name": docname, "status": "Pending"}, "user"
    )
    return frappe.db.get_value("User", next_user, "email") if next_user else None


# ============================================
#  RFQ NOTIFICATIONS
# ============================================

def notify_on_rfq_submit(doc, method):
    mr = get_linked_material_request(doc)
    requester_email = get_requester_email_from_material_request(mr)
    admin_emails = get_emails_by_role("Admin Officer")

    subject = f"RFQ {doc.name} Submitted"
    message = f"""
        <p>RFQ <b>{doc.name}</b> has been submitted{f' for Material Request <b>{mr}</b>' if mr else ''}.</p>
        <p><a href='{get_url(doc.get_url())}'>View RFQ</a></p>
    """

    recipients = [*admin_emails, requester_email]
    recipients = list(filter(None, recipients))
    debug_log("notify_on_rfq_submit", recipients, subject)
    send_email(recipients, subject, message)


# ============================================
#  SUPPLIER QUOTATION NOTIFICATIONS
# ============================================

def notify_on_sq_creation(doc, method):
    mr = get_linked_material_request(doc)
    requester_email = get_requester_email_from_material_request(mr)
    admin_emails = get_emails_by_role("Admin Officer")

    subject = f"Supplier Quotation {doc.name} Created"
    message = f"""
        <p>Supplier Quotation <b>{doc.name}</b> has been created{f' for Material Request <b>{mr}</b>' if mr else ''}.</p>
        <p><a href='{get_url(doc.get_url())}'>View Quotation</a></p>
    """

    recipients = [*admin_emails, requester_email]
    recipients = list(filter(None, recipients))
    debug_log("notify_on_sq_creation", recipients, subject)
    send_email(recipients, subject, message)


def notify_on_sq_submit(doc, method):
    approvers = get_emails_by_role("Business Manager")

    subject = f"Supplier Quotation {doc.name} Submitted for Approval"
    message = f"""
        <p>Supplier Quotation <b>{doc.name}</b> has been submitted for review.</p>
        <p><a href='{get_url(doc.get_url())}'>View Quotation</a></p>
    """

    debug_log("notify_on_sq_submit", approvers, subject)
    send_email(approvers, subject, message)


def notify_on_sq_approval(doc, method):
    mr = get_linked_material_request(doc)
    requester_email = get_requester_email_from_material_request(mr)

    subject = f"Supplier Quotation {doc.name} Approved"
    message = f"""
        <p>Your Supplier Quotation <b>{doc.name}</b> has been approved.</p>
        <p><a href='{get_url(doc.get_url())}'>View Quotation</a></p>
    """

    recipients = [requester_email]
    debug_log("notify_on_sq_approval", recipients, subject)
    send_email(recipients, subject, message)


# ============================================
#  PURCHASE ORDER NOTIFICATIONS
# ============================================

def notify_on_po_creation(doc, method):
    ref_sq = getattr(doc, "ref_sq", None)
    requester_email = get_requester_email_from_sq(ref_sq)
    accounts_emails = get_emails_by_role("Accounts User")

    subject = f"Purchase Order {doc.name} Created"
    message = f"""
        <p>Purchase Order <b>{doc.name}</b> has been created from Supplier Quotation <b>{ref_sq}</b>.</p>
        <p><a href='{get_url(doc.get_url())}'>View Purchase Order</a></p>
    """

    recipients = [*accounts_emails, requester_email]
    recipients = list(filter(None, recipients))
    debug_log("notify_on_po_creation", recipients, subject)
    send_email(recipients, subject, message)


def notify_on_po_approval(doc, method):
    next_approver_email = get_next_workflow_approver("Purchase Order", doc.name)
    ref_sq = getattr(doc, "ref_sq", None)
    requester_email = get_requester_email_from_sq(ref_sq)

    subject = f"Purchase Order {doc.name} Approval Update"
    message = f"""
        <p>Purchase Order <b>{doc.name}</b> has been approved and forwarded to the next approver.</p>
        <p><a href='{get_url(doc.get_url())}'>View Purchase Order</a></p>
    """

    recipients = list(filter(None, [requester_email, next_approver_email]))
    debug_log("notify_on_po_approval", recipients, subject)
    send_email(recipients, subject, message)


# ============================================
#  PAYMENT REQUEST NOTIFICATIONS
# ============================================

def notify_on_payment_request_creation(doc, method):
    requester_email = get_requester_email_from_material_request(doc.reference_name)
    accounts_emails = get_emails_by_role("Accounts User")

    subject = f"Payment Request {doc.name} Created"
    message = f"""
        <p>Payment Request <b>{doc.name}</b> has been created for Purchase Order <b>{doc.reference_name}</b>.</p>
        <p><a href='{get_url(doc.get_url())}'>View Payment Request</a></p>
    """

    recipients = [*accounts_emails, requester_email]
    recipients = list(filter(None, recipients))
    debug_log("notify_on_payment_request_creation", recipients, subject)
    send_email(recipients, subject, message)


def notify_on_payment_request_approval(doc, method):
    next_approver_email = get_next_workflow_approver("Payment Request", doc.name)
    requester_email = get_requester_email_from_material_request(doc.reference_name)

    subject = f"Payment Request {doc.name} Approval Update"
    message = f"""
        <p>Payment Request <b>{doc.name}</b> has been approved and forwarded to the next approver.</p>
        <p><a href='{get_url(doc.get_url())}'>View Payment Request</a></p>
    """

    recipients = list(filter(None, [requester_email, next_approver_email]))
    debug_log("notify_on_payment_request_approval", recipients, subject)
    send_email(recipients, subject, message)


# ============================================
#  MATERIAL REQUEST NOTIFICATIONS
# ============================================

def notify_on_mr_submit(doc, method):
    requester_email = frappe.db.get_value("User", doc.owner, "email")
    line_manager_user = frappe.db.get_value("Employee", {"user_id": doc.owner}, "reports_to")
    line_manager_email = frappe.db.get_value("User", line_manager_user, "email") if line_manager_user else None

    subject = f"Material Request {doc.name} Submitted"
    message = f"""
        <p>Your Material Request <b>{doc.name}</b> has been submitted for approval.</p>
        <p><a href='{get_url(doc.get_url())}'>View Request</a></p>
    """

    recipients = list(filter(None, [requester_email, line_manager_email]))
    debug_log("notify_on_mr_submit", recipients, subject)
    send_email(recipients, subject, message)


def notify_on_mr_approval(doc, method):
    requester_email = frappe.db.get_value("User", doc.owner, "email")

    subject = f"Material Request {doc.name} Approved"
    message = f"""
        <p>Your Material Request <b>{doc.name}</b> has been approved.</p>
        <p><a href='{get_url(doc.get_url())}'>View Request</a></p>
    """

    recipients = [requester_email]
    debug_log("notify_on_mr_approval", recipients, subject)
    send_email(recipients, subject, message)



def escalate_stuck_approvals():
    """Escalate any Workflow Actions pending for more than 3 days."""
    cutoff = now_datetime() - timedelta(days=3)
    stuck_actions = frappe.get_all(
        "Workflow Action",
        filters={"status": "Pending", "modified": ("<", cutoff)},
        fields=["reference_doctype", "reference_name", "user"]
    )

    for action in stuck_actions:
        doc_url = get_url(f"/app/{frappe.scrub(action.reference_doctype)}/{action.reference_name}")
        requester_email = None

        # --- Identify requester based on document type ---
        if action.reference_doctype == "Material Request":
            requester = frappe.db.get_value("Material Request", action.reference_name, "owner")
            requester_email = frappe.db.get_value("User", requester, "email") if requester else None

        elif action.reference_doctype == "Supplier Quotation":
            mr = frappe.db.get_value("Supplier Quotation Item", {"parent": action.reference_name}, "material_request")
            if mr:
                requester = frappe.db.get_value("Material Request", mr, "owner")
                requester_email = frappe.db.get_value("User", requester, "email") if requester else None

        elif action.reference_doctype == "Purchase Order":
            ref_sq = frappe.db.get_value("Purchase Order", action.reference_name, "ref_sq")
            requester_email = get_requester_email_from_sq(ref_sq)

        elif action.reference_doctype == "Payment Request":
            ref_po = frappe.db.get_value("Payment Request", action.reference_name, "reference_name")
            if ref_po:
                ref_sq = frappe.db.get_value("Purchase Order", ref_po, "ref_sq")
                requester_email = get_requester_email_from_sq(ref_sq)

        # --- Fallback: if no requester found ---
        if not requester_email:
            requester_email = frappe.db.get_value("User", action.user, "email")

        # --- Compose and send email ---
        recipients = list(filter(None, DEFAULT_ESCALATION_EMAILS + [requester_email]))
        subject = f"⚠️ Approval Pending for {action.reference_doctype} {action.reference_name}"
        message = f"""
            <p>The document <b>{action.reference_doctype} {action.reference_name}</b> has been pending approval for more than 3 days.</p>
            <p><a href='{doc_url}'>View Document</a></p>
        """

        debug_log("escalate_stuck_approvals", recipients, subject)
        if recipients:
            send_email(recipients, subject, message)
