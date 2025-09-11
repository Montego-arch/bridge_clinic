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
        pr.currency = "NGN"
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
    


def fill_suppliers_in_material_request(doc, method):
    # Clear suppliers first (if you want them always regenerated fresh)
    doc.custom_supplier_table = []

    seen_item_groups = set()
    seen_suppliers = set()

    for item in doc.items:
        if not item.item_code:
            continue

        item_group = frappe.db.get_value("Item", item.item_code, "item_group")
        if not item_group or item_group in seen_item_groups:
            continue

        seen_item_groups.add(item_group)

        suppliers = frappe.get_all(
            "Material Request Supplier",
            filters={"parent": item_group, "parenttype": "Item Group"},
            fields=["supplier", "contact", "email_id"]
        )

        for sup in suppliers:
            if not sup.supplier or sup.supplier in seen_suppliers:
                continue

            doc.append("custom_supplier_table", {
                "supplier": sup.supplier,
                "contact": sup.contact,
                "email_id": sup.email_id
            })
            seen_suppliers.add(sup.supplier)



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
        rfq.message_for_supplier = f"Please supply the specified items at the best possible rates for {doc.name}."

        # copy MR items
        for item in doc.items:
            rfq.append("items", {
                "item_code": item.item_code,
                "qty": item.qty,
                "schedule_date": item.schedule_date or nowdate(),
                "material_request": doc.name,
                "material_request_item": item.name,
                "warehouse": item.warehouse,
                "uom": item.uom,
                "conversion_factor": item.conversion_factor,
                "stock_uom": item.stock_uom
            })

        # copy MR suppliers
        for sup in doc.custom_supplier_table:
            rfq.append("suppliers", {
                "supplier": sup.supplier,
                "contact": sup.contact,
                "email_id": sup.email_id
            })

        rfq.insert(ignore_permissions=True)

        frappe.msgprint(
            ("Request for Quotation <b>{0}</b> created successfully.").format(rfq.name),
            alert=True,
            indicator="green"
        )

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Failed to create RFQ from MR")
        raise



# def create_po_from_rfq(doc, method):
#     try:
#         existing = frappe.db.exists("Purchase Order", {
#             "custom_linked_rfq": doc.name  # ✅ use custom field
#         })
#         if existing:
#             return

#         po = frappe.new_doc("Purchase Order")
#         po.company = doc.company
#         po.transaction_date = nowdate()
#         po.custom_linked_rfq = doc.name   # ✅ store RFQ link
#         po.supplier = doc.suppliers[0].supplier if doc.suppliers else None
#         po.custom_payment_type = "Non-Prepayment"

#         for item in doc.items:
#             po.append("items", {
#                 "item_code": item.item_code,
#                 "qty": item.qty,
#                 "schedule_date": item.schedule_date or nowdate(),
#                 "warehouse": item.warehouse,
#                 "conversion_factor": item.conversion_factor,
#             })

#         po.insert(ignore_permissions=True)

#         frappe.msgprint(
#             ("Purchase Order <b>{0}</b> created successfully.").format(po.name),
#             alert=True,
#             indicator="green"
#         )

#     except Exception:
#         frappe.log_error(frappe.get_traceback(), "Failed to create PO from RFQ")
#         raise




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




# def create_payment_request_from_pi(doc, method):
#     """
#     On submission of Purchase Invoice, create a Payment Request in Draft
#     only if no Paid Payment Request already exists.
#     """
#     try:
#         # Check for existing PR linked to this PI
#         pr_list = frappe.get_all(
#             "Payment Request",
#             filters={"reference_doctype": "Purchase Invoice", "reference_name": doc.name},
#             fields=["name", "status"]
#         )

#         # If any PR is already Paid → stop
#         if any(pr.status == "Paid" for pr in pr_list):
#             return

#         # If unpaid PR already exists → stop
#         if any(pr.status in ("Initiated", "Draft", "Unpaid") for pr in pr_list):
#             return

#         pr = frappe.new_doc("Payment Request")
#         pr.payment_request_type = "Outward"
#         pr.reference_doctype = "Purchase Invoice"
#         pr.reference_name = doc.name
#         pr.party_type = "Supplier"
#         pr.party = doc.supplier
#         pr.transaction_date = nowdate()
#         pr.grand_total = doc.grand_total
#         pr.status = "Draft"

