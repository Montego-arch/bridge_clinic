import frappe
from frappe.utils import get_url, now_datetime, getdate, fmt_money
from datetime import timedelta
from typing import List, Optional

DEBUG_MODE = False
DEFAULT_ESCALATION_EMAILS = ["ithelpdesk@thebridgeclinic.com", "financehelpdesk@thebridgeclinic.com"]

# ============================================
#  CORE UTILITIES
# ============================================

EXCLUDED_EMAILS = ["pamajayi101@gmail.com"]

def get_emails_by_role(role: str) -> List[str]:
    users = frappe.get_all("Has Role", filters={"role": role}, fields=["parent"])
    emails = {frappe.db.get_value("User", u.parent, "email") for u in users if frappe.db.get_value("User", u.parent, "email")}
    return [e for e in emails if e and e.lower() not in [x.lower() for x in EXCLUDED_EMAILS]]

def send_email(recipients: List[str], subject: str, message: str):
    recipients = [r for r in recipients if r and r.lower() not in [x.lower() for x in EXCLUDED_EMAILS]]
    if recipients:
        frappe.sendmail(recipients=recipients, subject=subject, message=message)

def debug_log(context: str, recipients: List[str], subject: str):
    if DEBUG_MODE:
        frappe.msgprint(f"<b>[DEBUG]</b><br>Context: {context}<br>Recipients: {', '.join(recipients) if recipients else 'None'}<br>Subject: {subject}")

def get_doc_link(doctype: str, name: str) -> str:
    return get_url(f"/app/{frappe.scrub(doctype)}/{name}")

def get_requester_info(user: str) -> dict:
    if not user:
        return {"email": None, "name": "Unknown"}
    email = frappe.db.get_value("User", user, "email")
    full_name = frappe.db.get_value("User", user, "full_name") or user
    return {"email": email, "name": full_name}

def get_line_manager_info(user: str) -> dict:
    if not user:
        return {"email": None, "name": None}
    emp = frappe.db.get_value("Employee", {"user_id": user}, ["reports_to", "name"], as_dict=True)
    if emp and emp.reports_to:
        mgr = frappe.db.get_value("Employee", emp.reports_to, ["user_id", "employee_name"], as_dict=True)
        if mgr and mgr.user_id:
            return {"email": frappe.db.get_value("User", mgr.user_id, "email"), "name": mgr.employee_name}
    return {"email": None, "name": None}

def get_approver_by_role(role: str) -> dict:
    emails = get_emails_by_role(role)
    return {"emails": emails, "name": role}

def get_linked_mr_from_items(doc) -> Optional[str]:
    if hasattr(doc, "items"):
        for item in doc.items:
            if getattr(item, "material_request", None):
                return item.material_request
    return None

def get_linked_rfq_from_sq(sq_name: str) -> Optional[str]:
    return frappe.db.get_value("Supplier Quotation Item", {"parent": sq_name}, "request_for_quotation")

def get_linked_sq_from_po(po_name: str) -> Optional[str]:
    return frappe.db.get_value("Purchase Order", po_name, "ref_sq")

def get_linked_po_from_pr(pr_doc) -> Optional[str]:
    """Get linked Purchase Order from Payment Request document."""
    if not pr_doc.reference_doctype or not pr_doc.reference_name:
        return None
    
    if pr_doc.reference_doctype == "Purchase Order":
        return pr_doc.reference_name
    
    if pr_doc.reference_doctype == "Purchase Invoice":
        # Purchase Invoice stores purchase_order in the ITEM child table, not at header level
        return frappe.db.get_value(
            "Purchase Invoice Item", 
            {"parent": pr_doc.reference_name}, 
            "purchase_order"
        )
    
    return None

# ============================================
#  HTML EMAIL BUILDER
# ============================================

def build_email_table(rows: List[tuple]) -> str:
    table_rows = "".join(f"<tr><td style='padding:8px 12px;border:1px solid #ddd;background:#f9f9f9;font-weight:bold;width:180px;'>{label}</td><td style='padding:8px 12px;border:1px solid #ddd;'>{value}</td></tr>" for label, value in rows if value)
    return f"<table style='border-collapse:collapse;width:100%;max-width:600px;font-family:Arial,sans-serif;font-size:14px;'>{table_rows}</table>"

