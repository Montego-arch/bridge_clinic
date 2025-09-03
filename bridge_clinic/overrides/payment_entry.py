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