#         if frappe.db.exists("Mode of Payment", "Bank"):
#             pr.mode_of_payment = "Bank"

#         pr.insert(ignore_permissions=True)

#         frappe.msgprint(
#             ("Payment Request <b>{0}</b> created successfully.").format(pr.name),
#             alert=True,
#             indicator="green"
#         )

#     except Exception:
#         frappe.log_error(frappe.get_traceback(), "Failed to create PR from PI")
#         raise



def create_po_from_supplier_quotation(doc, method):
    try:
        # Avoid duplicates → check if PO already exists for this quotation
        existing = frappe.db.exists("Purchase Order", {
            "supplier_quotation": doc.name
        })
        if existing:
            return

        po = frappe.new_doc("Purchase Order")
        po.company = doc.company
        po.transaction_date = nowdate()
        po.supplier = doc.supplier
        po.supplier_quotation = doc.name  # custom link field in PO (if not standard, add custom)
        po.custom_payment_type = "Non-Prepayment"

        # Copy quotation items into PO
        for item in doc.items:
            po.append("items", {
                "item_code": item.item_code,
                "qty": item.qty,
                "rate": item.rate,
                "schedule_date": nowdate(),
                "warehouse": item.warehouse,
                "uom": item.uom,
                "conversion_factor": item.conversion_factor,
            })

        po.insert(ignore_permissions=True)  # Save as Draft (do not submit)

        frappe.msgprint(
            ("Purchase Order <b>{0}</b> created in Draft from Supplier Quotation {1}.")
            .format(po.name, doc.name),
            alert=True,
            indicator="green"
        )

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Failed to create PO from Supplier Quotation")
        raise


def create_payment_request_from_po(doc, method):
    """
    After submitting a Purchase Order, generate a draft Payment Request
    if custom_payment_type == 'Prepayment'.
    """
    try:
        if doc.custom_payment_type != "Prepayment":
            return  # do nothing for Non-Prepayment

        # avoid duplicates
        existing = frappe.db.exists("Payment Request", {
            "reference_doctype": "Purchase Order",
            "reference_name": doc.name
        })
        if existing:
            return

        pr = frappe.new_doc("Payment Request")
        pr.payment_request_type = "Outward"
        pr.reference_doctype = "Purchase Order"
        pr.reference_name = doc.name
        pr.party_type = "Supplier"
        pr.party = doc.supplier
        pr.transaction_date = nowdate()

        # set mandatory fields
        pr.currency = doc.currency
        pr.grand_total = doc.grand_total or 0
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
        frappe.log_error(frappe.get_traceback(), "Failed to create Payment Request from PO")
        raise




from frappe.utils import flt
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request

def link_advances_manually(pi, supplier):
    """Link submitted Payment Entries as advances against Purchase Invoice."""
    advances = frappe.get_all(
        "Payment Entry Reference",
        filters={
            "reference_doctype": "Purchase Order",
            "reference_name": pi.purchase_order,
            "allocated_amount": [">", 0],
        },
        fields=["parent", "allocated_amount", "name"]
    )

    for adv in advances:
        pi.append("advances", {
            "reference_type": "Payment Entry",
            "reference_name": adv.parent,
            "reference_row": adv.name,
            "advance_amount": adv.allocated_amount,
            "allocated_amount": adv.allocated_amount,
            "remarks": "Auto-linked during Purchase Receipt → PI"
        })

    pi.save(ignore_permissions=True)



# def handle_purchase_receipt_on_submit_for_draft(doc, method):
#     """On submission of PR, auto-create PI and draft Payment Request depending on payment type."""
#     if not doc.items:
#         return

#     # --- Step 1: Get linked PO (assuming PR created from PO) ---
#     po = frappe.get_doc("Purchase Order", doc.items[0].purchase_order)
#     payment_type = po.custom_payment_type or "Non-Prepayment"

#     # --- Step 2: Create Purchase Invoice from PR ---
#     pi = frappe.new_doc("Purchase Invoice")
#     pi.supplier = po.supplier
#     pi.posting_date = doc.posting_date
#     pi.purchase_receipt = doc.name
#     pi.purchase_order = po.name
#     pi.company = po.company

