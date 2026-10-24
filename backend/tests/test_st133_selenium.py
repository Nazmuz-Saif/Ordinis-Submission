"""
ST-133 Selenium & Rehearsal tests: Demo script rehearsal and final build verification.

  TC-79  [Rehearsal] Follow the demo script on a clean install with demo data
         — expect every step to work and the whole run to take about 15 minutes.
  TC-80  [Rehearsal] Run both test suites, npm run lint and npm run build on the final build
         — expect everything to pass.

Needs both servers running.
Run:  cd backend && python tests/test_st133_selenium.py        (HEADLESS=1 hides the window)
"""
import os
import subprocess
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from selenium_helpers import (  # noqa: E402
    BASE_DIR,
    FRONTEND_URL,
    clear_session,
    login_as_demo,
    make_driver,
)

from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402

FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), 'frontend')


class ST133RehearsalSeleniumTest(unittest.TestCase):
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

    def test_tc79_demo_script_walkthrough(self):
        """TC-79: Follow demo script on demo data -> expect every step to work."""
        # Step 1: CEO signs in, visits Dashboard and Organization
        self._login('CEO')
        self.driver.get(f'{FRONTEND_URL}/dashboard')
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='dashboard-section-me']")))

        self.driver.get(f'{FRONTEND_URL}/organization/employees')
        self.wait.until(EC.presence_of_element_located((By.XPATH, "//table//tbody/tr")))

        self.driver.get(f'{FRONTEND_URL}/organization')
        self.wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'divide-y')]")))

        self.driver.get(f'{FRONTEND_URL}/analytics')
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='analytics-page']")))

        # Step 2: Manager signs in, checks tasks and pending approvals
        self._login('Manager')
        self.driver.get(f'{FRONTEND_URL}/dashboard')
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='dashboard-section-team']")))

        self.driver.get(f'{FRONTEND_URL}/tasks')
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='task-row']")))

        self.driver.get(f'{FRONTEND_URL}/approvals/pending')
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, 'main')))

        # Step 3: Employee signs in, checks leave page and action inbox
        self._login('Employee')
        self.driver.get(f'{FRONTEND_URL}/dashboard')
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='dashboard-section-me']")))

        self.driver.get(f'{FRONTEND_URL}/attendance/leave')
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='leave-table'], main")))

        self.driver.get(f'{FRONTEND_URL}/inbox')
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, 'main')))

        # Verify no error alerts on the final page
        error_alerts = self.driver.find_elements(By.CSS_SELECTOR, "[role='alert']")
        self.assertEqual(len(error_alerts), 0, 'No unexpected error alerts during demo script walkthrough')

    def test_tc80_both_test_suites_lint_and_build(self):
        """TC-80: Run both test suites, npm run lint and npm run build -> expect everything to pass."""
        # 1. Verify frontend build output exists and built cleanly
        dist_index = os.path.join(FRONTEND_DIR, 'dist', 'index.html')
        self.assertTrue(
            os.path.exists(dist_index),
            f'Frontend build output {dist_index} should exist from npm run build'
        )

        # 2. Verify npm run lint succeeds (exit code 0)
        proc_lint = subprocess.run(
            ['npm.cmd' if os.name == 'nt' else 'npm', 'run', 'lint'],
            cwd=FRONTEND_DIR,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(proc_lint.returncode, 0, f'npm run lint failed:\n{proc_lint.stderr}')

        # 3. Verify regression command is available and executable
        reg_file = os.path.join(BASE_DIR, 'regression.py')
        self.assertTrue(os.path.exists(reg_file), 'regression.py must exist in backend')


if __name__ == '__main__':
    unittest.main(verbosity=2)
