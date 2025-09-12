# custom_app/overrides/payment_entry.py

# import erpnext.accounts.doctype.payment_entry.payment_entry as pe

# def custom_set_party_type(doctype):
#     if doctype == "Expense Claim":
#         return "Employee"   # ✅ Map Expense Claim to Employee
#     return pe._original_set_party_type(doctype)

# # save original first, so we don’t lose it
# if not hasattr(pe, "_original_set_party_type"):
#     pe._original_set_party_type = pe.set_party_type

# # patch ERPNext’s set_party_type
# pe.set_party_type = custom_set_party_type
# bridge_clinic/overrides/custom_payment_entry.py
# from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
# from erpnext.accounts.doctype.payment_entry.payment_entry import get_reference_details

# class CustomPaymentEntry(PaymentEntry):
#     def set_missing_ref_details(
#         self,
#         force: bool = False,
#         update_ref_details_only_for: list | None = None,
#         reference_exchange_details: dict | None = None,
#     ) -> None:
#         for d in self.get("references"):
#             if d.allocated_amount:
#                 if update_ref_details_only_for and (
#                     (d.reference_doctype, d.reference_name) not in update_ref_details_only_for
#                 ):
#                     continue

#                 ref_details = get_reference_details(
#                     d.reference_doctype,
#                     d.reference_name,
#                     self.party_account_currency,
#                     self.party_type,
#                     self.party,
#                 )

#                 # Fix: ERPNext sends a dict, not an object
#                 if (
#                     reference_exchange_details
#                     and d.reference_doctype == reference_exchange_details.get("reference_doctype")
#                     and d.reference_name == reference_exchange_details.get("reference_name")
#                 ):
#                     ref_details.update({
#                         "exchange_rate": reference_exchange_details.get("exchange_rate")
#                     })

#                 for field, value in ref_details.items():
#                     if d.exchange_gain_loss:
#                         continue

#                     if field == "exchange_rate" or not d.get(field) or force:
#                         d.db_set(field, value)


from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
from erpnext.accounts.doctype.payment_entry.payment_entry import get_reference_details

class CustomPaymentEntry(PaymentEntry):
    def set_missing_ref_details(
        self,
        force: bool = False,
        update_ref_details_only_for: list | None = None,
        reference_exchange_details: dict | None = None,
    ) -> None:
        for d in self.get("references"):
            if d.allocated_amount:
                if update_ref_details_only_for and (
                    (d.reference_doctype, d.reference_name) not in update_ref_details_only_for
                ):
                    continue

                ref_details = get_reference_details(
                    d.reference_doctype,
                    d.reference_name,
                    self.party_account_currency,
                    self.party_type,
                    self.party,
                )

                # Fix: ERPNext sends a dict, not an object
                if (
                    reference_exchange_details
                    and d.reference_doctype == reference_exchange_details.get("reference_doctype")
                    and d.reference_name == reference_exchange_details.get("reference_name")
                ):
                    ref_details.update({
                        "exchange_rate": reference_exchange_details.get("exchange_rate")
                    })

                for field, value in ref_details.items():
                    if d.exchange_gain_loss:
                        continue

                    if field == "exchange_rate" or not d.get(field) or force:
                        d.db_set(field, value)

    def get_valid_reference_doctypes(self):
        """Extend ERPNext validation to allow Expense Claim for Employees"""
        if self.party_type == "Customer":
            return ("Sales Order", "Sales Invoice", "Journal Entry", "Dunning", "Payment Entry")
        elif self.party_type == "Supplier":
            return ("Purchase Order", "Purchase Invoice", "Journal Entry", "Payment Entry")
        elif self.party_type == "Shareholder":
            return ("Journal Entry",)
        elif self.party_type == "Employee":
            # ✅ Add Expense Claim here
            return ("Journal Entry", "Expense Claim")
        return super().get_valid_reference_doctypes()
