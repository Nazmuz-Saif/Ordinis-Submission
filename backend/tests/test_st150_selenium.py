"""
ST-150 Selenium tests, TC-118 to TC-120: Department and Designation detail pages.

Needs the demo company:  python manage.py seed_demo_data   (backend on :8000, frontend on :5173).
Run:  python -m unittest tests.test_st150_selenium     (from backend/, Chrome installed)
"""
import os
import sys
import unittest

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(TESTS_DIR))
sys.path.insert(0, TESTS_DIR)

from selenium_helpers import FRONTEND_URL, clear_session, login_as_demo, make_driver  # noqa: E402


class ST150DetailPagesSeleniumTest(unittest.TestCase):
    def setUp(self):
        self.driver, self.wait = make_driver()

    def tearDown(self):
        try:
            clear_session(self.driver)
        finally:
            self.driver.quit()

    def open_department(self, name):
        self.driver.get(f'{FRONTEND_URL}/organization')
        link = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, f"//a[@data-testid='department-link'][normalize-space()='{name}']")))
        link.click()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='department-name']")))

    def metric(self, label):
        return self.driver.find_element(
            By.XPATH, f"//*[@data-testid='metric-card'][.//p[normalize-space()='{label}']]//*[@data-testid='metric-value']"
        ).text.strip()

    def test_tc118_ceo_opens_a_department(self):
        login_as_demo(self.driver, self.wait, 'CEO')
        self.driver.get(f'{FRONTEND_URL}/organization')
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='department-head']")))
        self.open_department('Engineering')
        self.assertEqual(self.driver.find_element(By.CSS_SELECTOR, "[data-testid='department-name']").text, 'Engineering')
        self.assertIn('Tanvir Rahman', self.driver.find_element(By.CSS_SELECTOR, "[data-testid='department-head-line']").text)
        self.assertEqual(self.metric('People'), '4')
        rows = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='member-row']")
        self.assertEqual(len(rows), 4)
        table = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='members-table']").text
        self.assertIn('Software Engineer', table)
        self.assertIn('Ayesha Siddiqua', table)
        running = [e.text for e in self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='running-task']")]
        self.assertTrue(any('Build the employee directory search' in t for t in running), running)
        self.assertEqual(self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='hidden-tasks-note']"), [])

    def test_tc119_outsider_sees_counts_but_no_task_titles(self):
        login_as_demo(self.driver, self.wait, 'Employee')
        self.open_department('Sales')
        self.assertEqual(self.metric('Running tasks'), '2')
        self.assertEqual(self.metric('Overdue'), '1')
        self.assertEqual(self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='running-task']"), [])
        note = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='hidden-tasks-note']")))
        self.assertIn('2 more running tasks', note.text)
        page = self.driver.find_element(By.TAG_NAME, 'body').text
        self.assertNotIn('Follow up with the three open client quotes', page)
        self.assertNotIn('Prepare the monthly sales report', page)

    def test_tc120_designation_page_and_delete_in_use(self):
        login_as_demo(self.driver, self.wait, 'CEO')
        self.driver.get(f'{FRONTEND_URL}/organization/designations')
        link = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//a[@data-testid='designation-link'][normalize-space()='Software Engineer']")))
        link.click()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='designation-title']")))
        self.assertIn('2 people hold', self.driver.find_element(By.CSS_SELECTOR, "[data-testid='designation-count-line']").text)
        table = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='members-table']").text
        self.assertIn('Ayesha Siddiqua', table)
        self.assertIn('Farhan Ahmed', table)
        self.assertIn('Engineering', table)

        self.driver.get(f'{FRONTEND_URL}/organization/designations')
        row = self.wait.until(EC.visibility_of_element_located(
            (By.XPATH, "//div[.//a[@data-testid='designation-link'][normalize-space()='Software Engineer']][.//button[@title='Delete']]")))
        row.find_element(By.XPATH, ".//button[@title='Delete']").click()
        self.wait.until(EC.alert_is_present()).accept()
        message = self.wait.until(EC.visibility_of_element_located((By.XPATH, "//p[contains(.,'still has 2 employees')]")))
        self.assertIn('Ayesha Siddiqua', message.text)
        self.driver.refresh()
        self.wait.until(EC.visibility_of_element_located(
            (By.XPATH, "//a[@data-testid='designation-link'][normalize-space()='Software Engineer']")))


if __name__ == '__main__':
    unittest.main()
