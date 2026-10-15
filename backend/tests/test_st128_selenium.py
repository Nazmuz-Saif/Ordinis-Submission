
import os
import uuid
import unittest
from datetime import date, timedelta

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.development",
)

import django
django.setup()

from django.contrib.auth import get_user_model
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select

from organization.models import Company, Employee
from attendance.leave_models import LeaveRequest, LeaveType


import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from selenium_helpers import FRONTEND_URL, login  # noqa: E402  (one shared place: tests/selenium_helpers.py)
PASSWORD = "TestPass128"


class ST128LeaveSeleniumTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.User = get_user_model()
        cls.suffix = uuid.uuid4().hex[:10]
        cls.email_prefix = f"st128-{cls.suffix}"

        cls.emails = [
            f"{cls.email_prefix}-employee@example.com",
            f"{cls.email_prefix}-other@example.com",
        ]

        cls.company = Company.objects.create(
            name=f"ST128 Test Company {cls.suffix}",
            subdomain=f"st128-{cls.suffix}",
            is_active=True,
        )

        cls.users = []
        cls.employees = []

        for index, email in enumerate(cls.emails, start=1):
            user = cls.User.objects.create_user(
                email=email,
                password=PASSWORD,
                is_active=True,
            )

            user.company = cls.company
            user.save()

            cls.users.append(user)

            employee = Employee.objects.create(
                user=user,
                company=cls.company,
                employee_code=f"ST128-{cls.suffix}-{index}",
            )
            cls.employees.append(employee)

        cls.leave_type = LeaveType.objects.create(
            company=cls.company,
            name=f"ST128 Test Leave {cls.suffix}",
            days_allowed_per_year=5,
        )

        LeaveRequest.objects.create(
            company=cls.company,
            employee=cls.employees[1],
            leave_type=cls.leave_type,
            start_date=date.today() + timedelta(days=60),
            end_date=date.today() + timedelta(days=60),
            days=1,
            reason="PRIVATE-ST128-OTHER-ONLY",
            status="pending",
        )

        LeaveRequest.objects.create(
            company=cls.company,
            employee=cls.employees[0],
            leave_type=cls.leave_type,
            start_date=date.today() + timedelta(days=70),
            end_date=date.today() + timedelta(days=70),
            days=1,
            reason="OWN-ST128-SEED",
            status="pending",
        )

    @classmethod
    def tearDownClass(cls):
        try:
            LeaveRequest.objects.filter(company=cls.company).delete()
            LeaveType.objects.filter(company=cls.company).delete()
            Employee.objects.filter(company=cls.company).delete()
            cls.User.objects.filter(
                email__startswith=cls.email_prefix
            ).delete()
            Company.objects.filter(pk=cls.company.pk).delete()
        finally:
            super().tearDownClass()

    def setUp(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")

        self.driver = webdriver.Chrome(options=options)
        self.driver.set_window_size(1365, 900)
        self.wait = WebDriverWait(self.driver, 15)

    def tearDown(self):
        if hasattr(self, "driver"):
            self.driver.quit()

    def login_and_open_leave(self):
        login(self.driver, self.wait, self.emails[0], PASSWORD)

        form_selector = "[data-testid='leave-form']"

        try:
            self.wait.until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, form_selector)
                )
            )
            return
        except TimeoutException:
            pass

        attendance_links = self.driver.find_elements(
            By.XPATH,
            "//*[self::a or self::button]"
            "[normalize-space()='Attendance']",
        )

        for link in attendance_links:
            if link.is_displayed() and link.is_enabled():
                link.click()
                break

        try:
            self.wait.until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, form_selector)
                )
            )
            return
        except TimeoutException:
            pass

        leave_links = self.driver.find_elements(
            By.XPATH,
            "//*[self::a or self::button]"
            "[contains(normalize-space(.), 'Leave')]",
        )

        for link in leave_links:
            if link.is_displayed() and link.is_enabled():
                link.click()

                try:
                    self.wait.until(
                        EC.visibility_of_element_located(
                            (By.CSS_SELECTOR, form_selector)
                        )
                    )
                    return
                except TimeoutException:
                    continue

        visible_items = [
            element.text.strip()
            for element in self.driver.find_elements(
                By.XPATH, "//a | //button"
            )
            if element.is_displayed() and element.text.strip()
        ]

        self.fail(
            f"Leave form not found. URL={self.driver.current_url}; "
            f"navigation={visible_items}"
        )

    def fill_leave_form(self, start_date, end_date, reason):
        self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[data-testid='leave-form']")
            )
        )

        selector = "[data-testid='leave-type']"

        try:
            self.wait.until(
                lambda driver: any(
                    option.get_attribute("value")
                    and not option.get_attribute("disabled")
                    for option in Select(
                        driver.find_element(By.CSS_SELECTOR, selector)
                    ).options
                )
            )
        except TimeoutException:
            select = Select(
                self.driver.find_element(By.CSS_SELECTOR, selector)
            )
            option_labels = [
                {
                    "text": option.text,
                    "value": option.get_attribute("value"),
                    "disabled": option.get_attribute("disabled"),
                }
                for option in select.options
            ]

            self.fail(
                "Leave Type dropdown stayed empty after waiting. "
                f"Test company ID={self.company.pk}; "
                f"user company ID={self.users[0].company_id}; "
                f"employee company ID={self.employees[0].company_id}; "
                f"options={option_labels}"
            )

        select = Select(
            self.driver.find_element(By.CSS_SELECTOR, selector)
        )

        available_options = [
            option for option in select.options
            if option.get_attribute("value")
            and not option.get_attribute("disabled")
        ]

        select.select_by_value(
            available_options[0].get_attribute("value")
        )

        start_input = self.driver.find_element(
            By.CSS_SELECTOR, "[data-testid='leave-start']"
        )

        self.driver.execute_script(
            """
            const input = arguments[0];
            const setter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            setter.call(input, arguments[1]);
            input.dispatchEvent(new Event('input', {bubbles: true}));
            input.dispatchEvent(new Event('change', {bubbles: true}));
            """,
            start_input,
            start_date.isoformat(),
        )

        end_input = self.driver.find_element(
            By.CSS_SELECTOR, "[data-testid='leave-end']"
        )

        self.driver.execute_script(
            """
            const input = arguments[0];
            input.removeAttribute('min');
            const setter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            setter.call(input, arguments[1]);
            input.dispatchEvent(new Event('input', {bubbles: true}));
            input.dispatchEvent(new Event('change', {bubbles: true}));
            """,
            end_input,
            end_date.isoformat(),
        )

        reason_input = self.driver.find_element(
            By.CSS_SELECTOR, "[data-testid='leave-reason']"
        )
        reason_input.clear()
        reason_input.send_keys(reason)

    def test_01_apply_leave_pending(self):
        self.login_and_open_leave()

        start = date.today() + timedelta(days=20)
        end = start + timedelta(days=1)

        self.fill_leave_form(
            start, end, "ST128 in-balance test"
        )

        self.driver.find_element(
            By.CSS_SELECTOR, "[data-testid='leave-submit']"
        ).click()

        message = self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[data-testid='leave-message']")
            )
        )

        self.assertIn("Pending", message.text)
        self.assertIn("2 days", message.text)

        self.assertTrue(
            LeaveRequest.objects.filter(
                company=self.company,
                employee=self.employees[0],
                reason="ST128 in-balance test",
                status="pending",
            ).exists()
        )

    def test_02_employee_sees_only_own_requests(self):
        self.login_and_open_leave()

        table = self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[data-testid='leave-table']")
            )
        )

        self.assertIn("OWN-ST128-SEED", table.text)
        self.assertNotIn("PRIVATE-ST128-OTHER-ONLY", table.text)

    def test_03_over_balance_shows_remaining_days(self):
        self.login_and_open_leave()

        start = date.today() + timedelta(days=40)
        end = start + timedelta(days=5)

        self.fill_leave_form(
            start, end, "ST128 over-balance test"
        )

        self.driver.find_element(
            By.CSS_SELECTOR, "[data-testid='leave-submit']"
        ).click()

        error = self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[data-testid='leave-error']")
            )
        )

        self.assertIn("remaining balance", error.text.lower())
        self.assertIn("days", error.text.lower())

        self.assertFalse(
            LeaveRequest.objects.filter(
                company=self.company,
                employee=self.employees[0],
                reason="ST128 over-balance test",
            ).exists()
        )

    def test_04_reversed_dates_validation(self):
        self.login_and_open_leave()

        start = date.today() + timedelta(days=90)
        end = start - timedelta(days=1)

        self.fill_leave_form(
            start, end, "ST128 reversed-date test"
        )

        date_error = self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[data-testid='leave-end-error']")
            )
        )

        self.assertIn(
            "end date cannot be before",
            date_error.text.lower(),
        )


if __name__ == "__main__":
    unittest.main()