def build_email_body(greeting: str, intro: str, table_rows: List[tuple], action_text: str = None, closing: str = "Thank you.") -> str:
    table = build_email_table(table_rows)
    action = f"<p style='margin-top:15px;'>{action_text}</p>" if action_text else ""
    return f"<div style='font-family:Arial,sans-serif;font-size:14px;color:#333;'><p>{greeting},</p><p>{intro}</p>{table}{action}<p style='margin-top:20px;'>{closing}</p></div>"

# ============================================
#  MATERIAL REQUEST NOTIFICATIONS
# ============================================

def get_cost_center_from_items(doc) -> str:
    if hasattr(doc, "items") and doc.items:
        return getattr(doc.items[0], "cost_center", None) or "N/A"
    return "N/A"

def notify_on_mr_submit(doc, method):
    requester = get_requester_info(doc.owner)
    line_mgr = get_line_manager_info(doc.owner)
    cost_center = get_cost_center_from_items(doc)
    
    rows = [
        ("MAT-ID", doc.name),
        ("Created By", requester["name"]),
        ("Created Date", str(getdate(doc.creation))),
        ("Cost Centre", cost_center),
        ("No of Items", str(len(doc.items))),
        ("Request Link", f"<a href='{get_doc_link('Material Request', doc.name)}'>{doc.name}</a>"),
        ("Description", doc.custom_description or "N/A"),
    ]
    
    # Email to Requester
    msg = build_email_body(f"Dear {requester['name']}", f"This is to notify you that a new Material Request has been created with the details below:", rows)
    send_email([requester["email"]], f"New Material Request {doc.name} Created", msg)
    
    # Email to Line Manager for approval
    if line_mgr["email"]:
        msg_mgr = build_email_body(f"Dear {line_mgr['name']}", f"This is to notify you that Material Request with the details below requires your approval:", rows, "Click on the link to the Request to approve on ERPNext.")
        send_email([line_mgr["email"]], f"Material Request {doc.name} Pending Line Manager Approval", msg_mgr)

def notify_on_mr_approval(doc, method):
    requester = get_requester_info(doc.owner)
    rows = [
        ("MAT-ID", doc.name),
        ("Created By", requester["name"]),
        ("Status", doc.workflow_state or "Approved"),
        ("Request Link", f"<a href='{get_doc_link('Material Request', doc.name)}'>{doc.name}</a>"),
    ]
    msg = build_email_body(f"Dear {requester['name']}", f"Your Material Request <b>{doc.name}</b> has been approved.", rows)
    send_email([requester["email"]], f"Material Request {doc.name} Approved", msg)

# ============================================
#  REQUEST FOR QUOTATION NOTIFICATIONS
# ============================================

def notify_on_rfq_submit(doc, method):
    mr_name = get_linked_mr_from_items(doc)
    mr_owner = frappe.db.get_value("Material Request", mr_name, "owner") if mr_name else None
    requester = get_requester_info(mr_owner or doc.owner)
    line_mgr = get_line_manager_info(mr_owner or doc.owner)
    cost_center = get_cost_center_from_items(doc)
    
    suppliers = ", ".join([s.supplier for s in doc.suppliers]) if doc.suppliers else "N/A"
    
    rows = [
        ("RFQ ID", doc.name),
        ("MAT ID", mr_name or "N/A"),
        ("Created By", requester["name"]),
        ("Created Date", str(getdate(doc.creation))),
        ("Cost Centre", cost_center),
        ("No of Items", str(len(doc.items))),
        ("Request Link", f"<a href='{get_doc_link('Request for Quotation', doc.name)}'>{doc.name}</a>"),
        ("Suppliers", suppliers),
    ]
    
    recipients = [requester["email"], line_mgr["email"]]
    msg = build_email_body(f"Dear {requester['name']}", f"This is to notify you that Request for Quotation has been submitted with the details below:", rows)
    send_email(recipients, f"Request for Quotation {doc.name} Submitted", msg)

# ============================================
#  SUPPLIER QUOTATION NOTIFICATIONS
# ============================================

def notify_on_sq_creation(doc, method):
    mr_name = get_linked_mr_from_items(doc)
    rfq_name = get_linked_rfq_from_sq(doc.name)
    mr_owner = frappe.db.get_value("Material Request", mr_name, "owner") if mr_name else None
    requester = get_requester_info(mr_owner or doc.owner)
    line_mgr = get_line_manager_info(mr_owner or doc.owner)
    cost_center = get_cost_center_from_items(doc)
    
    rows = [
        ("SQ ID", doc.name),
        ("RFQ ID", rfq_name or "N/A"),
        ("MAT ID", mr_name or "N/A"),
        ("Created By", requester["name"]),
        ("Created Date", str(getdate(doc.creation))),
        ("Cost Centre", cost_center),
        ("No of Items", str(len(doc.items))),
        ("Request Link", f"<a href='{get_doc_link('Supplier Quotation', doc.name)}'>{doc.name}</a>"),
        ("Supplier", doc.supplier),
        ("Total Amount", fmt_money(doc.grand_total, currency=doc.currency)),
    ]
    
    recipients = [requester["email"], line_mgr["email"]]
    msg = build_email_body(f"Dear {requester['name']}", f"This is to notify you that a new Supplier Quotation has been created with the details below:", rows)
    send_email(recipients, f"Supplier Quotation {doc.name} Created", msg)

