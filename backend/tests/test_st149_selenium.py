"""
ST-149 Selenium tests: Billing timeline, invoice detail & tenant isolation, renewal invoice and pending payment banner.

  TC-115  [Selenium] Open Billing as the CEO — expect the timeline with days left, the end date, the status and the invoice list.
  TC-116  [Selenium] Open an invoice — expect its full detail with payment method and transaction id;
          open another company's invoice address — expect not found.
  TC-117  [Selenium] For a company 5 days from its end — expect Expiring soon and a renewal invoice,
          and after submitting the payment a pending banner.

Needs both servers running.
Run:  cd backend && python tests/test_st149_selenium.py        (HEADLESS=1 hides the window)
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

from django.core.management import call_command  # noqa: E402
from billing.models import Invoice, Subscription  # noqa: E402
from tenants.models import Company  # noqa: E402
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


def api_register_company(name, subdomain, email, password="StrongPass123", full_name="Test Owner"):
    req = urllib.request.Request(
        f"{BACKEND_API_URL}/auth/register/",
        data=json.dumps({
            "company_name": name,
            "subdomain": subdomain,
            "ceo_full_name": full_name,
            "ceo_email": email,
            "ceo_password": password,
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


class ST149BillingAndInvoicesSeleniumTest(unittest.TestCase):
    def setUp(self):
        self.driver, self.wait = make_driver()

    def tearDown(self):
        try:
            self.driver.get(f'{FRONTEND_URL}/login')
            clear_session(self.driver)
        except Exception:
            pass
        self.driver.quit()

    def _login(self, role):
        try:
            self.driver.get(f'{FRONTEND_URL}/login')
            clear_session(self.driver)
        except Exception:
            pass
        login_as_demo(self.driver, self.wait, role)

    def test_tc115_ceo_billing_page_timeline_and_invoices(self):
        """TC-115: Open Billing as CEO -> timeline with days left, end date, status and invoices list."""
        self._login('CEO')
        self.driver.get(f"{FRONTEND_URL}/settings/billing")
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Billing']")))

        # Timeline card
        timeline = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='timeline-card']")))
        self.assertIsNotNone(timeline)

        # Days left, ends date, and status
        days_elem = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='timeline-days']")))
        self.assertTrue(len(days_elem.text.strip()) > 0, "Days left should have text")

        end_elem = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='timeline-end']")))
        self.assertTrue(len(end_elem.text.strip()) > 0, "End date should have text")

        status_elem = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='timeline-status']")))
        self.assertTrue(len(status_elem.text.strip()) > 0, "Timeline status should have text")

        # Invoices list
        invoices_table = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='billing-invoices']")))
        self.assertIsNotNone(invoices_table)

    def test_tc116_invoice_detail_and_cross_company_isolation(self):
        """TC-116: Open invoice -> full detail with method and txn id; open other company invoice -> not found."""
        self._login('CEO')
        self.driver.get(f"{FRONTEND_URL}/settings/billing")
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Billing']")))

        # Ensure demo invoice has payment method and transaction ID
        demo_invoice = Invoice.objects.filter(company__subdomain='demo-acme').first()
        if not demo_invoice:
            demo_co = Company.objects.get(subdomain='demo-acme')
            demo_sub = Subscription.objects.get(company=demo_co)
            demo_invoice = Invoice.objects.create(
                company=demo_co,
                subscription=demo_sub,
                number="INV-2026-99001",
                amount=15000,
                status=Invoice.STATUS_PAID,
                plan_name="Professional",
                months=3,
                period_start=datetime.date.today(),
                period_end=datetime.date.today() + datetime.timedelta(days=90),
                issued_on=datetime.date.today(),
                due_on=datetime.date.today(),
                paid_on=datetime.date.today(),
                payment_method="bkash",
                transaction_id="DEMOBKASH99001",
            )
        else:
            demo_invoice.payment_method = 'bkash'
            demo_invoice.transaction_id = 'DEMOBKASH99001'
            demo_invoice.status = Invoice.STATUS_PAID
            demo_invoice.save()

        # 1. Open the demo invoice detail page
        self.driver.get(f"{FRONTEND_URL}/settings/billing/invoices/{demo_invoice.id}")
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='invoice-detail']")))

        method_elem = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='invoice-detail-method']")))
        self.assertIn("bkash", method_elem.text.lower(), "Invoice method must show bKash")

        tx_elem = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='invoice-detail-transaction']")))
        self.assertEqual(tx_elem.text.strip(), "DEMOBKASH99001", "Invoice transaction ID must match")

        # 2. Cross-company isolation: create an invoice for another company
        other_co = Company.objects.exclude(subdomain='demo-acme').first()
        self.assertIsNotNone(other_co, "Another company must exist in database")
        other_sub = Subscription.objects.filter(company=other_co).first()

        other_invoice = Invoice.objects.create(
            company=other_co,
            subscription=other_sub,
            number=f"INV-OTHER-{int(time.time())}",
            amount=5000,
            status=Invoice.STATUS_PAID,
            plan_name="Basic",
            months=1,
            period_start=datetime.date.today(),
            period_end=datetime.date.today() + datetime.timedelta(days=30),
            issued_on=datetime.date.today(),
            due_on=datetime.date.today(),
            paid_on=datetime.date.today(),
            payment_method="bkash",
            transaction_id=f"OTHERTX{int(time.time())}",
        )

        # Attempt to open other company's invoice
        self.driver.get(f"{FRONTEND_URL}/settings/billing/invoices/{other_invoice.id}")

        # Expect invoice-not-found
        not_found = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='invoice-not-found']")))
        self.assertIn("invoice not found", not_found.text.lower())

    def test_tc117_expiring_soon_renewal_invoice_and_pending_banner(self):
        """TC-117: Company 5 days from end -> Expiring soon, renewal invoice, and pending banner after payment."""
        ts = int(time.time())
        subdomain = f"tc117-{ts}"
        ceo_email = f"ceo.{ts}@tc117.test"
        password = "StrongPassword123!"
        txn_id = f"RENEW{ts}TX"

        api_register_company(f"Expiring Co {ts}", subdomain, ceo_email, password=password, full_name="Renewal Owner")

        today = datetime.date.today()
        sub = Subscription.objects.get(company__subdomain=subdomain)
        sub.status = Subscription.STATUS_ACTIVE
        sub.current_period_start = today - datetime.timedelta(days=25)
        sub.current_period_end = today + datetime.timedelta(days=5)  # 5 days left
        sub.billing_months = 1
        sub.reminders_sent = []
        sub.save()

        # Run process_subscriptions so renewal invoice is generated
        call_command('process_subscriptions')

        # Log in as the company CEO
        login(self.driver, self.wait, ceo_email, password)

        # 1. Open Billing page
        self.driver.get(f"{FRONTEND_URL}/settings/billing")
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Billing']")))

        # Verify Expiring soon status in timeline card
        timeline_status = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='timeline-status']")))
        self.assertIn("expiring soon", timeline_status.text.lower(), f"Status should show expiring soon: {timeline_status.text}")

        # Verify a renewal invoice is listed
        invoices_elem = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='billing-invoices']")))
        self.assertTrue("Due" in invoices_elem.text or "Open" in invoices_elem.text or "INV-" in invoices_elem.text)

        # 2. Click Renew button
        renew_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='renew-btn']")))
        self.driver.execute_script("arguments[0].click();", renew_btn)

        # Lands on /settings/billing/renew
        self.wait.until(lambda d: "/settings/billing/renew" in d.current_url)
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='payment-form']")))

        # Fill and submit payment
        payer_name = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='payer-name']")
        payer_name.clear()
        payer_name.send_keys("Renewal Payer")

        payer_number = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='payer-number']")
        payer_number.clear()
        payer_number.send_keys("01712345678")

        txn_input = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='transaction-id']")
        txn_input.clear()
        txn_input.send_keys(txn_id)

        submit_btn = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='payment-submit']")
        self.driver.execute_script("arguments[0].click();", submit_btn)

        # Form redirects back to /settings/billing
        self.wait.until(lambda d: d.current_url.endswith("/settings/billing") or "/settings/billing" in d.current_url)

        # 3. Verify pending banner is displayed
        pending_banner = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='renewal-pending-banner']")))
        self.assertIn("waiting for approval", pending_banner.text.lower())
        self.assertIn(txn_id, pending_banner.text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
