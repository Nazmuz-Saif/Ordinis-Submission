"""
ST-144 Selenium tests: Team Attendance view, hierarchy filtering, and menu visibility.

  TC-104  [Selenium] As the CEO pick an employee in Team Attendance — expect that
          person's calendar, cards and a table of check-in and check-out times.
  TC-105  [Selenium] As a Department Head open Team Attendance — expect only the people
          in the team in the dropdown; as a plain Employee expect no menu item.

Needs the demo company and both servers running.
Run:  cd backend && python tests/test_st144_selenium.py        (HEADLESS=1 hides the window)
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


class ST144TeamAttendanceSeleniumTest(unittest.TestCase):
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

    def test_tc104_ceo_picks_employee_in_team_attendance(self):
        """TC-104: As CEO pick an employee in Team Attendance -> calendar, metric cards, check-in/out table."""
        self._login('CEO')
        self.driver.get(f"{FRONTEND_URL}/attendance/team")

        # Verify page header
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Team Attendance']")))

        # Open employee dropdown
        picker_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='team-employee-select']")))
        picker_btn.click()

        # Wait for options and pick the first available employee
        options = self.wait.until(EC.visibility_of_all_elements_located((
            By.CSS_SELECTOR, "[data-testid^='team-employee-option-']"
        )))
        self.assertGreater(len(options), 0, "CEO should see employee options in the team picker")
        options[0].click()

        # Verify team attendance view appears
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='team-attendance-view']")))

        # Verify metric cards for Days present and Total hours
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='team-card-days']")))
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='team-card-hours']")))

        # Verify calendar component is present
        calendar_elem = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='attendance-calendar'], .grid")))
        self.assertIsNotNone(calendar_elem)

        # Verify days worked table with check-in and check-out headers
        table_container = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='team-day-table']")))
        self.assertIn("Days worked", table_container.text)
        table = table_container.find_element(By.TAG_NAME, "table")
        header_text = table.find_element(By.TAG_NAME, "thead").text
        self.assertIn("Check-in", header_text)
        self.assertIn("Check-out", header_text)

    def test_tc105_department_head_vs_plain_employee_team_attendance(self):
        """TC-105: Department Head sees only team subordinates; plain employee has no Team Attendance menu item."""
        # 1. Department Head (Manager)
        self._login('Manager')
        self.driver.get(f"{FRONTEND_URL}/attendance/team")
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Team Attendance']")))

        # Open employee picker
        picker_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='team-employee-select']")))
        picker_btn.click()

        options = self.wait.until(EC.visibility_of_all_elements_located((
            By.CSS_SELECTOR, "[data-testid^='team-employee-option-']"
        )))
        option_texts = [opt.text for opt in options]

        # In demo data: Tanvir Rahman manages Engineering (Ayesha Siddiqua, Farhan Ahmed, Mehedi Hasan)
        has_subordinate = any("Ayesha Siddiqua" in t or "Farhan Ahmed" in t for t in option_texts)
        self.assertTrue(has_subordinate, f"Manager should see team members in dropdown: {option_texts}")

        # Non-team members (e.g., Rafiq Islam from Sales) must NOT be present
        has_non_team = any("Rafiq Islam" in t for t in option_texts)
        self.assertFalse(has_non_team, f"Manager should NOT see non-team employees in dropdown: {option_texts}")

        # 2. Plain Employee (Ayesha Siddiqua) has no team and no view_team_attendance
        self._login('Employee')
        # Wait for dashboard or page to load
        time.sleep(1)

        # Check navigation sidebar: Team Attendance link should not exist
        team_nav_links = self.driver.find_elements(By.XPATH, "//a[normalize-space()='Team Attendance']")
        self.assertEqual(len(team_nav_links), 0, "Plain employee must not have 'Team Attendance' menu item in sidebar")


if __name__ == '__main__':
    unittest.main(verbosity=2)
