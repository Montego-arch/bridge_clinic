from frappe import _

def get_data(data=None, **kwargs):
    return {
        "fieldname": "reference_name",   # how links are tied
        "internal_links": {
            "Employee Advance": ["advances", "employee_advance"]
        },
        "transactions": [
            {
                "label": _("Payment"),
                "items": ["Payment Entry", "Journal Entry", "Payment Request"]  # 👈 added here
            },
            {
                "label": _("Reference"),
                "items": ["Employee Advance"]
            },
        ],
    }
