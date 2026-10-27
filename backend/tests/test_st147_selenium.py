"""
ST-147 Selenium tests: Registration payment flow, waiting page gate, platform admin approval and dashboard access.

  TC-110  [Selenium] Register a new company, choose Professional for 3 months and submit a bKash payment
          — expect the waiting page and no access to the dashboard.
  TC-111  [Selenium] As the Platform Admin approve that payment, then as the new owner reload
          — expect the dashboard and a paid invoice for 3 times the monthly price less any discount.

Needs both servers running.
Run:  cd backend && python tests/test_st147_selenium.py        (HEADLESS=1 hides the window)
"""
import os
import sys
import time
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(TESTS_DIR)
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, TESTS_DIR)
sys.path.insert(0, os.path.join(BACKEND_DIR, 'apps'))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
import django
django.setup()

from accounts.models import User  # noqa: E402
from billing import services  # noqa: E402
from billing.models import Invoice, PaymentSubmission, Subscription  # noqa: E402
from selenium_helpers import (  # noqa: E402
    FRONTEND_URL,
    clear_session,
    make_driver,
)

from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402


class ST147RegistrationFlowSeleniumTest(unittest.TestCase):
    def setUp(self):
        self.driver, self.wait = make_driver()

    def tearDown(self):
        try:
            self.driver.get(f'{FRONTEND_URL}/login')
            clear_session(self.driver)
        except Exception:
            pass
        self.driver.quit()

    def _register_and_submit_payment(self, ts, prefix="apex"):
        company_name = f"{prefix.capitalize()} Labs {ts}"
        subdomain = f"{prefix}-{ts}"
        full_name = f"Founder {ts}"
        email = f"ceo.{ts}@{prefix}.test"
        password = "StrongPassword123!"
        txn_id = f"BK{ts}TX"

        # 1. Register
        self.driver.get(f"{FRONTEND_URL}/register")
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Create your company']")))

        self.driver.find_element(By.NAME, "company_name").send_keys(company_name)
        sub_elem = self.driver.find_element(By.NAME, "subdomain")
        sub_elem.clear()
        sub_elem.send_keys(subdomain)
        self.driver.find_element(By.NAME, "ceo_full_name").send_keys(full_name)
        self.driver.find_element(By.NAME, "ceo_email").send_keys(email)
        self.driver.find_element(By.NAME, "ceo_password").send_keys(password)
        self.driver.find_element(By.XPATH, "//button[@type='submit'][contains(., 'Create company')]").click()

        # 2. Plan page
        self.wait.until(lambda d: "/subscribe" in d.current_url)
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Choose your plan']")))

        pro_card = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='plan-card-professional']")))
        self.driver.execute_script("arguments[0].click();", pro_card)

        three_mo_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='months-option-3']")))
        self.driver.execute_script("arguments[0].click();", three_mo_btn)
        time.sleep(1)

        next_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='plan-next']")))
        self.driver.execute_script("arguments[0].click();", next_btn)

        # 3. Pay page
        self.wait.until(lambda d: "/subscribe/pay" in d.current_url)
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='payment-form']")))

        payer_name = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='payer-name']")
        payer_name.clear()
        payer_name.send_keys("Owner Payer")

        payer_number = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='payer-number']")
        payer_number.clear()
        payer_number.send_keys("01712345678")

        txn_input = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='transaction-id']")
        txn_input.clear()
        txn_input.send_keys(txn_id)

        submit_btn = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='payment-submit']")
        self.driver.execute_script("arguments[0].click();", submit_btn)

        # 4. Waiting page
        self.wait.until(lambda d: "/subscribe/waiting" in d.current_url)
        return subdomain, email, password, txn_id

    def test_tc110_register_company_pro_plan_bkash_waiting_page(self):
        """TC-110: Register company -> Professional 3 months -> submit bKash -> waiting page, no dashboard access."""
        ts = int(time.time())
        subdomain, _, _, _ = self._register_and_submit_payment(ts, prefix="tc110")

        waiting_card = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='waiting-card']")))
        self.assertIn("waiting for approval", waiting_card.text.lower())
        self.assertIn("professional", waiting_card.text.lower())
        self.assertIn("15,000", waiting_card.text)

        # Verify dashboard access blocked
        self.driver.get(f"{FRONTEND_URL}/dashboard")
        time.sleep(1)
        self.assertTrue(
            "/subscribe" in self.driver.current_url,
            f"Access to dashboard must be blocked, url: {self.driver.current_url}"
        )

    def test_tc111_platform_admin_approves_payment_dashboard_unlocked(self):
        """TC-111: Platform Admin approves payment -> owner reloads -> dashboard opens, paid invoice for 15,000 BDT."""
        ts = int(time.time())
        subdomain, _, _, txn_id = self._register_and_submit_payment(ts, prefix="tc111")

        # Admin approves payment
        payment = PaymentSubmission.objects.get(transaction_id=txn_id)
        admin_user = User.objects.filter(is_platform_admin=True).first()
        services.approve_payment(payment, admin_user)

        # Owner reloads
        self.driver.get(f"{FRONTEND_URL}/dashboard")
        time.sleep(2)
        self.assertNotIn("/subscribe", self.driver.current_url, f"Dashboard should be unlocked, url: {self.driver.current_url}")

        # Check Billing page for paid invoice
        self.driver.get(f"{FRONTEND_URL}/settings/billing")
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Billing']")))

        invoices_table = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='billing-invoices']")))
        table_text = invoices_table.text
        self.assertIn("15,000", table_text)
        self.assertIn("Paid", table_text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