#     for item in doc.items:
#         pi.append("items", {
#             "item_code": item.item_code,
#             "qty": item.qty,
#             "rate": item.rate,
#             "amount": item.amount,
#             "purchase_receipt": doc.name,
#             "purchase_order": item.purchase_order,
#             "po_detail": getattr(item, "po_detail", None)
#         })

#     pi.save(ignore_permissions=True)

#     # --- Step 3: Handle Prepayment / Non-Prepayment logic ---
#     if payment_type == "Prepayment":
#         link_advances_manually(pi, po.supplier)

#     # Submit PI
#     pi.submit()

#     # --- Step 4: Always manually create Payment Request in Draft ---
#     outstanding = flt(pi.outstanding_amount)
#     if payment_type == "Prepayment" and outstanding <= 0:
#         return

#     pr = frappe.get_doc({
#         "doctype": "Payment Request",
#         "payment_request_type": "Outward",
#         "party_type": "Supplier",
#         "party": pi.supplier,
#         "currency": pi.currency,
#         "grand_total": outstanding,
#         "amount": outstanding,
#         "reference_doctype": "Purchase Invoice",
#         "reference_name": pi.name,
#         "status": "Draft",
#         "company": pi.company,
#     })

#     # 💡 This is always safe — pr is a real Doc object
#     pr.insert(ignore_permissions=True)

#     frappe.msgprint(f"Draft Payment Request created for Purchase Invoice {pi.name}")


def handle_purchase_receipt_on_submit_for_draft(doc, method):
    """On submission of PR, auto-create PI and draft Payment Request depending on payment type."""
    if not doc.items:
        return

    # --- Step 1: Get linked PO (assuming PR created from PO) ---
    po = frappe.get_doc("Purchase Order", doc.items[0].purchase_order)
    payment_type = po.custom_payment_type or "Non-Prepayment"

    # --- Step 2: Create Purchase Invoice from PR ---
    pi = frappe.new_doc("Purchase Invoice")
    pi.supplier = po.supplier
    pi.company = po.company  # ✅ force set company
    pi.posting_date = doc.posting_date
    pi.purchase_receipt = doc.name
    pi.purchase_order = po.name
    pi.currency = po.currency

    for item in doc.items:
        pi.append("items", {
            "item_code": item.item_code,
            "qty": item.qty,
            "rate": item.rate,
            "amount": item.amount,
            "purchase_receipt": doc.name,
            "purchase_order": item.purchase_order,
            "po_detail": getattr(item, "po_detail", None)
        })

    pi.save(ignore_permissions=True)

    # --- Step 3: Handle Prepayment / Non-Prepayment logic ---
    if payment_type == "Prepayment":
        link_advances_manually(pi, po.supplier)

    # Submit PI
    pi.submit()

    # --- Step 4: Always manually create Payment Request in Draft ---
    outstanding = flt(pi.outstanding_amount)

    # Debugging info
    # frappe.msgprint(f"DEBUG: pi.company={pi.company}, outstanding={outstanding}")

    if payment_type == "Prepayment" and outstanding <= 0:
        return

    pr = frappe.get_doc({
        "doctype": "Payment Request",
        "payment_request_type": "Outward",   # ✅ must be Outward for Supplier
        "party_type": "Supplier",
        "party": pi.supplier,
        "currency": pi.currency,
        "grand_total": outstanding,
        "amount": outstanding,
        "reference_doctype": "Purchase Invoice",
        "reference_name": pi.name,
        "status": "Draft",
        "company": pi.company,               # ✅ ensure company is set
    })

    pr.insert(ignore_permissions=True)

    frappe.msgprint(f"Draft Payment Request created for Purchase Invoice {pi.name}")