def notify_on_sq_submit(doc, method):
    mr_name = get_linked_mr_from_items(doc)
    rfq_name = get_linked_rfq_from_sq(doc.name)
    mr_owner = frappe.db.get_value("Material Request", mr_name, "owner") if mr_name else None
    requester = get_requester_info(mr_owner or doc.owner)
    biz_mgrs = get_approver_by_role("Business Manager")
    cost_center = get_cost_center_from_items(doc)
    
    rows = [
        ("SQ ID", doc.name),
        ("RFQ ID", rfq_name or "N/A"),
        ("MAT ID", mr_name or "N/A"),
        ("Created By", requester["name"]),
        ("Created Date", str(getdate(doc.creation))),
        ("Cost Centre", cost_center),
        ("No of Items", str(len(doc.items))),
        ("Request Link", f"<a href='{get_doc_link('Supplier Quotation', doc.name)}'>{doc.name}</a>"),
        ("Supplier", doc.supplier),
        ("Total Amount", fmt_money(doc.grand_total, currency=doc.currency)),
    ]
    
    for email in biz_mgrs["emails"]:
        msg = build_email_body("Dear Business Manager", f"This is to notify you that Supplier Quotation with the details below is pending approval:", rows, "Click on the link to the Request to approve on ERPNext.")
        send_email([email], f"Supplier Quotation {doc.name} Pending Business Manager Approval", msg)

def notify_on_sq_approval(doc, method):
    mr_name = get_linked_mr_from_items(doc)
    mr_owner = frappe.db.get_value("Material Request", mr_name, "owner") if mr_name else None
    requester = get_requester_info(mr_owner or doc.owner)
    
    rows = [
        ("SQ ID", doc.name),
        ("Status", "Approved"),
        ("Request Link", f"<a href='{get_doc_link('Supplier Quotation', doc.name)}'>{doc.name}</a>"),
    ]
    msg = build_email_body(f"Dear {requester['name']}", f"Your Supplier Quotation <b>{doc.name}</b> has been approved.", rows)
    send_email([requester["email"]], f"Supplier Quotation {doc.name} Approved", msg)

# ============================================
#  PURCHASE ORDER NOTIFICATIONS
# ============================================

def notify_on_po_creation(doc, method):
    sq_name = doc.ref_sq
    mr_name = None
    rfq_name = None
    
    if sq_name:
        mr_name = get_linked_mr_from_items(frappe.get_doc("Supplier Quotation", sq_name))
        rfq_name = get_linked_rfq_from_sq(sq_name)
    
    mr_owner = frappe.db.get_value("Material Request", mr_name, "owner") if mr_name else None
    requester = get_requester_info(mr_owner or doc.owner)
    treasury = get_approver_by_role("Treasury Specialist")
    
    rows = [
        ("PO ID", doc.name),
        ("SQ ID", sq_name or "N/A"),
        ("RFQ ID", rfq_name or "N/A"),
        ("MAT ID", mr_name or "N/A"),
        ("Created By", requester["name"]),
        ("Created Date", str(getdate(doc.creation))),
        ("Cost Centre", doc.cost_center or "N/A"),
        ("No of Items", str(len(doc.items))),
        ("Request Link", f"<a href='{get_doc_link('Purchase Order', doc.name)}'>{doc.name}</a>"),
        ("Supplier", doc.supplier),
        ("Total Amount", fmt_money(doc.grand_total, currency=doc.currency)),
    ]
    
    recipients = [requester["email"]] + treasury["emails"]
    msg = build_email_body(f"Dear {requester['name']}", f"This is a notification that a Purchase Order has been created with the details below:", rows)
    send_email(recipients, f"New Purchase Order {doc.name} Created", msg)

