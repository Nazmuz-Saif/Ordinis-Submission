"""
Selenium Test:
Enter an end date before the start date — expect a validation error.
Company: Onnorokom Pathshala (subdomain: onnorokom)
Delegator: ceo.onnorokom@gmail.com
Delegate: tahsin@onnorokom.com
Invalid Date Range: Start: 2026-10-15, End: 2026-10-10
"""
import os
import sys
import time
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "apps"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django
django.setup()

from django.contrib.auth import get_user_model
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from approvals.models import DelegationRule
from organization.models import Company, Department, Designation, Employee
from rbac.models import EmployeeRole, Permission, Role
from tenants.models import CompanySettings

User = get_user_model()

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
SUBDOMAIN = "onnorokom"
CEO_EMAIL = "ceo.onnorokom@gmail.com"
PASSWORD = "TestPass123!"

DELEGATE_CODE = "ONNOROKOM-THS01"
DELEGATE_EMAIL = "tahsin@onnorokom.com"

INVALID_START_DATE = "2026-10-15"
INVALID_END_DATE = "2026-10-10"
REASON = "Testing invalid date range (end before start)"


def set_react_input_value(driver, element, value):
    """Sets input value and dispatches React-compatible events."""
    driver.execute_script(
        """
        var element = arguments[0];
        var value = arguments[1];
        var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
        nativeInputValueSetter.call(element, value);
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
        """,
        element,
        value,
    )


def setup_delegation_test_data():
    """Sets up Onnorokom company, CEO, and delegate Tahsin."""
    # 1. Company
    company, _ = Company.objects.get_or_create(
        subdomain=SUBDOMAIN,
        defaults={"name": "Onnorokom Pathshala", "is_active": True}
    )
    CompanySettings.objects.get_or_create(company=company)

    # 2. CEO
    ceo_user, _ = User.objects.get_or_create(
        email=CEO_EMAIL,
        defaults={"company": company}
    )
    ceo_user.company = company
    ceo_user.set_password(PASSWORD)
    ceo_user.save()

    ceo_desig, _ = Designation.objects.get_or_create(company=company, title="CEO")
    ceo_emp, _ = Employee.objects.get_or_create(
        user=ceo_user,
        defaults={"company": company, "designation": ceo_desig, "employee_code": "ONNOROKOM-EMP001"}
    )
    ceo_role, _ = Role.objects.get_or_create(
        company=company,
        name="CEO",
        defaults={"is_system_default": True}
    )
    ceo_role.permissions.set(Permission.objects.all())
    EmployeeRole.objects.get_or_create(employee=ceo_emp, role=ceo_role, company=company)

    # 3. Delegate (Tahsin)
    dev_desig, _ = Designation.objects.get_or_create(company=company, title="Software Engineer")
    dev_user, _ = User.objects.get_or_create(
        email=DELEGATE_EMAIL,
        defaults={"company": company}
    )
    dev_user.company = company
    dev_user.set_password(PASSWORD)
    dev_user.save()

    dev_emp, _ = Employee.objects.get_or_create(
        user=dev_user,
        defaults={
            "company": company,
            "designation": dev_desig,
            "employee_code": DELEGATE_CODE,
            "reports_to": ceo_emp,
        }
    )

    return company, ceo_emp, dev_emp


