"""
Selenium Test:
Delegate to yourself — expect the request rejected.
Company: Onnorokom Pathshala (subdomain: onnorokom)
CEO: ceo.onnorokom@gmail.com
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

REASON = "Self-delegation attempt"


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
    """Sets up Onnorokom company, CEO, and colleague Tahsin."""
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

    # 3. Colleague (Tahsin)
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


class DelegationSelfRejectSeleniumTest(unittest.TestCase):
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

    def test_delegate_to_yourself_is_rejected(self):
        driver = self.driver

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
        time.sleep(2)

        # [Step 4] UI Verification: Self is excluded from default colleague dropdown
        print("[Step 4] Verifying UI excludes self from 'Delegate to' dropdown by default...")
        delegate_select_elem = self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='delegation-delegate']"))
        )
        select_obj = Select(delegate_select_elem)

        colleague_texts = [opt.text for opt in select_obj.options]
        self.assertFalse(
            any(CEO_EMAIL in text for text in colleague_texts),
            f"Security flaw: Logged-in user '{CEO_EMAIL}' should not appear in colleagues dropdown!"
        )
        print(f"  -> UI Verified: Current user '{CEO_EMAIL}' is not available in colleague dropdown.")
        time.sleep(1.5)

        # [Step 5] Attempt self-delegation submission
        print(f"[Step 5] Attempting to submit self-delegation for '{CEO_EMAIL}'...")
        driver.execute_script(
            """
            var sel = arguments[0];
            var empId = arguments[1];
            var email = arguments[2];
            var opt = document.createElement('option');
            opt.value = empId;
            opt.text = email + ' · ONNOROKOM-EMP001 (Myself)';
            sel.appendChild(opt);
            """,
            delegate_select_elem,
            str(self.ceo.id),
            CEO_EMAIL,
        )

        select_obj.select_by_value(str(self.ceo.id))
        # Trigger React onChange
        driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", delegate_select_elem)
        print(f"  -> Injected and selected self '{CEO_EMAIL}' in delegate dropdown.")
        time.sleep(2)  # Pause to clearly see self selected in dropdown!

        # Set Start Date
        start_input = driver.find_element(By.CSS_SELECTOR, "[data-testid='delegation-start']")
        set_react_input_value(driver, start_input, start_date)
        time.sleep(1)

        # Set End Date
        end_input = driver.find_element(By.CSS_SELECTOR, "[data-testid='delegation-end']")
        set_react_input_value(driver, end_input, end_date)
        time.sleep(1)

        # Set Reason
        reason_input = driver.find_element(By.XPATH, "//input[@placeholder='e.g. On leave']")
        reason_input.clear()
        reason_input.send_keys(REASON)
        time.sleep(2)

        # [Step 6] Submit form
        save_btn = driver.find_element(By.CSS_SELECTOR, "[data-testid='delegation-save']")
        print("[Step 6] Submitting self-delegation form...")
        save_btn.click()

        # [Step 7] Expect request REJECTED with message
        print("[Step 7] Checking for rejection error message on screen...")
        error_element = self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='delegation-error']"))
        )
        error_text = error_element.text.strip()
        print(f"  -> REJECTION ERROR DISPLAYED: \"{error_text}\"")

        # Assert rejection message
        self.assertTrue(
            "cannot delegate to yourself" in error_text.lower(),
            f"Expected error message mentioning 'cannot delegate to yourself', but got: '{error_text}'"
        )
        print("  -> SUCCESS: Self-delegation request was rejected with the correct error message!")

        # Pause 5 seconds so the user can clearly see the red rejection error on screen
        print("  -> Pausing for 5 seconds to let you view the rejection error on screen...")
        time.sleep(5)

        # [Step 8] Database Verification: Confirm NO self-delegation record exists
        print("[Step 8] Verifying database integrity...")
        self_delegation_in_db = DelegationRule.objects.filter(
            company=self.company,
            delegator=self.ceo,
            delegate=self.ceo,
        ).exists()
        self.assertFalse(
            self_delegation_in_db,
            "Security / Integrity Failure: Self-delegation record was found in DB!"
        )
        print("  -> Database verified: No self-delegation record exists.")


if __name__ == "__main__":
    unittest.main()