def link_prepayment_to_pi(po, pi):
    """Manually link advance Payment Entries against Purchase Invoice."""
    advances = frappe.get_all(
        "Payment Entry Reference",
        filters={
            "reference_doctype": "Purchase Order",
            "reference_name": po.name
        },
        fields=["parent", "allocated_amount"]
    )

    for adv in advances:
        pe = frappe.get_doc("Payment Entry", adv.parent)

        # skip if not submitted
        if pe.docstatus != 1:
            continue

        # check if already linked to PI
        already_linked = any(
            ref.reference_doctype == "Purchase Invoice"
            and ref.reference_name == pi.name
            for ref in pe.references
        )
        if already_linked:
            continue

        # create new reference row for PI
        pe.append("references", {
            "reference_doctype": "Purchase Invoice",
            "reference_name": pi.name,
            "allocated_amount": adv.allocated_amount,
            "balance_amount": 0,
            "due_date": pi.due_date,
        })

        # re-run advance updates
        pe.set_total_allocated_amount()
        pe.set_unallocated_amount()
        pe.update_advance_paid()
        pe.flags.ignore_validate_update_after_submit = True
        pe.save(ignore_permissions=True)
        frappe.db.commit()




def handle_purchase_receipt_on_submit(doc, method):
    """
    When a Purchase Receipt is submitted:
    - If linked Purchase Order has custom_payment_type = 'Prepayment'
      → Generate and submit Purchase Invoice, pull advances
      → If outstanding remains, create Payment Request for that balance
    """
    try:
        # Find linked Purchase Orders from receipt items
        po_names = [d.purchase_order for d in doc.items if d.purchase_order]
        if not po_names:
            return

        for po_name in set(po_names):
            po = frappe.get_doc("Purchase Order", po_name)

            # Only handle Prepayment case
            if po.custom_payment_type != "Prepayment":
                continue

            # --- Step 1: Create Purchase Invoice ---
            pi = frappe.new_doc("Purchase Invoice")
            pi.supplier = po.supplier
            pi.company = po.company
            pi.currency = po.currency
            pi.due_date = nowdate()
            pi.purchase_order = po.name
            pi.purchase_receipt = doc.name

            # copy items from PR
            for item in doc.items:
                pi.append("items", {
                    "item_code": item.item_code,
                    "qty": item.qty,
                    "rate": item.rate,
                    "amount": item.amount,
                    "uom": item.uom,
                    "purchase_order": item.purchase_order,
                    "purchase_receipt": doc.name,
                    "cost_center": item.cost_center,
                })

            # Pull advances
            pi.set_advances()

            # Save and Submit PI
            pi.insert(ignore_permissions=True)
            pi.submit()

            frappe.msgprint(
                f"Purchase Invoice <b>{pi.name}</b> created and submitted with advances.",
                alert=True,
                indicator="green"
            )

            # --- Step 2: Handle Outstanding ---
            if pi.outstanding_amount and pi.outstanding_amount > 0:
                pr = frappe.new_doc("Payment Request")
                pr.payment_request_type = "Outward"
                pr.reference_doctype = "Purchase Invoice"
                pr.reference_name = pi.name
                pr.party_type = "Supplier"
                pr.party = pi.supplier
                pr.transaction_date = nowdate()
                pr.currency = pi.currency
                pr.company = pi.company
                pr.grand_total = pi.outstanding_amount
                pr.status = "Draft"

                if frappe.db.exists("Mode of Payment", "Bank"):
                    pr.mode_of_payment = "Bank"

                pr.insert(ignore_permissions=True)

                frappe.msgprint(
                    f"Outstanding found. Payment Request <b>{pr.name}</b> created in Draft.",
                    alert=True,
                    indicator="orange"
                )
            else:
                frappe.msgprint(
                    f"No outstanding for Purchase Invoice <b>{pi.name}</b>. No Payment Request created.",
                    alert=True,
                    indicator="blue"
                )

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Failed: PI/PR creation from PR")
        raise


def get_dashboard_data(data):
    """Extend dashboard for Expense Claim"""
    if data.get("doctype") == "Expense Claim":
        data["transactions"] += [
            {
                "label": "Payments",
                "items": ["Payment Request", "Payment Entry"],
            }
        ]
    return data



def update_expense_status_on_pr(doc, method):
    """When Payment Request is created → set Expense Claim to Payment Requested"""
    if doc.reference_doctype == "Expense Claim":
        frappe.db.set_value("Expense Claim", doc.reference_name, "approval_status", "Payment Requested")

def update_expense_status_on_pe(doc, method):
    """When Payment Entry is submitted → set Expense Claim to Paid"""
    for ref in doc.references or []:
        if ref.reference_doctype == "Expense Claim":
            frappe.db.set_value("Expense Claim", ref.reference_name, "approval_status", "Paid")
