"""
Selenium Test:
1. Add an employee via the top form with reporting relationship.
2. Attempt an invalid submission in the top form and expect an error message.
3. Edit an existing manager in the table and attempt a circular reporting cycle —
   expect the request blocked with the circular hierarchy error message.
Company: Onnorokom Pathshala (subdomain: onnorokom)
CEO: ceo.onnorokom@gmail.com
Manager: Oitijjho (ONNOROKOM-MNS01)
Team Member: Tahsin (ONNOROKOM-THS01, reports to Oitijjho)
"""
import os
import sys
import time
import unittest
from unittest.mock import Mock

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

from organization.models import Company, Department, Designation, Employee
from organization.serializers import EmployeeSerializer
from rbac.models import EmployeeRole, Permission, Role
from tenants.models import CompanySettings

User = get_user_model()

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
SUBDOMAIN = "onnorokom"
CEO_EMAIL = "ceo.onnorokom@gmail.com"
PASSWORD = "TestPass123!"

MANAGER_CODE = "ONNOROKOM-MNS01"
MANAGER_EMAIL = "oitijjho@onnorokom.com"

TEAM_MEMBER_CODE = "ONNOROKOM-THS01"
TEAM_MEMBER_EMAIL = "tahsin@onnorokom.com"


def setup_initial_data():
    """Sets up Onnorokom company with CEO and Manager Oitijjho, cleaning any previous Tahsin."""
    # 1. Company
    company, _ = Company.objects.get_or_create(
        subdomain=SUBDOMAIN,
        defaults={"name": "Onnorokom Pathshala", "is_active": True}
    )
    CompanySettings.objects.get_or_create(company=company)

    # 2. Clean up any previous test team member to allow fresh UI creation
    User.objects.filter(email=TEAM_MEMBER_EMAIL).delete()
    Employee.objects.filter(company=company, employee_code=TEAM_MEMBER_CODE).delete()

    # 3. CEO User & Employee
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

    # Ensure CEO Role has all permissions
    ceo_role, _ = Role.objects.get_or_create(
        company=company,
        name="CEO",
        defaults={"is_system_default": True}
    )
    ceo_role.permissions.set(Permission.objects.all())
    EmployeeRole.objects.get_or_create(employee=ceo_emp, role=ceo_role, company=company)

    # 4. Manager (Oitijjho)
    mgr_desig, _ = Designation.objects.get_or_create(company=company, title="Engineering Manager")
    mgr_user, _ = User.objects.get_or_create(
        email=MANAGER_EMAIL,
        defaults={"company": company}
    )
    mgr_user.company = company
    mgr_user.set_password(PASSWORD)
    mgr_user.save()

    mgr_emp, _ = Employee.objects.get_or_create(
        user=mgr_user,
        defaults={
            "company": company,
            "designation": mgr_desig,
            "employee_code": MANAGER_CODE,
            "reports_to": ceo_emp,
        }
    )
    mgr_emp.reports_to = ceo_emp
    mgr_emp.save()

    return company, ceo_emp, mgr_emp


