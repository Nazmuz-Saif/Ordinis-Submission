
import os
import sys
import unittest
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.development"
)

import django
django.setup()

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC


import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from selenium_helpers import FRONTEND_URL, login  # noqa: E402  (one shared place: tests/selenium_helpers.py)

EMAIL = "ceo@acme.com"
PASSWORD = "TestPass123"
EMPLOYEE_CODE = "ORDI-EMP001"


def previous_months(count=24):
    year = date.today().year
    month = date.today().month

    for _ in range(count):
        month -= 1

        if month == 0:
            month = 12
            year -= 1

        yield f"{year:04d}-{month:02d}"


class TestST127Payslip(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        cls.driver = webdriver.Chrome(options=options)
        cls.wait = WebDriverWait(cls.driver, 20)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "driver"):
            cls.driver.quit()

    def login(self):
        login(self.driver, self.wait, EMAIL, PASSWORD)

    def select_employee(self):
        element = self.wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "[data-testid='payslip-employee']")
            )
        )

        dropdown = Select(element)

        matching_option = next(
            (
                option for option in dropdown.options
                if EMPLOYEE_CODE in option.text
            ),
            None
        )

        self.assertIsNotNone(
            matching_option,
            f"Employee {EMPLOYEE_CODE} was not found."
        )

        dropdown.select_by_visible_text(matching_option.text)

    def set_month(self, month):
        month_input = self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[data-testid='payslip-month']")
            )
        )

        self.driver.execute_script(
            """
            const input = arguments[0];
            const value = arguments[1];
            const setter = Object.getOwnPropertyDescriptor(
                HTMLInputElement.prototype,
                'value'
            ).set;
            setter.call(input, value);
            input.dispatchEvent(new Event('input', {bubbles: true}));
            input.dispatchEvent(new Event('change', {bubbles: true}));
            """,
            month_input,
            month
        )

    def submit_form(self):
        self.wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "[data-testid='payslip-generate']")
            )
        ).click()

    def read_response(self):
        result_elements = self.driver.find_elements(
            By.CSS_SELECTOR, "[data-testid='payslip-result']"
        )
        error_elements = self.driver.find_elements(
            By.CSS_SELECTOR, "[data-testid='payslip-error']"
        )

        result_text = ""
        error_text = ""

        for element in result_elements:
            if element.is_displayed():
                result_text = element.text.strip()
                break

        for element in error_elements:
            if element.is_displayed():
                error_text = element.text.strip()
                break

        return result_text, error_text

    def wait_for_response_change(self, old_result, old_error):
        def response_changed(driver):
            result_text, error_text = self.read_response()

            return (
                (bool(result_text) and result_text != old_result)
                or (bool(error_text) and error_text != old_error)
            )

        self.wait.until(response_changed)

    @staticmethod
    def amount(text):
        cleaned = (
            text.replace("BDT", "")
            .replace("৳", "")
            .replace(",", "")
            .strip()
        )
        return float(cleaned)

    def test_tc66_generate_and_tc67_duplicate(self):
        driver = self.driver

        self.login()
        driver.get(FRONTEND_URL + "/payroll/payslips")

        self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[data-testid='payslip-form']")
            )
        )

        self.select_employee()
        generated_month = None

        for month in previous_months():
            self.set_month(month)

            old_result, old_error = self.read_response()
            self.submit_form()
            self.wait_for_response_change(old_result, old_error)

            result_text, error_text = self.read_response()

            if result_text:
                generated_month = month
                break

            if "already exists" not in error_text.lower():
                self.fail(
                    f"Payslip generation failed for {month}: {error_text}"
                )

        self.assertIsNotNone(
            generated_month,
            "No unused month was found in the previous 24 months."
        )

        gross = self.amount(
            driver.find_element(
                By.CSS_SELECTOR, "[data-testid='result-gross']"
            ).text
        )

        deductions = self.amount(
            driver.find_element(
                By.CSS_SELECTOR, "[data-testid='result-deductions']"
            ).text
        )

        net = self.amount(
            driver.find_element(
                By.CSS_SELECTOR, "[data-testid='result-net']"
            ).text
        )

        self.assertGreater(gross, 0)
        self.assertGreaterEqual(deductions, 0)
        self.assertAlmostEqual(net, gross - deductions, places=2)

        print(
            f"\nTC-66 PASS: Month={generated_month}, "
            f"Gross={gross}, Deductions={deductions}, Net={net}"
        )

        self.set_month(generated_month)
        old_result, old_error = self.read_response()

        self.submit_form()
        self.wait_for_response_change(old_result, old_error)

        result_text, error_text = self.read_response()

        self.assertIn(
            "already exists",
            error_text.lower(),
            f"Expected duplicate rejection, received: "
            f"result={result_text!r}, error={error_text!r}"
        )

        print("TC-67 PASS: Duplicate payslip was rejected.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
