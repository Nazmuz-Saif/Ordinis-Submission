"""
ST-141 Selenium tests: My Profile page for Employees and Platform Admin.

  TC-97  [Selenium] Open My Profile as an Employee, change the phone number, save and reload
         — expect the new number and no way to edit the email.
  TC-98  [Selenium] Open My Profile as the Platform Admin — expect the name and contact fields
         and no company fields.

Needs both servers running.
Run:  cd backend && python tests/test_st141_selenium.py        (HEADLESS=1 hides the window)
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

from selenium_helpers import (  # noqa: E402
    DEMO_USERS,
    FRONTEND_URL,
    clear_session,
    login_as_demo,
    make_driver,
)

from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402


class ST141MyProfileSeleniumTest(unittest.TestCase):
    def setUp(self):
        self.driver, self.wait = make_driver()

    def tearDown(self):
        try:
            self.driver.get(f'{FRONTEND_URL}/login')
            clear_session(self.driver)
        except Exception:
            pass
        self.driver.quit()

    def _login(self, role='Employee'):
        try:
            self.driver.get(f'{FRONTEND_URL}/login')
            clear_session(self.driver)
        except Exception:
            pass
        login_as_demo(self.driver, self.wait, role)

    def test_tc97_employee_my_profile_update_phone_email_readonly(self):
        """TC-97: Open My Profile as Employee, change phone, save and reload -> new phone persisted, email uneditable."""
        self._login('Employee')
        self.driver.get(f"{FRONTEND_URL}/profile")
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='My Profile']")))

        # Verify email is read-only (rendered as display text, not an editable input)
        email_elem = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='profile-email']")))
        self.assertEqual(email_elem.tag_name, 'p', "Email must be rendered in read-only paragraph container")
        self.assertEqual(len(self.driver.find_elements(By.NAME, "email")), 0, "No editable email input should exist")

        # Edit phone number using React value tracker update
        phone_input = self.wait.until(EC.visibility_of_element_located((By.ID, "profile-phone")))
        new_phone = f"+880 1812-{int(time.time()) % 1000000:06d}"
        self.driver.execute_script("""
            const input = arguments[0];
            const val = arguments[1];
            const lastVal = input.value;
            input.value = val;
            const tracker = input._valueTracker;
            if (tracker) {
                tracker.setValue(lastVal);
            }
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
        """, phone_input, new_phone)

        # Wait until save button is no longer disabled (dirty=True) and click
        save_btn = self.wait.until(lambda d: d.find_element(By.CSS_SELECTOR, "[data-testid='profile-save']"))
        self.wait.until(lambda d: not save_btn.get_attribute("disabled"))
        self.driver.execute_script("arguments[0].click();", save_btn)

        # Wait for success notification
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='profile-success']")))

        # Reload page and assert new phone persisted
        self.driver.refresh()
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='My Profile']")))

        reloaded_phone_input = self.wait.until(EC.visibility_of_element_located((By.ID, "profile-phone")))
        self.assertEqual(reloaded_phone_input.get_attribute("value"), new_phone, "Reloaded phone should match saved value")
        self.assertEqual(len(self.driver.find_elements(By.NAME, "email")), 0, "Email must remain uneditable after reload")

    def test_tc98_platform_admin_my_profile_no_company_fields(self):
        """TC-98: Open My Profile as Platform Admin -> name & contact fields present, no company fields."""
        self._login('Platform Admin')
        self.driver.get(f"{FRONTEND_URL}/profile")
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='My Profile']")))

        # Platform admin should see full name input and email display
        name_input = self.wait.until(EC.visibility_of_element_located((By.ID, "profile-full_name")))
        self.assertTrue(name_input.is_displayed(), "Full name input should be present for Platform Admin")

        email_display = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='profile-email']")))
        self.assertTrue(email_display.is_displayed(), "Email display should be present for Platform Admin")
        self.assertEqual(email_display.text.strip(), DEMO_USERS['Platform Admin'])

        # Company fields (company name, department, employee code, designation, manager) should NOT be present
        company_elems = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='profile-company']")
        self.assertEqual(len(company_elems), 0, "Company field must NOT be present on Platform Admin profile")

        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        self.assertNotIn("Department", page_text, "Department label should not be present on Platform Admin profile")
        self.assertNotIn("Employee code", page_text, "Employee code should not be present on Platform Admin profile")
        self.assertNotIn("Reports to", page_text, "Reports to should not be present on Platform Admin profile")


if __name__ == '__main__':
    unittest.main(verbosity=2)
