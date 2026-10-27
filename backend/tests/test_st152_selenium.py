"""
ST-152 Selenium tests, TC-123 and TC-124: the Platform Admin's company detail page.

Needs the demo company (python manage.py seed_demo_data), the backend on :8000 and the frontend on :5173.
Run:  python -m unittest tests.test_st152_selenium     (from backend/, Chrome installed)
TC-124 uses its own small company ("Detail Test Corp"), so the demo company is never suspended.
"""
import os
import sys
import unittest
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / 'apps'))
sys.path.insert(0, str(BASE_DIR / 'tests'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

import django  # noqa: E402

django.setup()

from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402

from core import demo  # noqa: E402
from selenium_helpers import FRONTEND_URL, clear_session, login_as_demo, make_driver  # noqa: E402
from tenants.models import Company  # noqa: E402

TEST_SUBDOMAIN = 'detail-corp'


class ST152CompanyDetailSeleniumTest(unittest.TestCase):
    def setUp(self):
        self.driver, self.wait = make_driver()

    def tearDown(self):
        try:
            clear_session(self.driver)
        finally:
            self.driver.quit()

    def text(self, testid):
        return self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, f"[data-testid='{testid}']"))).text

    def test_tc123_open_a_company_detail_page(self):
        company = Company.objects.get(subdomain=demo.SUBDOMAIN)
        login_as_demo(self.driver, self.wait, 'Platform Admin')
        self.driver.get(f'{FRONTEND_URL}/admin/companies')
        link = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, f"//a[@data-testid='company-link'][normalize-space()='{company.name}']")))
        link.click()
        self.wait.until(EC.url_contains(f'/admin/companies/{company.id}'))
        self.assertEqual(self.text('company-name'), company.name)
        self.assertEqual(self.text('company-subdomain'), demo.SUBDOMAIN)
        self.assertEqual(self.text('company-status'), 'Active')
        self.assertEqual(self.text('owner-email'), demo.email('ceo'))
        self.assertEqual(self.text('owner-name'), demo.name('ceo'))
        self.assertEqual(self.text('plan-name').split(' ')[0], 'Basic')
        self.assertRegex(self.text('plan-days-left'), r'\d+ days?')
        self.assertTrue(self.text('plan-end'))
        self.assertRegex(self.text('size-text'), r'10 of 10')
        self.assertTrue(self.text('invoices-total').isdigit())
        self.assertTrue(self.text('tickets-open'))
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h2[normalize-space()='Recent platform actions']")))
        page = self.driver.find_element(By.TAG_NAME, 'body').text
        for local in ('nusrat.jahan', 'manager', 'imran.hossain', 'hr', 'accountant', 'employee', 'farhan.ahmed', 'mehedi.hasan', 'rafiq.islam'):
            self.assertNotIn(demo.name(local), page, f'{demo.name(local)} must not be on the page')
            self.assertNotIn(demo.email(local), page)

    def test_tc124_suspend_with_a_note_from_the_detail_page(self):
        company, _ = Company.objects.get_or_create(subdomain=TEST_SUBDOMAIN, defaults={'name': 'Detail Test Corp', 'is_active': True})
        Company.objects.filter(pk=company.pk).update(is_active=True)
        note = f'Payment overdue {uuid.uuid4().hex[:6]}'
        login_as_demo(self.driver, self.wait, 'Platform Admin')
        self.driver.get(f'{FRONTEND_URL}/admin/companies/{company.id}')
        self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='suspend-btn']"))).click()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='company-note']"))).send_keys(note)
        self.driver.find_element(By.CSS_SELECTOR, "[data-testid='confirm-btn']").click()
        self.wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, "[data-testid='company-status']"), 'Suspended'))
        self.assertIn(note, self.text('company-last-note'))
        rows = self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-testid='company-action-row']")))
        self.assertIn('Suspended', rows[0].text)
        self.assertIn(note, rows[0].text)
        self.assertFalse(Company.objects.get(pk=company.pk).is_active)
        self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='activate-btn']"))).click()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='company-note']"))).send_keys('Paid in full, active again')
        self.driver.find_element(By.CSS_SELECTOR, "[data-testid='confirm-btn']").click()
        self.wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, "[data-testid='company-status']"), 'Active'))
        self.assertTrue(Company.objects.get(pk=company.pk).is_active)


if __name__ == '__main__':
    unittest.main()
