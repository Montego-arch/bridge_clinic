# custom_app/overrides/payment_request.py
import frappe
from frappe import _
from frappe.utils import flt, nowdate
from erpnext.accounts.doctype.payment_request.payment_request import (
    PaymentRequest as ERPNextPaymentRequest,
    get_existing_payment_request_amount,
    get_amount,
)
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry


class CustomPaymentRequest(ERPNextPaymentRequest):
	def validate_payment_request_amount(self):
		"""Allow validation for Expense Claims as well"""

		if flt(self.grand_total) == 0:
			frappe.throw(
				_("{0} cannot be zero").format(
					self.get_label_from_fieldname("grand_total")
				),
				title=_("Invalid Amount"),
			)

		# ✅ Safely get referenced document
		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)

		# ✅ Expense Claim handling (skip ERPNext helper – no currency field)
		if ref_doc.doctype == "Expense Claim":
			existing_payment_request_amount = frappe.db.get_value(
				"Payment Request",
				{
					"reference_doctype": "Expense Claim",
					"reference_name": ref_doc.name,
					"docstatus": 1,
				},
				"sum(outstanding_amount)",
			) or 0

			ref_amount = (
				ref_doc.total_sanctioned_amount
				or ref_doc.grand_total
				or 0
			)

		else:
			# ✅ Other doctypes use ERPNext’s built-in helper
			try:
				existing_payment_request_amount = flt(
					get_existing_payment_request_amount(ref_doc)
				)
			except TypeError:
				# Fallback if ERPNext is running old signature
				existing_payment_request_amount = flt(
					get_existing_payment_request_amount(self.reference_doctype, self.reference_name)
				)

			if not hasattr(ref_doc, "order_type") or ref_doc.order_type != "Shopping Cart":
				ref_amount = get_amount(ref_doc, self.payment_account)
			else:
				ref_amount = 0

		# ✅ Prevent over-requesting
		if existing_payment_request_amount + flt(self.grand_total) > ref_amount:
			frappe.throw(
				_("Total Payment Request amount cannot be greater than {0} amount").format(
					self.reference_doctype
				)
			)



	def create_payment_entry(self, submit=False):
		"""
		Override: ensure Expense Claim creates a Payment Entry with party_type=Employee
		"""
		party_type = "Employee" if self.reference_doctype == "Expense Claim" else None

		payment_entry = get_payment_entry(
			self.reference_doctype,
			self.reference_name,
			party_amount=self.grand_total,
			party_type=party_type,
			bank_account=self.bank_account,
		)

		payment_entry.payment_request = self.name

		if not payment_entry.reference_no:
			payment_entry.reference_no = f"AUTO-{self.name}"

		if not payment_entry.reference_date:
			payment_entry.reference_date = nowdate()

		if submit:
			payment_entry.submit()
		else:
			payment_entry.insert(ignore_permissions=True)

		return payment_entry
