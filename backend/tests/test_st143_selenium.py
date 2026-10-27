"""
ST-143 Selenium tests: Employee detail page privacy and role permissions.

  TC-102  [Selenium] As the CEO open an Employee's detail page — expect the full profile
          and the Permissions grouped by module under each Role.
  TC-103  [Selenium] As an Employee open a colleague outside my reporting line — expect
          name and designation only, with no phone, address or salary.

Needs the demo company and both servers running.
Run:  cd backend && python tests/test_st143_selenium.py        (HEADLESS=1 hides the window)
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

from organization.models import Employee  # noqa: E402
from selenium_helpers import (  # noqa: E402
    DEMO_USERS,
    FRONTEND_URL,
    clear_session,
    login_as_demo,
    make_driver,
)

from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402


class ST143EmployeeDetailSeleniumTest(unittest.TestCase):
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

    def test_tc102_ceo_opens_employee_detail_page_roles_and_permissions(self):
        """TC-102: CEO opens Employee detail page -> full profile and Permissions grouped by module under each Role."""
        # Get manager employee who has roles and permissions assigned
        manager_emp = Employee.objects.filter(
            company__subdomain='demo-acme',
            user__email=DEMO_USERS['Manager']
        ).first()
        self.assertIsNotNone(manager_emp, "Manager employee should exist in demo company")

        self._login('CEO')
        self.driver.get(f"{FRONTEND_URL}/organization/employees/{manager_emp.id}")

        # Verify employee name is displayed
        name_elem = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='employee-name']")))
        self.assertIn("Tanvir Rahman", name_elem.text)

        # Full profile details: email and phone visible
        email_elem = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='detail-email']")))
        self.assertEqual(email_elem.text.strip(), DEMO_USERS['Manager'])

        phone_elems = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='detail-phone']")
        self.assertTrue(len(phone_elems) > 0, "CEO must see employee phone number")
        self.assertTrue(bool(phone_elems[0].text.strip()), "Phone number must not be empty")

        # Roles and Permissions section
        perm_section = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='permissions-section']")))
        self.assertIn("Roles and Permissions", perm_section.text)

        # Role block and module groups under role
        role_blocks = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='role-block']")
        self.assertGreaterEqual(len(role_blocks), 1, "At least one role block must be shown")

        # Verify permissions grouped by module
        perm_text = perm_section.text
        # Module headers are uppercase, e.g. ORGANIZATION, ATTENDANCE, PAYROLL
        self.assertTrue(
            any(module in perm_text for module in ["ORGANIZATION", "ATTENDANCE", "PAYROLL", "ROLES", "WORKFLOW", "TASKS"]),
            f"Permissions should be grouped by module in permissions section: {perm_text}"
        )

    def test_tc103_employee_opens_colleague_outside_reporting_line(self):
        """TC-103: Employee opens colleague outside reporting line -> name and designation only, no phone, address or salary."""
        # Rafiq Islam (Sales) is outside Ayesha Siddiqua's (Engineering) reporting line
        rafiq_emp = Employee.objects.filter(
            company__subdomain='demo-acme',
            user__email__startswith='rafiq.islam'
        ).first()
        self.assertIsNotNone(rafiq_emp, "Rafiq Islam should exist in demo company")

        self._login('Employee')
        self.driver.get(f"{FRONTEND_URL}/organization/employees/{rafiq_emp.id}")

        # Name and designation are displayed
        name_elem = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='employee-name']")))
        self.assertIn("Rafiq Islam", name_elem.text)

        body_text = self.driver.find_element(By.TAG_NAME, "body").text
        self.assertIn("Sales Executive", body_text)

        # Privacy checks: no phone, address, salary, or permissions section
        phone_elems = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='detail-phone']")
        self.assertEqual(len(phone_elems), 0, "Phone number must NOT be visible to colleague outside reporting line")

        addr_elems = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='detail-address']")
        self.assertEqual(len(addr_elems), 0, "Address must NOT be visible to colleague outside reporting line")

        salary_elems = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='salary-section']")
        self.assertEqual(len(salary_elems), 0, "Salary section must NOT be visible to colleague outside reporting line")

        perm_elems = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='permissions-section']")
        self.assertEqual(len(perm_elems), 0, "Permissions section must NOT be visible to colleague outside reporting line")

        # Contact private note is shown
        note_elems = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='contact-private-note']")
        self.assertGreaterEqual(len(note_elems), 1, "Contact private note should be displayed")


if __name__ == '__main__':
    unittest.main(verbosity=2)