class ReportingCycleSeleniumTest(unittest.TestCase):
    def setUp(self):
        self.company, self.ceo, self.mgr = setup_initial_data()
        options = webdriver.ChromeOptions()
        if os.environ.get("HEADLESS", "0") == "1":
            options.add_argument("--headless=new")
        self.driver = webdriver.Chrome(options=options)
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 20)

    def tearDown(self):
        self.driver.quit()

    def test_reporting_flows_top_form_and_circular_cycle_blocked(self):
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

        # [Step 3] Navigate to Employees page
        print("[Step 3] Navigating to Employees page (/organization/employees)...")
        driver.get(f"{FRONTEND_URL}/organization/employees")

        self.wait.until(
            EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Employees']"))
        )
        time.sleep(2)

        # ----------------------------------------------------------------------
        # PART 1: Add Tahsin via the top "Add Employee" form reporting to Oitijjho
        # ----------------------------------------------------------------------
        print(f"\n--- PART 1: Adding team member '{TEAM_MEMBER_CODE}' via top form ---")
        top_form = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, "//form[contains(@class, 'grid')]"))
        )

        email_field = top_form.find_element(By.NAME, "email")
        email_field.clear()
        email_field.send_keys(TEAM_MEMBER_EMAIL)
        time.sleep(1)

        pass_field = top_form.find_element(By.NAME, "password")
        pass_field.clear()
        pass_field.send_keys(PASSWORD)
        time.sleep(1)

        code_field = top_form.find_element(By.NAME, "employee_code")
        code_field.clear()
        code_field.send_keys(TEAM_MEMBER_CODE)
        time.sleep(1)

        top_reports_select = Select(top_form.find_element(By.NAME, "reports_to"))
        top_reports_select.select_by_visible_text(MANAGER_CODE)
        print(f"  -> Set Reports To in top form to Manager '{MANAGER_CODE}'.")
        time.sleep(2)

        submit_btn = top_form.find_element(By.XPATH, ".//button[@type='submit']")
        print(f"  -> Submitting top form to create '{TEAM_MEMBER_CODE}'...")
        submit_btn.click()

        # Wait for Tahsin to appear in the table
        self.wait.until(
            EC.visibility_of_element_located((By.XPATH, f"//a[normalize-space()='{TEAM_MEMBER_CODE}']"))
        )
        print(f"  -> SUCCESS: '{TEAM_MEMBER_CODE}' (Tahsin) created and visible in table!")
        time.sleep(3)  # Pause to clearly see Tahsin in the table

        # ----------------------------------------------------------------------
        # PART 2: Attempt invalid duplicate / self-reporting in top form -> Expect Error
        # ----------------------------------------------------------------------
        print("\n--- PART 2: Attempting invalid entry in top form to verify error handling ---")
        top_form = driver.find_element(By.XPATH, "//form[contains(@class, 'grid')]")

        email_field = top_form.find_element(By.NAME, "email")
        email_field.clear()
        email_field.send_keys(MANAGER_EMAIL)  # already registered email
        time.sleep(1)

        pass_field = top_form.find_element(By.NAME, "password")
        pass_field.clear()
        pass_field.send_keys(PASSWORD)
        time.sleep(1)

        code_field = top_form.find_element(By.NAME, "employee_code")
        code_field.clear()
        code_field.send_keys(MANAGER_CODE)  # already existing employee code
        time.sleep(1)

        top_reports_select = Select(top_form.find_element(By.NAME, "reports_to"))
        top_reports_select.select_by_visible_text(MANAGER_CODE)
        print(f"  -> In top form: entered existing code '{MANAGER_CODE}' with self-reporting.")
        time.sleep(2)

        submit_btn = top_form.find_element(By.XPATH, ".//button[@type='submit']")
        submit_btn.click()

        # Expect error message displayed on screen
        error_element = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, "//p[contains(@class, 'text-[#DC2626]')]"))
        )
        top_error_text = error_element.text.strip()
        print(f"  -> TOP FORM ERROR DISPLAYED: \"{top_error_text}\"")
        self.assertTrue(len(top_error_text) > 0, "Expected an error message from top form, but none was displayed.")
        time.sleep(4)  # Pause 4 seconds to view the top form error message

        # ----------------------------------------------------------------------
        # PART 3: In Table, edit Oitijjho and attempt circular reporting cycle -> Expect Block
        # ----------------------------------------------------------------------
        print(f"\n--- PART 3: Attempting circular reporting cycle on '{MANAGER_CODE}' in table ---")
        mgr_link = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, f"//a[normalize-space()='{MANAGER_CODE}']"))
        )
        mgr_row = mgr_link.find_element(By.XPATH, "./ancestor::tr")

        # Click the Edit (Pencil) button on Oitijjho's row
        print(f"  -> Clicking Edit (Pencil) button for '{MANAGER_CODE}'...")
        edit_btn = mgr_row.find_element(By.XPATH, ".//button[@title='Edit']")
        edit_btn.click()
        time.sleep(2)

        # In edit row, select Tahsin in Reports To dropdown
        print(f"  -> In edit row, selecting subordinate '{TEAM_MEMBER_CODE}' (Tahsin)...")
        tbody_reports_select = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, "//tbody//select[@name='reports_to']"))
        )
        select_obj = Select(tbody_reports_select)
        select_obj.select_by_visible_text(TEAM_MEMBER_CODE)
        print(f"  -> Selected '{TEAM_MEMBER_CODE}' in Reports To dropdown.")
        time.sleep(2.5)  # Pause to clearly see the invalid circular selection!

        # Click Save (Checkmark button) inside the edit row
        print("  -> Submitting invalid circular reporting change...")
        save_btn = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//tbody//button[contains(@class, 'text-[#16A34A]')]"))
        )
        save_btn.click()

        # Expect request to be BLOCKED and circular reporting chain message displayed
        print("  -> Waiting for circular chain block message...")
        error_element = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, "//p[contains(@class, 'text-[#DC2626]')]"))
        )
        cycle_error_text = error_element.text.strip()
        print(f"  -> CIRCULAR CHAIN ERROR DISPLAYED: \"{cycle_error_text}\"")

        self.assertTrue(
            "circular reporting chain" in cycle_error_text.lower(),
            f"Expected error message mentioning circular reporting chain, but got: '{cycle_error_text}'"
        )
        print("  -> SUCCESS: Circular hierarchy request was blocked with the correct message!")

        # Pause 5 seconds so user can clearly see the circular reporting chain error message
        print("  -> Pausing for 5 seconds to let you view the blocked circular chain error on screen...")
        time.sleep(5)

        # ----------------------------------------------------------------------
        # PART 4: Database & Model Verification
        # ----------------------------------------------------------------------
        print("\n--- PART 4: Verifying Database Integrity & Self-Reporting Validation ---")
        self.mgr.refresh_from_db()
        dev_emp = Employee.objects.get(employee_code=TEAM_MEMBER_CODE)

        self.assertNotEqual(
            self.mgr.reports_to_id,
            dev_emp.id,
            "Security / Integrity Failure: Manager's reports_to was changed to subordinate!"
        )
        self.assertEqual(
            dev_emp.reports_to_id,
            self.mgr.id,
            "Integrity check passed: Subordinate correctly reports to Manager."
        )
        print("  -> Database verified: Hierarchy remains uncorrupted.")

        # Self-manager validation check
        mock_request = Mock()
        mock_request.user = self.ceo.user
        serializer = EmployeeSerializer(
            instance=self.mgr,
            data={"reports_to": self.mgr.id},
            context={"request": mock_request},
            partial=True
        )
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid, "Expected serializer to reject setting employee as their own manager.")
        self.assertIn("reports_to", serializer.errors)
        self.assertIn("cannot report to themselves", str(serializer.errors["reports_to"]).lower())
        print(f"  -> Self-manager validation verified: {serializer.errors['reports_to']}")


if __name__ == "__main__":
    unittest.main()