def notify_on_po_approval(doc, method):
    sq_name = doc.ref_sq
    mr_name = None
    rfq_name = None
    
    if sq_name:
        sq_doc = frappe.get_doc("Supplier Quotation", sq_name)
        mr_name = get_linked_mr_from_items(sq_doc)
        rfq_name = get_linked_rfq_from_sq(sq_name)
    
    mr_owner = frappe.db.get_value("Material Request", mr_name, "owner") if mr_name else None
    requester = get_requester_info(mr_owner or doc.owner)
    line_mgr = get_line_manager_info(mr_owner or doc.owner)
    
    rows = [
        ("PO ID", doc.name),
        ("SQ ID", sq_name or "N/A"),
        ("RFQ ID", rfq_name or "N/A"),
        ("MAT ID", mr_name or "N/A"),
        ("Created By", requester["name"]),
        ("Created Date", str(getdate(doc.creation))),
        ("Cost Centre", doc.cost_center or "N/A"),
        ("No of Items", str(len(doc.items))),
        ("Request Link", f"<a href='{get_doc_link('Purchase Order', doc.name)}'>{doc.name}</a>"),
        ("Supplier", doc.supplier),
        ("Total Amount", fmt_money(doc.grand_total, currency=doc.currency)),
    ]
    
    ws = doc.workflow_state or ""
    
    if "HOF" in ws or "Head of Finance" in ws:
        hof = get_approver_by_role("Head of Finance")
        for email in hof["emails"]:
            msg = build_email_body("Dear Head of Finance", f"This is to notify you that Purchase Order with the details below is pending approval:", rows, "Click on the link to the Request to approve on ERPNext.")
            send_email([email], f"Purchase Order {doc.name} Pending HOF Approval", msg)
    elif "Auditor" in ws:
        auditors = get_approver_by_role("Auditor")
        for email in auditors["emails"]:
            msg = build_email_body("Dear Auditor", f"This is to notify you that Purchase Order with the details below is pending approval:", rows, "Click on the link to the Request to approve on ERPNext.")
            send_email([email], f"Purchase Order {doc.name} Pending Auditor Approval", msg)
    elif "MD" in ws or "COO" in ws:
        execs = get_approver_by_role("MD") + get_approver_by_role("COO")
        for email in execs:
            msg = build_email_body("Dear MD/COO", f"This is to notify you that Purchase Order with the details below is pending approval:", rows, "Click on the link to the Request to approve on ERPNext.")
            send_email([email], f"Purchase Order {doc.name} Pending MD/COO Approval", msg)
    elif "Approved" in ws:
        recipients = [requester["email"], line_mgr["email"]]
        msg = build_email_body(f"Dear {requester['name']}", f"This is to notify you that Purchase Order with the details below is approved:", rows)
        send_email(recipients, f"Purchase Order {doc.name} Approved", msg)

# ============================================
#  PAYMENT REQUEST NOTIFICATIONS
# ============================================

def notify_on_payment_request_creation(doc, method):
    po_name = get_linked_po_from_pr(doc)
    sq_name = get_linked_sq_from_po(po_name) if po_name else None
    mr_name = None
    rfq_name = None
    
    if sq_name:
        sq_doc = frappe.get_doc("Supplier Quotation", sq_name)
        mr_name = get_linked_mr_from_items(sq_doc)
        rfq_name = get_linked_rfq_from_sq(sq_name)
    
    mr_owner = frappe.db.get_value("Material Request", mr_name, "owner") if mr_name else None
    requester = get_requester_info(mr_owner or doc.owner)
    treasury = get_approver_by_role("Treasury Specialist")
    
    rows = [
        ("PR ID", doc.name),
        ("PO ID", po_name or "N/A"),
        ("SQ ID", sq_name or "N/A"),
        ("RFQ ID", rfq_name or "N/A"),
        ("MAT ID", mr_name or "N/A"),
        ("Created By", requester["name"]),
        ("Created Date", str(getdate(doc.creation))),
        ("Cost Centre", doc.cost_center or "N/A"),
        ("Request Link", f"<a href='{get_doc_link('Payment Request', doc.name)}'>{doc.name}</a>"),
        ("Party", doc.party_name or doc.party),
        ("Total Amount", fmt_money(doc.grand_total, currency=doc.currency)),
    ]
    
    recipients = [requester["email"]] + treasury["emails"]
    msg = build_email_body(f"Dear {requester['name']}", f"This is a notification that a new Payment Request has been created with the details below:", rows)
    send_email(recipients, f"New Payment Request {doc.name} Created", msg)

