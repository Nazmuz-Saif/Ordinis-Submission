import unittest

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from tests.selenium_helpers import make_driver, login_as_demo, FRONTEND_URL


class TestST137AttendanceSummary(unittest.TestCase):

    def setUp(self):
        self.driver, self.wait = make_driver()

        try:
            login_as_demo(self.driver, self.wait, 'Employee')
            self.driver.get(f'{FRONTEND_URL}/attendance')

            self.wait.until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, '[data-testid="attendance-today"]')
                )
            )

            self.wait.until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, '[data-testid="calendar-grid"]')
                )
            )

            self.wait.until(
                lambda driver: driver.find_element(
                    By.CSS_SELECTOR,
                    '[data-testid="calendar-month-label"]'
                ).text.strip() != ''
            )

        except Exception:
            self.driver.quit()
            raise

    def tearDown(self):
        if hasattr(self, 'driver'):
            self.driver.quit()

    def test_tc137_01_attendance_summary_and_calendar_display(self):
        driver = self.driver

        self.assertEqual(
            driver.find_element(By.TAG_NAME, 'h1').text.strip(),
            'Attendance',
        )

        self.assertTrue(
            driver.find_element(
                By.CSS_SELECTOR, '[data-testid="attendance-date"]'
            ).text.strip()
        )

        self.assertTrue(
            driver.find_element(
                By.CSS_SELECTOR, '[data-testid="attendance-status"]'
            ).is_displayed()
        )

        summary_cards = (
            'calendar-card-present',
            'calendar-card-absent',
            'calendar-card-on-leave',
            'calendar-card-rate',
        )

        for test_id in summary_cards:
            with self.subTest(summary_card=test_id):
                self.assertTrue(
                    driver.find_element(
                        By.CSS_SELECTOR,
                        f'[data-testid="{test_id}"]',
                    ).is_displayed()
                )

        self.assertTrue(
            driver.find_element(
                By.CSS_SELECTOR,
                '[data-testid="calendar-month-label"]',
            ).text.strip()
        )

        days = driver.find_elements(
            By.CSS_SELECTOR, '[data-testid^="calendar-day-"]'
        )

        self.assertGreater(
            len(days),
            0,
            'The attendance calendar should display days.',
        )

    def test_tc137_02_calendar_month_navigation(self):
        driver = self.driver

        month_label = (
            By.CSS_SELECTOR, '[data-testid="calendar-month-label"]'
        )
        previous_button = (
            By.CSS_SELECTOR, '[data-testid="calendar-prev"]'
        )
        next_button = (
            By.CSS_SELECTOR, '[data-testid="calendar-next"]'
        )
        calendar_grid = (
            By.CSS_SELECTOR, '[data-testid="calendar-grid"]'
        )

        current_month = driver.find_element(*month_label).text.strip()

        self.assertTrue(
            current_month,
            'Current month label should not be empty.',
        )

        previous = self.wait.until(
            EC.element_to_be_clickable(previous_button)
        )

        self.assertTrue(
            previous.is_enabled(),
            'Previous-month button should be enabled.',
        )

        driver.execute_script(
            "arguments[0].click();",
            previous,
        )

        try:
            self.wait.until(
                lambda d: (
                    d.find_element(*month_label).text.strip()
                    != current_month
                )
            )
        except Exception:
            actual_month = driver.find_element(*month_label).text.strip()
            self.fail(
                f'Previous-month navigation failed. '
                f'Before click: {current_month!r}; '
                f'after click: {actual_month!r}.'
            )

        previous_month = driver.find_element(*month_label).text.strip()

        self.assertTrue(
            driver.find_element(*calendar_grid).is_displayed(),
            'Calendar grid should remain visible after Previous.',
        )

        next_btn = self.wait.until(
            EC.element_to_be_clickable(next_button)
        )

        self.assertTrue(
            next_btn.is_enabled(),
            'Next-month button should be enabled after moving backward.',
        )

        driver.execute_script(
            "arguments[0].click();",
            next_btn,
        )

        self.wait.until(
            lambda d: (
                d.find_element(*month_label).text.strip()
                != previous_month
            )
        )

        self.assertEqual(
            driver.find_element(*month_label).text.strip(),
            current_month,
            'Next should return the calendar to the original month.',
        )

        self.assertTrue(
            driver.find_element(*calendar_grid).is_displayed(),
            'Calendar grid should remain visible after Next.',
        )

    def test_tc137_03_personal_attendance_records_or_empty_state(self):
        driver = self.driver

        heading = driver.find_elements(
            By.XPATH,
            "//h2[normalize-space()='My attendance']",
        )

        self.assertTrue(
            heading,
            'My attendance section should be displayed.',
        )

        rows = driver.find_elements(
            By.CSS_SELECTOR, '[data-testid="attendance-row"]'
        )

        empty_state = driver.find_elements(
            By.XPATH,
            "//*[normalize-space()='No attendance yet']",
        )

        self.assertTrue(
            rows or empty_state,
            'Expected attendance records or the empty-state message.',
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)