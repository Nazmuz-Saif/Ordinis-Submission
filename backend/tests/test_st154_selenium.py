
"""
ST-154 Selenium tests, TC-127 to TC-130:
notes on suspend/activate, Request access, Help & Support, and the sidebar.

Requirements:
- Demo data seeded using: python manage.py seed_demo_data
- Backend on :8000
- Frontend on :5173
- Chrome installed

Run from backend/:
    python -m unittest tests.test_st154_selenium -v
"""

import os
import sys
import unittest
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "apps"))
sys.path.insert(0, str(BASE_DIR / "tests"))

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.development",
)

import django  # noqa: E402

django.setup()

from selenium.common.exceptions import TimeoutException  # noqa: E402
from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402

from core import demo  # noqa: E402
from platform_admin.models import (  # noqa: E402
    SupportAccessRequest,
    SupportTicket,
)
from selenium_helpers import (  # noqa: E402
    FRONTEND_URL,
    clear_session,
    login_as_demo,
    make_driver,
)
from tenants.models import Company  # noqa: E402


class ST154SeleniumTest(unittest.TestCase):

    def setUp(self):
        self.driver, self.wait = make_driver()

    def tearDown(self):
        try:
            clear_session(self.driver)
        except Exception:
            pass
        finally:
            try:
                self.driver.quit()
            except Exception:
                pass

    def css(self, selector):
        return self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, selector)
            )
        )

    def clickable(self, selector):
        return self.wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, selector)
            )
        )

    def company_row(self, name):
        return self.wait.until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    "//*[@data-testid='company-row']"
                    f"[.//a[normalize-space()='{name}']]",
                )
            )
        )

    def ticket_item(self, subject):
        return self.wait.until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    "//*[@data-testid='ticket-item']"
                    f"[contains(.,'{subject}')]",
                )
            )
        )

    def ticket_row(self, subject):
        return self.wait.until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    "//*[@data-testid='ticket-row']"
                    f"[contains(.,'{subject}')]",
                )
            )
        )

    # TC-127
    def test_tc127_suspend_needs_a_note_and_the_note_shows_in_activity(self):
        company, _ = Company.objects.get_or_create(
            subdomain="note-corp",
            defaults={
                "name": "Note Test Corp",
                "is_active": True,
            },
        )

        Company.objects.filter(pk=company.pk).update(is_active=True)

        note = f"Unpaid invoice {uuid.uuid4().hex[:6]}"

        try:
            login_as_demo(
                self.driver,
                self.wait,
                "Platform Admin",
            )
            self.driver.get(f"{FRONTEND_URL}/admin/companies")

            self.company_row(company.name).find_element(
                By.CSS_SELECTOR,
                "[data-testid='suspend-btn']",
            ).click()

            self.css("[data-testid='company-note']")

            # Attempt 1: empty note must be rejected.
            self.clickable("[data-testid='confirm-btn']").click()

            self.assertIn(
                "required",
                self.css("[role='alert']").text.lower(),
            )

            # Attempt 2: a short note must be rejected.
            note_input = self.css("[data-testid='company-note']")
            note_input.send_keys("too short")

            self.clickable("[data-testid='confirm-btn']").click()

            self.assertIn(
                "at least 10",
                self.css("[role='alert']").text.lower(),
            )

            self.assertTrue(
                Company.objects.get(pk=company.pk).is_active,
                "Company should remain active after invalid note submissions.",
            )

            # Attempt 3: valid note should allow suspension.
            note_input = self.css("[data-testid='company-note']")
            note_input.clear()
            note_input.send_keys(note)

            self.clickable("[data-testid='confirm-btn']").click()

            self.assertIn(
                "suspended",
                self.css("[data-testid='admin-message']").text.lower(),
            )

            self.assertFalse(
                Company.objects.get(pk=company.pk).is_active,
                "Company should be inactive after suspension.",
            )

            # Verify the note is recorded in the activity log.
            self.driver.get(f"{FRONTEND_URL}/admin/activity")

            activity_row = self.wait.until(
                EC.visibility_of_element_located(
                    (
                        By.XPATH,
                        "//*[@data-testid='activity-row']"
                        f"[contains(.,'{note}')]",
                    )
                )
            )

            self.assertIn("Suspended", activity_row.text)

        finally:
            # Restore the test company to an active state.
            Company.objects.filter(pk=company.pk).update(is_active=True)

    # TC-128
    def test_tc128_request_access_from_the_companies_page(self):
        company = Company.objects.get(subdomain=demo.SUBDOMAIN)
        reason = f"Check bug {uuid.uuid4().hex[:6]}"

        try:
            login_as_demo(
                self.driver,
                self.wait,
                "Platform Admin",
            )
            self.driver.get(f"{FRONTEND_URL}/admin/companies")

            self.company_row(company.name).find_element(
                By.CSS_SELECTOR,
                "[data-testid='request-access-btn']",
            ).click()

            self.css("[data-testid='access-reason']").send_keys(reason)

            self.clickable("[data-testid='confirm-btn']").click()

            self.assertIn(
                "Access request sent",
                self.css("[data-testid='admin-message']").text,
            )

            self.driver.get(f"{FRONTEND_URL}/admin/access-requests")

            request_row = self.wait.until(
                EC.visibility_of_element_located(
                    (
                        By.XPATH,
                        "//*[@data-testid='request-row']"
                        f"[contains(.,'{reason}')]",
                    )
                )
            )

            self.assertIn("Pending", request_row.text)

        finally:
            # Delete only the request created by this test.
            SupportAccessRequest.objects.filter(
                company=company,
                reason=reason,
            ).delete()

    # TC-129
    def test_tc129_ticket_from_help_and_support_then_resolved_with_a_note(self):
        subject = f"Payslip is empty {uuid.uuid4().hex[:6]}"
        description = "My payslip shows nothing for last month."
        answer = "Payslip generated again, please check"

        try:
            # Step 1: Employee submits a support ticket.
            login_as_demo(
                self.driver,
                self.wait,
                "Employee",
            )
            self.driver.get(f"{FRONTEND_URL}/settings/help")

            # Use normal Selenium typing; do not use the custom helper
            # that previously failed while checking the live input value.
            subject_input = self.css(
                "[data-testid='ticket-subject']"
            )
            subject_input.send_keys(subject)

            description_input = self.css(
                "[data-testid='ticket-description']"
            )
            description_input.send_keys(description)

            self.clickable(
                "[data-testid='ticket-submit']"
            ).click()

            # Verify that submission succeeds in the UI.
            try:
                self.wait.until(
                    EC.visibility_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            "[data-testid='ticket-sent']",
                        )
                    )
                )

            except TimeoutException:
                # Capture the actual state instead of reporting only timeout.
                db_ticket = SupportTicket.objects.filter(
                    subject=subject
                ).first()

                form_text = ""
                forms = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "[data-testid='ticket-form']",
                )
                if forms:
                    form_text = forms[0].text

                visible_messages = []
                for element in self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "[role='alert'], [role='status']",
                ):
                    if element.is_displayed():
                        message = element.text.strip()
                        if message:
                            visible_messages.append(message)

                current_subject = ""
                subject_elements = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "[data-testid='ticket-subject']",
                )
                if subject_elements:
                    current_subject = subject_elements[0].get_attribute(
                        "value"
                    ) or ""

                current_description = ""
                description_elements = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "[data-testid='ticket-description']",
                )
                if description_elements:
                    current_description = (
                        description_elements[0].get_attribute("value") or ""
                    )

                self.fail(
                    "Ticket submission did not show the success message. "
                    f"Backend record exists: {db_ticket is not None}. "
                    f"Backend status: "
                    f"{getattr(db_ticket, 'status', None)!r}. "
                    f"Current URL: {self.driver.current_url!r}. "
                    f"Visible messages: {visible_messages!r}. "
                    f"Form text: {form_text!r}. "
                    f"Current subject value: {current_subject!r}. "
                    f"Current description value: "
                    f"{current_description!r}."
                )

            # Verify the employee sees the newly created ticket.
            item = self.ticket_item(subject)

            self.assertIn(
                "Open",
                item.find_element(
                    By.CSS_SELECTOR,
                    "[data-testid='ticket-item-status']",
                ).text,
            )

            # Step 2: Platform Admin resolves the ticket with a note.
            clear_session(self.driver)

            login_as_demo(
                self.driver,
                self.wait,
                "Platform Admin",
            )
            self.driver.get(f"{FRONTEND_URL}/admin/tickets")

            row = self.ticket_row(subject)

            row.find_element(
                By.CSS_SELECTOR,
                "[data-testid='resolve-btn']",
            ).click()

            self.css(
                "[data-testid='resolution-note']"
            ).send_keys(answer)

            self.clickable(
                "[data-testid='confirm-btn']"
            ).click()

            # Verify the resolution is recorded for the admin.
            resolution = self.wait.until(
                EC.visibility_of_element_located(
                    (
                        By.XPATH,
                        "//*[@data-testid='ticket-row']"
                        f"[contains(.,'{subject}')]"
                        "//*[@data-testid='ticket-resolution']",
                    )
                )
            )

            self.assertIn(answer, resolution.text)

            # Step 3: Employee verifies resolved status and resolution note.
            clear_session(self.driver)

            login_as_demo(
                self.driver,
                self.wait,
                "Employee",
            )
            self.driver.get(f"{FRONTEND_URL}/settings/help")

            item = self.ticket_item(subject)

            self.assertIn(
                "Resolved",
                item.find_element(
                    By.CSS_SELECTOR,
                    "[data-testid='ticket-item-status']",
                ).text,
            )

            self.assertIn(
                answer,
                item.find_element(
                    By.CSS_SELECTOR,
                    "[data-testid='ticket-item-note']",
                ).text,
            )

        finally:
            # Remove only the ticket created by this test.
            SupportTicket.objects.filter(subject=subject).delete()

    # TC-130
    def test_tc130_the_sidebar_has_no_unfinished_items(self):
        login_as_demo(
            self.driver,
            self.wait,
            "CEO",
        )
        self.driver.get(f"{FRONTEND_URL}/dashboard")

        sidebar = self.css("[data-testid='sidebar']")

        # Sidebar.jsx renders group items even when their groups are closed.
        # Inspect the rendered navigation rather than clicking every group.
        sidebar_text = sidebar.get_attribute("textContent") or ""

        self.assertNotIn(
            "Soon",
            sidebar_text,
            "Sidebar should not contain unfinished items marked 'Soon'.",
        )

        # These links should not be rendered for the CEO role.
        for label in ("Projects", "Payroll", "Expenses"):
            self.assertEqual(
                sidebar.find_elements(
                    By.CSS_SELECTOR,
                    f"[data-testid='sidebar-link-{label}']",
                ),
                [],
                f"{label} should not appear in the CEO sidebar.",
            )

        # Help & Support must appear exactly once.
        self.assertEqual(
            len(
                sidebar.find_elements(
                    By.CSS_SELECTOR,
                    "[data-testid='sidebar-link-Help & Support']",
                )
            ),
            1,
            "Help & Support should appear exactly once.",
        )


if __name__ == "__main__":
    unittest.main()
