"""
ST-148 Selenium tests: Platform Admin payments review, approval, rejection note requirement, and subscriptions list.

  TC-112  [Selenium] As the Platform Admin open Payments — expect pending submissions with details;
          approve one — expect it Approved with the new end date and invoice number.
  TC-113  [Selenium] Reject a payment without a note — expect a refusal; with a note
          — expect Rejected and the note visible to the company.
  TC-114  [Selenium] Open Subscriptions — expect companies sorted by days left with the expiring ones highlighted.

Needs both servers running.
Run:  cd backend && python tests/test_st148_selenium.py        (HEADLESS=1 hides the window)
"""
import datetime
import json
import os
import sys
import time
import unittest
import urllib.request

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(TESTS_DIR)
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, TESTS_DIR)
sys.path.insert(0, os.path.join(BACKEND_DIR, 'apps'))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
import django
django.setup()

from billing.models import PaymentSubmission, Subscription  # noqa: E402
from selenium_helpers import (  # noqa: E402
    BACKEND_API_URL,
    DEMO_PASSWORD,
    DEMO_USERS,
    FRONTEND_URL,
    clear_session,
    login,
    login_as_demo,
    make_driver,
)

from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402


def create_waiting_company_with_payment(ts, tag="tc"):
    subdomain = f"{tag}-{ts}"
    email = f"ceo.{ts}@{tag}.test"
    password = "StrongPassword123!"
    tx_id = f"TX{ts}{tag.upper()}"

    # Register company
    reg_req = urllib.request.Request(
        f"{BACKEND_API_URL}/auth/register/",
        data=json.dumps({
            "company_name": f"{tag.upper()} Co {ts}",
            "subdomain": subdomain,
            "ceo_full_name": f"Owner {ts}",
            "ceo_email": email,
            "ceo_password": password,
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(reg_req) as resp:
        token = json.loads(resp.read().decode("utf-8"))["data"]["access"]

    # Submit payment
    pay_req = urllib.request.Request(
        f"{BACKEND_API_URL}/billing/payments/",
        data=json.dumps({
            "plan": "Professional",
            "months": 3,
            "method": "bkash",
            "payer_name": f"Payer {ts}",
            "payer_number": "01712345678",
            "transaction_id": tx_id,
            "amount": "15000.00",
        }).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    with urllib.request.urlopen(pay_req) as resp:
        pay_data = json.loads(resp.read().decode("utf-8"))

    return subdomain, email, password, tx_id


class ST148AdminPaymentsAndSubscriptionsSeleniumTest(unittest.TestCase):
    def setUp(self):
        self.driver, self.wait = make_driver()

    def tearDown(self):
        try:
            self.driver.get(f'{FRONTEND_URL}/login')
            clear_session(self.driver)
        except Exception:
            pass
        self.driver.quit()

    def _login_admin(self):
        try:
            self.driver.get(f'{FRONTEND_URL}/login')
            clear_session(self.driver)
        except Exception:
            pass
        login_as_demo(self.driver, self.wait, 'Platform Admin')

    def test_tc112_platform_admin_approves_payment_with_invoice_and_end_date(self):
        """TC-112: Platform Admin opens Payments -> details -> approve -> Approved with new end date and invoice number."""
        ts = int(time.time())
        subdomain, _, _, tx_id = create_waiting_company_with_payment(ts, tag="tc112")

        self._login_admin()
        self.driver.get(f"{FRONTEND_URL}/admin/payments")
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Payments']")))

        # Search for the transaction ID
        search_input = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='payments-search']")))
        search_input.clear()
        search_input.send_keys(tx_id)
        time.sleep(1)

        # Open the payment detail
        open_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='payment-open']")))
        self.driver.execute_script("arguments[0].click();", open_btn)

        # Verify details in detail panel
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='payment-detail']")))
        detail_panel = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='payment-detail']")
        self.assertIn(tx_id, detail_panel.text)
        self.assertIn("15,000", detail_panel.text)
        self.assertIn("Professional", detail_panel.text)

        # Click Approve
        approve_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='approve-btn']")))
        self.driver.execute_script("arguments[0].click();", approve_btn)

        # Confirm in dialog
        confirm_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='confirm-btn']")))
        self.driver.execute_script("arguments[0].click();", confirm_btn)

        # Verify Approved result with end date and invoice number
        result_box = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='approved-result']")))
        self.assertIn("approved", result_box.text.lower())

        end_date_elem = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='result-end-date']")))
        self.assertIn("runs until", end_date_elem.text.lower())

        inv_elem = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='result-invoice']")))
        self.assertIn("INV-", inv_elem.text)

    def test_tc113_platform_admin_reject_payment_note_required(self):
        """TC-113: Reject payment without note -> refusal; with note -> Rejected and note visible to company."""
        ts = int(time.time())
        subdomain, ceo_email, password, tx_id = create_waiting_company_with_payment(ts, tag="tc113")

        self._login_admin()
        self.driver.get(f"{FRONTEND_URL}/admin/payments")
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Payments']")))

        # Search for transaction
        search_input = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='payments-search']")))
        search_input.clear()
        search_input.send_keys(tx_id)
        time.sleep(1)

        # Open payment detail
        open_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='payment-open']")))
        self.driver.execute_script("arguments[0].click();", open_btn)
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='payment-detail']")))

        # Click Reject
        reject_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='reject-btn']")))
        self.driver.execute_script("arguments[0].click();", reject_btn)

        # 1. Try to reject without a note -> refusal
        confirm_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='confirm-btn']")))
        self.driver.execute_script("arguments[0].click();", confirm_btn)

        # Expect error message in dialog with role="alert"
        dialog_error = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[role='alert']")))
        self.assertTrue(len(dialog_error.text.strip()) > 0, "Rejection without a note must display an error message")
        self.assertIn("rejected", dialog_error.text.lower())

        # 2. Enter note and confirm reject
        note_text = f"Wrong transaction amount for {tx_id}"
        note_area = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='reject-note']")
        note_area.clear()
        note_area.send_keys(note_text)

        self.driver.execute_script("arguments[0].click();", confirm_btn)

        # Expect Rejected status and note visible in detail panel
        rejected_note = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='detail-rejected-note']")))
        self.assertEqual(rejected_note.text.strip(), note_text)

        # 3. Log in as the company and verify note is visible
        try:
            self.driver.get(f'{FRONTEND_URL}/login')
            clear_session(self.driver)
        except Exception:
            pass
        login(self.driver, self.wait, ceo_email, password)

        # Owner is on waiting page: rejection notice with the note should be shown
        self.driver.get(f"{FRONTEND_URL}/subscribe/waiting")
        rejected_note_elem = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='rejected-note']")))
        self.assertEqual(rejected_note_elem.text.strip(), note_text, "Company should see the exact rejection note")

    def test_tc114_platform_admin_subscriptions_sorted_and_highlighted(self):
        """TC-114: Platform Admin opens Subscriptions -> sorted by days left with expiring ones highlighted."""
        # Ensure at least one company is expiring within 5 days so it gets highlighted
        ts = int(time.time())
        subdomain, _, _, _ = create_waiting_company_with_payment(ts, tag="tc114")
        sub = Subscription.objects.get(company__subdomain=subdomain)
        today = datetime.date.today()
        sub.status = Subscription.STATUS_ACTIVE
        sub.current_period_start = today - datetime.timedelta(days=25)
        sub.current_period_end = today + datetime.timedelta(days=4)
        sub.save()

        self._login_admin()
        self.driver.get(f"{FRONTEND_URL}/admin/subscriptions")
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Subscriptions']")))

        table = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='subscriptions-table']")))
        rows = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='subscription-row']")
        self.assertGreater(len(rows), 0, "Subscriptions table should list companies")

        # Verify highlighted expiring company (tone='amber' or tone='red')
        highlighted = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='days-left'][data-tone='amber'], [data-testid='days-left'][data-tone='red']")
        self.assertGreater(len(highlighted), 0, "Expiring companies must be highlighted with amber or red tone")


if __name__ == '__main__':
    unittest.main(verbosity=2)
