"""
ST-130 Selenium tests: Demo data and role dashboards.

  TC-74  After running the demo data command log in as the CEO, a Manager, HR, an Accountant
         and an Employee — expect each dashboard to show real numbers and charts.
  TC-75  Run the demo data command a second time — expect no duplicate Employees, Departments
         or Tasks on their pages.

Needs the demo company (python manage.py seed_demo_data) and both servers running.
Run:  cd backend && python tests/test_st130_selenium.py        (HEADLESS=1 hides the window)
"""
import os
import subprocess
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from selenium_helpers import (  # noqa: E402
    BASE_DIR,
    DEMO_PASSWORD,
    DEMO_USERS,
    FRONTEND_URL,
    clear_session,
    login_as_demo,
    make_driver,
)

from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402


class ST130DashboardAndDemoDataSeleniumTest(unittest.TestCase):
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

    def test_tc74_dashboards_show_real_numbers_and_charts(self):
        """TC-74: Dashboards for CEO, Manager, HR, Accountant and Employee show role-appropriate real numbers and charts."""
        # 1. CEO: sees all 4 sections (me, team, people, finance) with metrics and charts
        self._login('CEO')
        self.driver.get(f'{FRONTEND_URL}/dashboard')
        # Wait until loading finishes and metric cards appear (finance is the last section)
        self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='dashboard-section-finance'] [data-testid='metric-card']"))
        )

        for section_id in ('me', 'team', 'people', 'finance'):
            sec = self.wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, f"[data-testid='dashboard-section-{section_id}']"))
            )
            metric_cards = sec.find_elements(By.CSS_SELECTOR, "[data-testid='metric-card']")
            self.assertGreater(len(metric_cards), 0, f'Section {section_id} should have metric cards')
            for card in metric_cards:
                val = card.find_element(By.CSS_SELECTOR, "[data-testid='metric-value']").text.strip()
                self.assertTrue(val != '', f'Metric card in {section_id} has empty value')

        # Check charts in CEO dashboard: bar charts and donut chart
        bar_charts = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='bar-chart']")
        donut_charts = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='donut-chart']")
        self.assertGreaterEqual(len(bar_charts), 2, 'CEO dashboard should have bar charts')
        self.assertGreaterEqual(len(donut_charts), 1, 'CEO dashboard should have a donut chart')

        # 2. Manager: sees me and team; does NOT see people or finance
        self._login('Manager')
        self.driver.get(f'{FRONTEND_URL}/dashboard')
        self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='dashboard-section-team'] [data-testid='metric-card']"))
        )

        self.assertEqual(len(self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='dashboard-section-people']")), 0)
        self.assertEqual(len(self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='dashboard-section-finance']")), 0)

        team_sec = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='dashboard-section-team']")
        team_cards = team_sec.find_elements(By.CSS_SELECTOR, "[data-testid='metric-card']")
        self.assertGreaterEqual(len(team_cards), 4)

        # 3. HR: sees me and people; does NOT see team or finance
        self._login('HR')
        self.driver.get(f'{FRONTEND_URL}/dashboard')
        self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='dashboard-section-people'] [data-testid='metric-card']"))
        )

        self.assertEqual(len(self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='dashboard-section-team']")), 0)
        self.assertEqual(len(self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='dashboard-section-finance']")), 0)

        people_sec = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='dashboard-section-people']")
        people_cards = people_sec.find_elements(By.CSS_SELECTOR, "[data-testid='metric-card']")
        self.assertGreaterEqual(len(people_cards), 4)
        people_text = people_sec.text
        self.assertIn('Employees', people_text)
        self.assertIn('Departments', people_text)

        # 4. Accountant: sees me and finance; does NOT see team or people
        self._login('Accountant')
        self.driver.get(f'{FRONTEND_URL}/dashboard')
        self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='dashboard-section-finance'] [data-testid='metric-card']"))
        )

        self.assertEqual(len(self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='dashboard-section-team']")), 0)
        self.assertEqual(len(self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='dashboard-section-people']")), 0)

        finance_sec = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='dashboard-section-finance']")
        finance_cards = finance_sec.find_elements(By.CSS_SELECTOR, "[data-testid='metric-card']")
        self.assertGreaterEqual(len(finance_cards), 4)

        # 5. Employee: sees only me; does NOT see team, people or finance
        self._login('Employee')
        self.driver.get(f'{FRONTEND_URL}/dashboard')
        self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='dashboard-section-me'] [data-testid='metric-card']"))
        )

        self.assertEqual(len(self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='dashboard-section-team']")), 0)
        self.assertEqual(len(self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='dashboard-section-people']")), 0)
        self.assertEqual(len(self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='dashboard-section-finance']")), 0)

        me_sec = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='dashboard-section-me']")
        me_cards = me_sec.find_elements(By.CSS_SELECTOR, "[data-testid='metric-card']")
        self.assertGreaterEqual(len(me_cards), 4)

    def test_tc75_demo_data_no_duplicates_on_second_run(self):
        """TC-75: Run demo data command a second time -> expect no duplicate Employees, Departments or Tasks on their pages."""
        # Run seed_demo_data a second time via subprocess
        proc = subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, 'manage.py'), 'seed_demo_data'],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 0, f'seed_demo_data failed: {proc.stderr}')
        self.assertIn('nothing new', proc.stdout.lower(), 'Second seed_demo_data run should report nothing new')

        # Log in as CEO to inspect all pages
        self._login('CEO')

        # 1. Check Employees page: exactly 10 employees, unique employee codes and names
        self.driver.get(f'{FRONTEND_URL}/organization/employees')
        self.wait.until(EC.presence_of_element_located((By.XPATH, "//table//tbody/tr")))
        time.sleep(1)
        emp_rows = self.driver.find_elements(By.XPATH, "//table//tbody/tr")
        self.assertEqual(len(emp_rows), 10, f'Expected exactly 10 employees, found {len(emp_rows)}')
        emp_texts = [r.text.strip() for r in emp_rows]
        self.assertEqual(len(set(emp_texts)), 10, 'All employee rows on the page should be unique')

        # 2. Check Departments page: exactly 5 departments, no duplicates
        self.driver.get(f'{FRONTEND_URL}/organization')
        self.wait.until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'divide-y')]//span[contains(@class, 'font-medium')]"))
        )
        time.sleep(1)
        dept_elements = self.driver.find_elements(
            By.XPATH, "//div[contains(@class, 'divide-y')]//span[contains(@class, 'font-medium')]"
        )
        dept_names = [d.text.strip() for d in dept_elements if d.text.strip()]
        self.assertEqual(len(dept_names), 5, f'Expected 5 departments, found {len(dept_names)}: {dept_names}')
        self.assertEqual(len(set(dept_names)), 5, 'Department names must be unique without duplicates')

        # 3. Check Tasks page: all tasks rendered without duplicate ids or titles
        self.driver.get(f'{FRONTEND_URL}/tasks')
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='task-row']")))
        time.sleep(1)
        task_rows = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='task-row']")
        self.assertEqual(len(task_rows), 15, f'Expected 15 tasks, found {len(task_rows)}')
        task_texts = [t.text.strip() for t in task_rows]
        self.assertEqual(len(set(task_texts)), 15, 'All tasks on the page must be unique without duplicates')


if __name__ == '__main__':
    unittest.main(verbosity=2)
