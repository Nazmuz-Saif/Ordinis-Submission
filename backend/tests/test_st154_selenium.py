"""
ST-154 Selenium tests, TC-127 to TC-130: notes on suspend/activate, Request access, Help & Support, the sidebar.

Needs the demo company (python manage.py seed_demo_data), the backend on :8000 and the frontend on :5173.
Run:  python -m unittest tests.test_st154_selenium     (from backend/, Chrome installed)
TC-127 uses its own small company ("Note Test Corp"); TC-128 and TC-129 remove what they create.
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
from platform_admin.models import SupportAccessRequest, SupportTicket  # noqa: E402
from selenium_helpers import FRONTEND_URL, clear_session, login_as_demo, make_driver  # noqa: E402
from tenants.models import Company  # noqa: E402


class ST154SeleniumTest(unittest.TestCase):
    def setUp(self):
        self.driver, self.wait = make_driver()

    def tearDown(self):
        try:
            clear_session(self.driver)
        finally:
            self.driver.quit()

    def css(self, selector):
        return self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))

    def clickable(self, selector):
        return self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))

    def company_row(self, name):
        return self.wait.until(EC.visibility_of_element_located(
            (By.XPATH, f"//*[@data-testid='company-row'][.//a[normalize-space()='{name}']]")))

    def test_tc127_suspend_needs_a_note_and_the_note_shows_in_activity(self):
        company, _ = Company.objects.get_or_create(subdomain='note-corp', defaults={'name': 'Note Test Corp', 'is_active': True})
        Company.objects.filter(pk=company.pk).update(is_active=True)
        note = f'Unpaid invoice {uuid.uuid4().hex[:6]}'
        try:
            login_as_demo(self.driver, self.wait, 'Platform Admin')
            self.driver.get(f'{FRONTEND_URL}/admin/companies')
            self.company_row(company.name).find_element(By.CSS_SELECTOR, "[data-testid='suspend-btn']").click()
            self.css("[data-testid='company-note']")
            self.clickable("[data-testid='confirm-btn']").click()                     # no note
            self.assertIn('required', self.css("[role='alert']").text)
            self.driver.find_element(By.CSS_SELECTOR, "[data-testid='company-note']").send_keys('too short')
            self.driver.find_element(By.CSS_SELECTOR, "[data-testid='confirm-btn']").click()
            self.assertIn('at least 10', self.css("[role='alert']").text)
            self.assertTrue(Company.objects.get(pk=company.pk).is_active)             # nothing changed
            self.driver.find_element(By.CSS_SELECTOR, "[data-testid='company-note']").clear()
            self.driver.find_element(By.CSS_SELECTOR, "[data-testid='company-note']").send_keys(note)
            self.driver.find_element(By.CSS_SELECTOR, "[data-testid='confirm-btn']").click()
            self.assertIn('suspended', self.css("[data-testid='admin-message']").text.lower())
            self.assertFalse(Company.objects.get(pk=company.pk).is_active)
            self.driver.get(f'{FRONTEND_URL}/admin/activity')
            row = self.wait.until(EC.visibility_of_element_located(
                (By.XPATH, f"//*[@data-testid='activity-row'][contains(.,'{note}')]")))
            self.assertIn('Suspended', row.text)
        finally:
            Company.objects.filter(pk=company.pk).update(is_active=True)

    def test_tc128_request_access_from_the_companies_page(self):
        company = Company.objects.get(subdomain=demo.SUBDOMAIN)
        SupportAccessRequest.objects.filter(company=company, status='pending').delete()
        reason = f'Check bug {uuid.uuid4().hex[:6]}'
        try:
            login_as_demo(self.driver, self.wait, 'Platform Admin')
            self.driver.get(f'{FRONTEND_URL}/admin/companies')
            self.company_row(company.name).find_element(By.CSS_SELECTOR, "[data-testid='request-access-btn']").click()
            self.css("[data-testid='access-reason']").send_keys(reason)
            self.clickable("[data-testid='confirm-btn']").click()
            self.assertIn('Access request sent', self.css("[data-testid='admin-message']").text)
            self.driver.get(f'{FRONTEND_URL}/admin/access-requests')
            row = self.wait.until(EC.visibility_of_element_located(
                (By.XPATH, f"//*[@data-testid='request-row'][contains(.,'{reason}')]")))
            self.assertIn('Pending', row.text)
        finally:
            SupportAccessRequest.objects.filter(company=company, reason__startswith='Check bug').delete()

    def test_tc129_ticket_from_help_and_support_then_resolved_with_a_note(self):
        subject = f'Payslip is empty {uuid.uuid4().hex[:6]}'
        answer = 'Payslip generated again, please check'
        try:
            login_as_demo(self.driver, self.wait, 'Employee')
            self.driver.get(f'{FRONTEND_URL}/settings/help')
            self.css("[data-testid='ticket-subject']").send_keys(subject)
            self.driver.find_element(By.CSS_SELECTOR, "[data-testid='ticket-description']").send_keys('My payslip shows nothing for last month.')
            self.driver.find_element(By.CSS_SELECTOR, "[data-testid='ticket-submit']").click()
            self.css("[data-testid='ticket-sent']")
            item = self.wait.until(EC.visibility_of_element_located((By.XPATH, f"//*[@data-testid='ticket-item'][contains(.,'{subject}')]")))
            self.assertIn('Open', item.find_element(By.CSS_SELECTOR, "[data-testid='ticket-item-status']").text)

            clear_session(self.driver)
            login_as_demo(self.driver, self.wait, 'Platform Admin')
            self.driver.get(f'{FRONTEND_URL}/admin/tickets')
            row = self.wait.until(EC.visibility_of_element_located((By.XPATH, f"//*[@data-testid='ticket-row'][contains(.,'{subject}')]")))
            row.find_element(By.CSS_SELECTOR, "[data-testid='resolve-btn']").click()
            self.css("[data-testid='resolution-note']").send_keys(answer)
            self.clickable("[data-testid='confirm-btn']").click()
            self.wait.until(EC.visibility_of_element_located(
                (By.XPATH, f"//*[@data-testid='ticket-row'][contains(.,'{subject}')]//*[@data-testid='ticket-resolution']")))

            clear_session(self.driver)
            login_as_demo(self.driver, self.wait, 'Employee')
            self.driver.get(f'{FRONTEND_URL}/settings/help')
            item = self.wait.until(EC.visibility_of_element_located((By.XPATH, f"//*[@data-testid='ticket-item'][contains(.,'{subject}')]")))
            self.assertIn('Resolved', item.find_element(By.CSS_SELECTOR, "[data-testid='ticket-item-status']").text)
            self.assertIn(answer, item.find_element(By.CSS_SELECTOR, "[data-testid='ticket-item-note']").text)
        finally:
            SupportTicket.objects.filter(subject__startswith='Payslip is empty').delete()

    def test_tc130_the_sidebar_has_no_unfinished_items(self):
        login_as_demo(self.driver, self.wait, 'CEO')
        self.driver.get(f'{FRONTEND_URL}/dashboard')
        sidebar = self.css("[data-testid='sidebar']")
        for group in self.driver.find_elements(By.CSS_SELECTOR, "[data-testid^='sidebar-group-'][aria-expanded]"):
            if group.get_attribute('aria-expanded') != 'true':
                group.click()
        text = sidebar.text
        self.assertNotIn('Soon', text)
        for label in ('Projects', 'Payroll', 'Expenses'):
            self.assertEqual(self.driver.find_elements(By.CSS_SELECTOR, f"[data-testid='sidebar-link-{label}']"), [], label)
        self.assertEqual(len(self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='sidebar-link-Help & Support']")), 1)


if __name__ == '__main__':
    unittest.main()