class DelegationInvalidDateRangeSeleniumTest(unittest.TestCase):
    def setUp(self):
        self.company, self.ceo, self.dev = setup_delegation_test_data()
        options = webdriver.ChromeOptions()
        if os.environ.get("HEADLESS", "0") == "1":
            options.add_argument("--headless=new")
        self.driver = webdriver.Chrome(options=options)
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 20)

    def tearDown(self):
        self.driver.quit()

    def test_end_date_before_start_date_shows_validation_error(self):
        driver = self.driver

        # [Step 1] Navigate to Login page and log in as CEO
        print("\n[Step 1] Navigating to Login page...")
        driver.get(f"{FRONTEND_URL}/login")
        time.sleep(2)

        email_input = self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
        )
        email_input.clear()
        email_input.send_keys(CEO_EMAIL)

        password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password_input.clear()
        password_input.send_keys(PASSWORD)
        time.sleep(1.5)

        login_btn = driver.find_element(By.XPATH, "//button[normalize-space()='Login']")
        print(f"[Step 2] Logging in as CEO ({CEO_EMAIL})...")
        login_btn.click()

        self.wait.until(EC.url_contains("/organization"))
        time.sleep(1.5)

        # [Step 3] Navigate to Delegations page
        print("[Step 3] Navigating to Delegations page (/approvals/delegations)...")
        driver.get(f"{FRONTEND_URL}/approvals/delegations")

        self.wait.until(
            EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Delegation']"))
        )
        print("  -> Delegations page loaded successfully.")
        time.sleep(2.5)

        # [Step 4] Fill in Delegation form with INVALID date range (end before start)
        print(f"[Step 4] Selecting Delegate '{DELEGATE_EMAIL}'...")
        delegate_select_elem = self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='delegation-delegate']"))
        )
        select_obj = Select(delegate_select_elem)

        selected = False
        for option in select_obj.options:
            if DELEGATE_EMAIL in option.text:
                select_obj.select_by_visible_text(option.text)
                selected = True
                break
        self.assertTrue(selected, f"Could not find delegate '{DELEGATE_EMAIL}' in dropdown options.")
        print(f"  -> Selected '{DELEGATE_EMAIL}' as Delegate.")
        time.sleep(1.5)

        # Set Start Date (2026-10-15)
        print(f"  -> Setting Start Date: {INVALID_START_DATE}...")
        start_input = driver.find_element(By.CSS_SELECTOR, "[data-testid='delegation-start']")
        set_react_input_value(driver, start_input, INVALID_START_DATE)
        time.sleep(1.5)

        # Set End Date (2026-10-10 - BEFORE start date!)
        print(f"  -> Setting End Date (BEFORE start date): {INVALID_END_DATE}...")
        end_input = driver.find_element(By.CSS_SELECTOR, "[data-testid='delegation-end']")
        set_react_input_value(driver, end_input, INVALID_END_DATE)
        time.sleep(1.5)

        # Set Reason
        print(f"  -> Entering Reason: '{REASON}'...")
        reason_input = driver.find_element(By.XPATH, "//input[@placeholder='e.g. On leave']")
        reason_input.clear()
        reason_input.send_keys(REASON)
        time.sleep(2.5)  # Pause to see the invalid date inputs clearly on screen

        # [Step 5] Submit form
        save_btn = driver.find_element(By.CSS_SELECTOR, "[data-testid='delegation-save']")
        print("[Step 5] Submitting form with invalid date range...")
        save_btn.click()

        # [Step 6] Expect Validation Error on screen
        print("[Step 6] Checking for validation error message...")
        error_element = self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='delegation-error']"))
        )
        error_text = error_element.text.strip()
        print(f"  -> VALIDATION ERROR DISPLAYED: \"{error_text}\"")

        # Assert expected error message
        self.assertTrue(
            "before the start date" in error_text.lower(),
            f"Expected error message mentioning 'before the start date', but got: '{error_text}'"
        )
        print("  -> SUCCESS: Invalid date range was blocked with the correct validation error!")

        # Pause 5 seconds so the user can clearly see the red validation error message on screen
        print("  -> Pausing for 5 seconds to let you view the validation error on screen...")
        time.sleep(5)

        # [Step 7] Verify NO record was created in the database
        print("[Step 7] Verifying database integrity...")
        record_exists = DelegationRule.objects.filter(
            company=self.company,
            delegator=self.ceo,
            delegate=self.dev,
            start_date=INVALID_START_DATE,
            end_date=INVALID_END_DATE,
        ).exists()
        self.assertFalse(record_exists, "Database check failed: Invalid delegation record was saved in DB!")
        print("  -> Database verified: No invalid delegation record exists in database.")


if __name__ == "__main__":
    unittest.main()
