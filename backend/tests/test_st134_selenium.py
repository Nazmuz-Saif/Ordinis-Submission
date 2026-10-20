"""
ST-134 Selenium tests: the Analytics page.

  TC-81  CEO opens Analytics: the metric cards, the attendance line chart and the tasks-by-department bar chart.
  TC-82  An Employee without view_analytics: no Analytics menu item, and the page address shows no data.

Needs the demo company (python manage.py seed_demo_data) and both servers running.
Run:  cd backend && python tests/test_st134_selenium.py        (HEADLESS=1 hides the window)
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from selenium_helpers import FRONTEND_URL, clear_session, login_as_demo, make_driver  # noqa: E402

from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402

TESTIDS = ('analytics-attendance-rate', 'analytics-completion-rate', 'analytics-overdue', 'analytics-workload')


class ST134AnalyticsSeleniumTest(unittest.TestCase):
    def setUp(self):
        self.driver, self.wait = make_driver()

    def tearDown(self):
        clear_session(self.driver)
        self.driver.quit()

    def open_analytics(self):
        self.driver.get(f'{FRONTEND_URL}/analytics')
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='analytics-page'], main")))

    def test_tc81_ceo_sees_metric_cards_and_both_charts(self):
        login_as_demo(self.driver, self.wait, 'CEO')
        self.open_analytics()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='analytics-page']")))
        for testid in TESTIDS:
            card = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, f"[data-testid='{testid}']")))
            self.assertTrue(card.text.strip(), f'{testid} is empty')
        self.assertIn('%', self.driver.find_element(By.CSS_SELECTOR, "[data-testid='analytics-attendance-rate']").text)
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='line-chart']")))
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='grouped-bar-chart']")))
        self.assertTrue(self.driver.find_elements(By.XPATH, "//aside//a[normalize-space()='Analytics']"))

    def test_tc82_employee_has_no_menu_item_and_no_page(self):
        login_as_demo(self.driver, self.wait, 'Employee')
        self.assertFalse(self.driver.find_elements(By.XPATH, "//aside//a[normalize-space()='Analytics']"))
        self.driver.get(f'{FRONTEND_URL}/analytics')
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//*[contains(text(),'do not have access')]")))
        self.assertFalse(self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='analytics-attendance-rate']"))
        self.assertFalse(self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='line-chart']"))


if __name__ == '__main__':
    unittest.main(verbosity=2)
