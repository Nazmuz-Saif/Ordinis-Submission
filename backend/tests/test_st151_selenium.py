"""
ST-151 Selenium tests, TC-121 and TC-122: change plan with an upgrade payment.

Needs the demo company (python manage.py seed_demo_data), the backend on :8000 and the frontend on :5173.
Run:  python -m unittest tests.test_st151_selenium     (from backend/, Chrome installed)
The test puts the demo company back on Basic and removes what it created.
"""
import os
import re
import sys
import unittest
import uuid
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / 'tests'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

import django  # noqa: E402

django.setup()

from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402

from selenium_helpers import FRONTEND_URL, clear_session, login_as_demo, make_driver  # noqa: E402


def number_in(text):
    """'BDT 1,234.00' -> Decimal('1234.00')"""
    return Decimal(re.sub(r'[^0-9.]', '', text) or '0')


class ST151ChangePlanSeleniumTest(unittest.TestCase):
    def setUp(self):
        from billing import services
        from billing.models import Invoice, PaymentSubmission, Subscription
        from tenants.models import Company
        from core import demo

        self.services, self.Invoice, self.Payment, self.Subscription = services, Invoice, PaymentSubmission, Subscription
        self.company = Company.objects.get(subdomain=demo.SUBDOMAIN)
        sub = Subscription.objects.get(company=self.company)
        self.original = (sub.plan_id, sub.current_period_end, sub.next_plan_id, sub.next_plan_from)
        PaymentSubmission.objects.filter(company=self.company, status=PaymentSubmission.STATUS_PENDING).delete()
        self.driver, self.wait = make_driver()

    def tearDown(self):
        try:
            clear_session(self.driver)
        finally:
            self.driver.quit()
        Subscription = self.Subscription
        self.Payment.objects.filter(company=self.company, transaction_id__startswith='SEL151').delete()
        self.Invoice.objects.filter(company=self.company, kind=self.Invoice.KIND_UPGRADE).delete()
        plan_id, end, next_plan_id, next_from = self.original
        Subscription.objects.filter(company=self.company).update(
            plan_id=plan_id, current_period_end=end, next_plan_id=next_plan_id, next_plan_from=next_from,
        )

    def sub(self):
        return self.Subscription.objects.select_related('plan').get(company=self.company)

    def open_quote(self):
        login_as_demo(self.driver, self.wait, 'CEO')
        self.driver.get(f'{FRONTEND_URL}/settings/billing/change-plan')
        self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='plan-upgrade-Professional']"))).click()
        return self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='upgrade-quote']")))

    def test_tc121_choose_professional_shows_the_extra_amount_and_keeps_the_end_date(self):
        sub = self.sub()
        self.assertEqual(sub.plan.name, 'Basic', 'The demo company must be on Basic.')
        self.open_quote()
        days = int(self.driver.find_element(By.CSS_SELECTOR, "[data-testid='upgrade-days-left']").text)
        diff = Decimal('5000') - Decimal('1500')
        expected = (diff * days / 30).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        shown = number_in(self.driver.find_element(By.CSS_SELECTOR, "[data-testid='upgrade-amount']").text)
        self.assertEqual(shown, expected)
        self.assertEqual(self.driver.find_element(By.CSS_SELECTOR, "[data-testid='upgrade-target']").text, 'Professional')
        end_text = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='upgrade-end-date']").text
        self.assertRegex(end_text, rf'\b{sub.current_period_end.day}\b.*\b{sub.current_period_end.year}\b')
        self.assertIn('end date does not change', self.driver.find_element(By.TAG_NAME, 'body').text)
        self.assertEqual(self.sub().current_period_end, sub.current_period_end)      # a quote saves nothing
        self.assertEqual(self.sub().plan.name, 'Basic')

    def test_tc122_pay_then_platform_admin_approves_the_upgrade(self):
        before = self.sub()
        end_before = before.current_period_end
        self.open_quote()
        amount = number_in(self.driver.find_element(By.CSS_SELECTOR, "[data-testid='upgrade-amount']").text)
        tx = f'SEL151{uuid.uuid4().hex[:8].upper()}'
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='payment-form']")))
        self.driver.find_element(By.CSS_SELECTOR, "[data-testid='payer-name']").send_keys('Demo Owner')
        self.driver.find_element(By.CSS_SELECTOR, "[data-testid='payer-number']").send_keys('01700000000')
        self.driver.find_element(By.CSS_SELECTOR, "[data-testid='transaction-id']").send_keys(tx)
        self.driver.find_element(By.CSS_SELECTOR, "[data-testid='payment-submit']").click()
        self.wait.until(EC.url_contains('/settings/billing'))
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='renewal-pending-banner']")))
        pending = self.Payment.objects.get(company=self.company, transaction_id=tx)
        self.assertEqual((pending.kind, pending.status, pending.plan.name, pending.amount), ('upgrade', 'pending', 'Professional', amount))
        self.assertEqual(self.sub().plan.name, 'Basic')           # nothing changes before approval

        clear_session(self.driver)
        login_as_demo(self.driver, self.wait, 'Platform Admin')
        self.driver.get(f'{FRONTEND_URL}/admin/payments')
        search = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='payments-search']")))
        search.send_keys(tx)
        self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='payment-open']"))).click()
        self.assertIn('upgrade', self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='detail-kind']"))).text.lower())
        self.driver.find_element(By.CSS_SELECTOR, "[data-testid='approve-btn']").click()
        self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='confirm-btn']"))).click()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='payments-message']")))

        after = self.sub()
        self.assertEqual(after.plan.name, 'Professional')
        self.assertEqual(after.current_period_end, end_before)
        invoice = self.Invoice.objects.get(company=self.company, kind=self.Invoice.KIND_UPGRADE)
        self.assertEqual((invoice.amount, invoice.status), (amount, self.Invoice.STATUS_PAID))
        self.assertEqual(self.services.usage(self.company.__class__.objects.get(pk=self.company.pk))['limit'], 50)


if __name__ == '__main__':
    unittest.main()
