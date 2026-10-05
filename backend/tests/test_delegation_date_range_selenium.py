"""
Selenium Test:
Create a delegation with a valid date range — expect it in the list.
Company: Onnorokom Pathshala (subdomain: onnorokom)
Delegator: ceo.onnorokom@gmail.com
Delegate: tahsin@onnorokom.com
"""
import datetime
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

REASON = "Annual Vacation Delegation"


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
    """Sets up Onnorokom company, CEO (delegator), and Tahsin (delegate), cleaning previous delegation rules."""
    # 1. Company
    company, _ = Company.objects.get_or_create(
        subdomain=SUBDOMAIN,
        defaults={"name": "Onnorokom Pathshala", "is_active": True}
    )
    CompanySettings.objects.get_or_create(company=company)

    # 2. CEO (Delegator)
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

    # 4. Clean up any previous test delegations between them
    DelegationRule.objects.filter(company=company, delegator=ceo_emp).delete()

    return company, ceo_emp, dev_emp


class DelegationDateRangeSeleniumTest(unittest.TestCase):
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

    def test_create_delegation_with_valid_date_range(self):
        driver = self.driver

        # Calculate a valid date range (tomorrow to +7 days)
        today = datetime.date.today()
        start_date = (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (today + datetime.timedelta(days=8)).strftime("%Y-%m-%d")

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
        time.sleep(2.5)  # Pause to clearly view the delegations form

        # [Step 4] Fill in Delegation form with valid date range
        print(f"[Step 4] Selecting Delegate '{DELEGATE_EMAIL}'...")
        delegate_select_elem = self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='delegation-delegate']"))
        )
        select_obj = Select(delegate_select_elem)

        # Select colleague containing delegate email
        selected = False
        for option in select_obj.options:
            if DELEGATE_EMAIL in option.text:
                select_obj.select_by_visible_text(option.text)
                selected = True
                break
        self.assertTrue(selected, f"Could not find delegate '{DELEGATE_EMAIL}' in dropdown options.")
        print(f"  -> Selected '{DELEGATE_EMAIL}' as Delegate.")
        time.sleep(1.5)

        # Set Start Date
        print(f"  -> Setting Start Date: {start_date}...")
        start_input = driver.find_element(By.CSS_SELECTOR, "[data-testid='delegation-start']")
        set_react_input_value(driver, start_input, start_date)
        time.sleep(1.5)

        # Set End Date
        print(f"  -> Setting End Date: {end_date} (valid range)...")
        end_input = driver.find_element(By.CSS_SELECTOR, "[data-testid='delegation-end']")
        set_react_input_value(driver, end_input, end_date)
        time.sleep(1.5)

        # Set Reason
        print(f"  -> Entering Reason: '{REASON}'...")
        reason_input = driver.find_element(By.XPATH, "//input[@placeholder='e.g. On leave']")
        reason_input.clear()
        reason_input.send_keys(REASON)
        time.sleep(2)  # Pause to see all filled details clearly

        # [Step 5] Submit form
        save_btn = driver.find_element(By.CSS_SELECTOR, "[data-testid='delegation-save']")
        print("[Step 5] Submitting Delegation form (clicking 'Create delegation')...")
        save_btn.click()

        # [Step 6] Expect Delegation in the list
        print("[Step 6] Waiting for delegation to appear in the list...")
        delegation_row = self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='delegation-row']"))
        )
        row_text = delegation_row.text
        print(f"  -> Delegation row content: {row_text}")

        # Assertions on table content
        self.assertIn(DELEGATE_EMAIL, row_text, f"Expected delegate email '{DELEGATE_EMAIL}' in table row.")
        self.assertIn(start_date, row_text, f"Expected start date '{start_date}' in table row.")
        self.assertIn(end_date, row_text, f"Expected end date '{end_date}' in table row.")
        self.assertIn(REASON, row_text, f"Expected reason '{REASON}' in table row.")
        print(f"  -> SUCCESS! Delegation with date range {start_date} → {end_date} is displayed in the list.")

        # Pause 5 seconds so the user can clearly see the created delegation in the table
        print("  -> Pausing for 5 seconds to let you view the newly created delegation in the UI...")
        time.sleep(5)

        # [Step 7] Verify record in database
        print("[Step 7] Verifying database record...")
        delegation_in_db = DelegationRule.objects.filter(
            company=self.company,
            delegator=self.ceo,
            delegate=self.dev,
            start_date=start_date,
            end_date=end_date,
            reason=REASON,
        ).exists()
        self.assertTrue(delegation_in_db, "Database check failed: DelegationRule record was not created in DB.")
        print("  -> Database verified: DelegationRule record saved successfully in DB!")


if __name__ == "__main__":
    unittest.main()