def notify_on_payment_request_approval(doc, method):
    po_name = get_linked_po_from_pr(doc)
    sq_name = get_linked_sq_from_po(po_name) if po_name else None
    mr_name = None
    rfq_name = None
    
    if sq_name:
        sq_doc = frappe.get_doc("Supplier Quotation", sq_name)
        mr_name = get_linked_mr_from_items(sq_doc)
        rfq_name = get_linked_rfq_from_sq(sq_name)
    
    mr_owner = frappe.db.get_value("Material Request", mr_name, "owner") if mr_name else None
    requester = get_requester_info(mr_owner or doc.owner)
    line_mgr = get_line_manager_info(mr_owner or doc.owner)
    
    rows = [
        ("PR ID", doc.name),
        ("PO ID", po_name or "N/A"),
        ("SQ ID", sq_name or "N/A"),
        ("RFQ ID", rfq_name or "N/A"),
        ("MAT ID", mr_name or "N/A"),
        ("Created By", requester["name"]),
        ("Created Date", str(getdate(doc.creation))),
        ("Cost Centre", doc.cost_center or "N/A"),
        ("Request Link", f"<a href='{get_doc_link('Payment Request', doc.name)}'>{doc.name}</a>"),
        ("Party", doc.party_name or doc.party),
        ("Total Amount", fmt_money(doc.grand_total, currency=doc.currency)),
    ]
    
    ws = doc.workflow_state or ""
    
    if "HOF" in ws or "Head of Finance" in ws:
        hof = get_approver_by_role("Head of Finance")
        for email in hof["emails"]:
            msg = build_email_body("Dear Head of Finance", f"This is to notify you that Payment Request with the details below is pending approval:", rows, "Click on the link to the Request to approve on ERPNext.")
            send_email([email], f"Payment Request {doc.name} Pending HOF Approval", msg)
    elif "Auditor" in ws:
        auditors = get_approver_by_role("Auditor")
        for email in auditors["emails"]:
            msg = build_email_body("Dear Auditor", f"This is to notify you that Payment Request with the details below is pending approval:", rows, "Click on the link to the Request to approve on ERPNext.")
            send_email([email], f"Payment Request {doc.name} Pending Auditor Approval", msg)
    elif "MD" in ws or "COO" in ws:
        execs = get_emails_by_role("MD") + get_emails_by_role("COO")
        for email in execs:
            msg = build_email_body("Dear MD/COO", f"This is to notify you that Payment Request with the details below is pending approval:", rows, "Click on the link to the Request to approve on ERPNext.")
            send_email([email], f"Payment Request {doc.name} Pending MD/COO Approval", msg)
    elif "Approved" in ws:
        recipients = [requester["email"], line_mgr["email"]]
        msg = build_email_body(f"Dear {requester['name']}", f"This is to notify you that Payment Request with the details below is approved:", rows)
        send_email(recipients, f"Payment Request {doc.name} Approved", msg)

# ============================================
#  ESCALATION
# ============================================

def escalate_stuck_approvals():
    cutoff = now_datetime() - timedelta(days=3)
    stuck = frappe.get_all(
        "Workflow Action",
        filters={"status": "Open", "creation": ("<", cutoff)},
        fields=["reference_doctype", "reference_name", "user", "creation"]
    )

    for action in stuck:
        doc_url = get_doc_link(action.reference_doctype, action.reference_name)
        approver_email = frappe.db.get_value("User", action.user, "email")
        days_pending = (now_datetime() - action.creation).days

        rows = [
            ("Document Type", action.reference_doctype),
            ("Document ID", f"<a href='{doc_url}'>{action.reference_name}</a>"),
            ("Pending Since", f"{days_pending} days"),
            ("Assigned Approver", approver_email or action.user),
        ]

        # Notify the approver
        if approver_email:
            msg = build_email_body(
                "Dear Approver",
                f"The following document has been awaiting your approval for <b>{days_pending} days</b>. Please take action at your earliest convenience:",
                rows,
                "Click on the document link above to review and approve on ERPNext."
            )
            send_email([approver_email], f"⚠️ Reminder: {action.reference_doctype} {action.reference_name} Pending Your Approval", msg)

        # Notify escalation contacts (IT/Finance helpdesk)
        escalation_msg = build_email_body(
            "Dear Team",
            f"The following document has been stuck in approval for <b>{days_pending} days</b>:",
            rows
        )
        send_email(DEFAULT_ESCALATION_EMAILS, f"⚠️ Escalation: {action.reference_doctype} {action.reference_name} Pending {days_pending} Days", escalation_msg)
