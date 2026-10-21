import os
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.development"
)

import django
django.setup()

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from selenium_helpers import make_driver, login_as_demo, FRONTEND_URL


class TestST136BillingSelenium(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.driver, cls.wait = make_driver()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "driver"):
            cls.driver.quit()

    def setUp(self):
        self.driver.get(FRONTEND_URL + "/login")
        login_as_demo(self.driver, self.wait, "CEO")

    def test_tc86_ceo_can_view_billing_plan_usage_and_invoices(self):
        """TC-86: CEO can view plan details, employee usage and invoices."""
        self.driver.get(FRONTEND_URL + "/settings/billing")

        plan_card = self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[data-testid='billing-plan-card']")
            )
        )
        self.assertTrue(plan_card.is_displayed())

        plan_name = self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[data-testid='billing-plan-name']")
            )
        )
        self.assertTrue(plan_name.text.strip(), "Plan name should be displayed.")

        usage = self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[data-testid='billing-usage-text']")
            )
        )
        self.assertRegex(
            usage.text,
            r"\d+\s+of\s+\d+\s+employees|\d+\s+employees\s+\(no limit\)",
            "Employee usage and limit should be displayed."
        )

        invoices = self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[data-testid='billing-invoices']")
            )
        )
        self.assertTrue(invoices.is_displayed())

    def test_tc87_employee_creation_when_plan_limit_is_reached(self):
        """TC-87: At the employee limit, creation is rejected without adding an employee."""
        self.driver.get(FRONTEND_URL + "/settings/billing")

        usage = self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[data-testid='billing-usage-text']")
            )
        ).text.strip()

        import re
        match = re.search(r"(\d+)\s+of\s+(\d+)\s+employees", usage)

        if not match:
            self.skipTest(
                "The demo CEO account does not expose a finite employee limit."
            )

        current_count, employee_limit = map(int, match.groups())
        if current_count < employee_limit:
            self.skipTest(
                f"Plan limit is not reached: {current_count}/{employee_limit}. "
                "Use a dedicated test company at its employee limit."
            )

        self.driver.get(FRONTEND_URL + "/organization/employees")

        self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//h1[normalize-space()='Employees']")
            )
        )

        name = f"ST136 Limit Test {os.getpid()}"
        email = f"st136-limit-{os.getpid()}@example.com"
        code = f"ST136-{os.getpid()}"

        self.wait.until(
            EC.visibility_of_element_located(
                (By.NAME, "full_name")
            )
        ).send_keys(name)

        self.driver.find_element(By.NAME, "email").send_keys(email)
        self.driver.find_element(By.NAME, "password").send_keys("TestPass123!")
        self.driver.find_element(By.NAME, "employee_code").send_keys(code)

        before_rows = self.driver.find_elements(
            By.XPATH, f"//*[contains(normalize-space(), '{code}')]"
        )

        self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[normalize-space()='Add Employee']")
            )
        ).click()

        error = self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//*[contains(translate(normalize-space(.), "
                 "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
                 "'upgrade your plan')]")
            )
        )
        self.assertIn("upgrade your plan", error.text.lower())

        after_rows = self.driver.find_elements(
            By.XPATH, f"//*[contains(normalize-space(), '{code}')]"
        )
        self.assertEqual(
            len(after_rows),
            len(before_rows),
            "An employee must not be added when the plan limit is reached."
        )


if __name__ == "__main__":
    unittest.main()
