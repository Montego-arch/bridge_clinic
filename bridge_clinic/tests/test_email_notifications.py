"""Behavioral tests: notification emails must be limited to Bridge Clinic Limited.

The client runs 5 companies on one ERPNext site. Notifications from this app
must only fire for Bridge Clinic Limited documents and only reach users who
belong to Bridge Clinic Limited (i.e. have an Active Employee record in that
company).

These tests run against a real bench DB (no mocks): they create real User /
Employee / Company rows, invoke the notification entry points the doc_events
hooks call, and assert on the externally visible result — rows in Email Queue.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime, nowdate

from bridge_clinic.email_notifications import (
    get_emails_by_role,
    notify_on_mr_submit,
)

TARGET_COMPANY = "Bridge Clinic Limited"
OTHER_COMPANY = "_Test Company"
ROLE = "Business Manager"


def ensure_company(name, abbr):
    if not frappe.db.exists("Company", name):
        frappe.get_doc(
            {
                "doctype": "Company",
                "company_name": name,
                "abbr": abbr,
                "default_currency": "NGN",
                "country": "Nigeria",
            }
        ).insert(ignore_permissions=True)


def ensure_role(role):
    if not frappe.db.exists("Role", role):
        frappe.get_doc({"doctype": "Role", "role_name": role}).insert(
            ignore_permissions=True
        )


def make_user_with_role(email, role):
    if frappe.db.exists("User", email):
        user = frappe.get_doc("User", email)
    else:
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": email.split("@")[0],
                "send_welcome_email": 0,
            }
        ).insert(ignore_permissions=True)
    user.add_roles(role)
    return user.name


def ensure_outgoing_email_account():
    """The dev site has no outgoing Email Account; Email Queue insertion needs one.

    This stubs the minimum boundary (an SMTP account record) — nothing is
    actually sent in test mode.
    """
    if frappe.db.exists("Email Account", {"default_outgoing": 1, "enable_outgoing": 1}):
        return
    frappe.get_doc(
        {
            "doctype": "Email Account",
            "email_account_name": "_Test Bridge Outgoing",
            "email_id": "test_bridge_outgoing@example.com",
            "smtp_server": "localhost",
            "smtp_port": 25,
            "use_tls": 0,
            "enable_outgoing": 1,
            "default_outgoing": 1,
            "no_smtp_authentication": 1,
        }
    ).insert(ignore_permissions=True)


def make_employee_record(user, company):
    existing = frappe.db.exists("Employee", {"user_id": user})
    if existing:
        frappe.db.set_value("Employee", existing, {"company": company, "status": "Active"})
        return existing
    emp = frappe.get_doc(
        {
            "doctype": "Employee",
            "first_name": user.split("@")[0],
            "gender": "Male",
            "date_of_birth": "1990-01-01",
            "date_of_joining": "2024-01-01",
            "company": company,
            "status": "Active",
            "user_id": user,
        }
    ).insert(ignore_permissions=True)
    return emp.name


class TestCompanyScopedNotifications(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_company(TARGET_COMPANY, "BCL")
        ensure_role(ROLE)
        ensure_outgoing_email_account()
        cls.bcl_email = "bcl.manager@test-bridge-clinic.com"
        cls.other_email = "other.manager@test-bridge-clinic.com"
        make_user_with_role(cls.bcl_email, ROLE)
        make_user_with_role(cls.other_email, ROLE)
        make_employee_record(cls.bcl_email, TARGET_COMPANY)
        make_employee_record(cls.other_email, OTHER_COMPANY)

    # ------------- helpers -------------

    def _make_mr_doc(self, company, owner):
        """Build an in-memory Material Request the way the on_submit hook sees it.

        Not inserted: inserting would fire this app's other doc_events
        (RFQ auto-creation etc.) which are not under test here. The notify
        function only reads fields off the doc.
        """
        doc = frappe.get_doc(
            {
                "doctype": "Material Request",
                "material_request_type": "Purchase",
                "company": company,
                "transaction_date": nowdate(),
                "schedule_date": nowdate(),
                "custom_description": "test request",
                "items": [
                    {
                        "doctype": "Material Request Item",
                        "item_code": "_Test Item",
                        "qty": 1,
                        "schedule_date": nowdate(),
                    }
                ],
            }
        )
        doc.name = "TEST-MR-" + frappe.generate_hash(length=8)
        doc.owner = owner
        doc.creation = now_datetime()
        return doc

    def _new_queue_recipients(self, before_names):
        rows = frappe.get_all("Email Queue", pluck="name")
        new_rows = set(rows) - set(before_names)
        recipients = set()
        for name in new_rows:
            recipients.update(
                frappe.get_all(
                    "Email Queue Recipient",
                    filters={"parent": name},
                    pluck="recipient",
                )
            )
        return recipients

    # ------------- tests -------------

    def test_role_emails_limited_to_bridge_clinic_company(self):
        """Role-based recipients must only include Bridge Clinic Limited employees."""
        emails = get_emails_by_role(ROLE)
        self.assertIn(self.bcl_email, emails)
        self.assertNotIn(self.other_email, emails)

    def test_mr_submit_sends_nothing_for_other_company(self):
        """A Material Request belonging to another company must not email anyone."""
        before = frappe.get_all("Email Queue", pluck="name")
        doc = self._make_mr_doc(OTHER_COMPANY, self.other_email)
        notify_on_mr_submit(doc, "on_submit")
        self.assertEqual(self._new_queue_recipients(before), set())

    def test_mr_submit_notifies_requester_for_bridge_clinic(self):
        """A Bridge Clinic Limited Material Request still notifies its requester."""
        before = frappe.get_all("Email Queue", pluck="name")
        doc = self._make_mr_doc(TARGET_COMPANY, self.bcl_email)
        notify_on_mr_submit(doc, "on_submit")
        self.assertIn(self.bcl_email, self._new_queue_recipients(before))
