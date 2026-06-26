"""Behavioral tests for the PR -> PI automation helpers.

These test the externally-visible results the helpers produce — whether a tax
row ends up as Add vs Deduct, and whether a due date is pushed forward so it
never precedes the posting/bill date. They are pure (no DB, no app install
required) so they run on the shared home.com bench via --module.
"""

from datetime import date

from frappe.tests.utils import FrappeTestCase
from frappe import _dict

from bridge_clinic.api import (
    WHT_ACCOUNTS,
    map_pr_tax_to_pi,
    clamp_due_date,
)


class TestPrPiTaxMapping(FrappeTestCase):
    def test_wht_account_is_forced_to_deduct(self):
        # WHT row entered as "Add" on the receipt must become "Deduct" on the invoice
        tax = _dict(
            account_head=WHT_ACCOUNTS[0],
            charge_type="Actual",
            rate=0,
            tax_amount=500,
            add_deduct_tax="Add",
        )
        result = map_pr_tax_to_pi(tax)
        self.assertEqual(result["add_deduct_tax"], "Deduct")
        self.assertEqual(result["account_head"], WHT_ACCOUNTS[0])
        self.assertEqual(result["tax_amount"], 500)

    def test_non_wht_deduct_flag_is_preserved(self):
        tax = _dict(
            account_head="2110 - VAT - BCL",
            charge_type="On Net Total",
            rate=7.5,
            tax_amount=750,
            add_deduct_tax="Deduct",
        )
        result = map_pr_tax_to_pi(tax)
        self.assertEqual(result["add_deduct_tax"], "Deduct")

    def test_non_wht_without_flag_defaults_to_add(self):
        tax = _dict(
            account_head="2110 - VAT - BCL",
            charge_type="On Net Total",
            rate=7.5,
            tax_amount=750,
        )
        result = map_pr_tax_to_pi(tax)
        self.assertEqual(result["add_deduct_tax"], "Add")


class TestClampDueDate(FrappeTestCase):
    def test_due_date_before_posting_is_pushed_to_posting(self):
        # The bug: a due date earlier than the posting date triggers
        # "Due date cannot be before Posting/Supplier invoice date".
        result = clamp_due_date(
            due_date=date(2026, 1, 1),
            posting_date=date(2026, 6, 10),
            bill_date=date(2026, 6, 10),
        )
        self.assertEqual(result, date(2026, 6, 10))

    def test_later_due_date_is_kept(self):
        result = clamp_due_date(
            due_date=date(2026, 7, 10),
            posting_date=date(2026, 6, 10),
            bill_date=date(2026, 6, 10),
        )
        self.assertEqual(result, date(2026, 7, 10))
