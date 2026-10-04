"""
Selenium Test:
Open an Employee detail page — expect the subordinate list;
assign then revoke a Role — expect the page to update.
Company: Onnorokom Pathshala (subdomain: onnorokom)
CEO: ceo.onnorokom@gmail.com
Manager: Oitijjho (ONNOROKOM-MNS01)
Subordinate: Tahsin (ONNOROKOM-THS01, reports to Oitijjho)
Role to Assign/Revoke: Team Lead
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

from organization.models import Company, Department, Designation, Employee
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

TEST_ROLE_NAME = "Team Lead"


def setup_detail_test_data():
    """Sets up Onnorokom company, CEO, Manager (Oitijjho), Subordinate (Tahsin), and Team Lead role."""
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

    # 3. Manager (Oitijjho)
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

    # 4. Subordinate (Tahsin, reports to Oitijjho)
    dev_desig, _ = Designation.objects.get_or_create(company=company, title="Software Engineer")
    dev_user, _ = User.objects.get_or_create(
        email=TEAM_MEMBER_EMAIL,
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
            "employee_code": TEAM_MEMBER_CODE,
            "reports_to": mgr_emp,
        }
    )
    dev_emp.reports_to = mgr_emp
    dev_emp.save()

    # 5. Role "Team Lead"
    test_role, _ = Role.objects.get_or_create(
        company=company,
        name=TEST_ROLE_NAME,
        defaults={"description": "Team Lead role for department heads and leads."}
    )
    # Ensure it's not currently assigned to Oitijjho so test can assign it freshly
    EmployeeRole.objects.filter(employee=mgr_emp, role=test_role).delete()

    return company, ceo_emp, mgr_emp, dev_emp, test_role


class EmployeeDetailSubordinatesRolesSeleniumTest(unittest.TestCase):
    def setUp(self):
        self.company, self.ceo, self.mgr, self.dev, self.test_role = setup_detail_test_data()
        options = webdriver.ChromeOptions()
        if os.environ.get("HEADLESS", "0") == "1":
            options.add_argument("--headless=new")
        self.driver = webdriver.Chrome(options=options)
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 20)

    def tearDown(self):
        self.driver.quit()

    def test_employee_detail_subordinates_and_role_lifecycle(self):
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

        # [Step 3] Navigate to Employees list
        print("[Step 3] Navigating to Employees page (/organization/employees)...")
        driver.get(f"{FRONTEND_URL}/organization/employees")

        self.wait.until(
            EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Employees']"))
        )
        time.sleep(2)

        # [Step 4] Click on Manager Oitijjho (ONNOROKOM-MNS01) to open detail page
        print(f"[Step 4] Opening Employee detail page for '{MANAGER_CODE}' (Oitijjho)...")
        mgr_link = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, f"//a[normalize-space()='{MANAGER_CODE}']"))
        )
        mgr_link.click()

        # Wait for Detail page to load
        self.wait.until(
            EC.visibility_of_element_located((By.XPATH, f"//h1[normalize-space()='{MANAGER_CODE}']"))
        )
        print("  -> Employee detail page loaded successfully.")
        time.sleep(2.5)  # Pause to view loaded detail page

        # [Step 5] Verify Subordinate List: Tahsin (ONNOROKOM-THS01) is displayed
        print(f"[Step 5] Verifying Subordinate list displays '{TEAM_MEMBER_CODE}' (Tahsin)...")
        subordinate_link = self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, f"//div[contains(@class, 'divide-y')]//a[normalize-space()='{TEAM_MEMBER_CODE}']")
            )
        )
        self.assertTrue(
            subordinate_link.is_displayed(),
            f"Expected subordinate '{TEAM_MEMBER_CODE}' to be displayed in the team list."
        )
        print(f"  -> SUCCESS: Subordinate '{TEAM_MEMBER_CODE}' is visible in the Team list!")
        time.sleep(3.5)  # Pause so user can clearly see Tahsin in Oitijjho's Team list!

        # [Step 6] Assign Role: Team Lead
        print(f"[Step 6] Assigning Role '{TEST_ROLE_NAME}' to '{MANAGER_CODE}'...")
        role_select_elem = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, "//select[contains(@class, 'min-w-[200px]')]"))
        )
        role_select = Select(role_select_elem)
        role_select.select_by_visible_text(TEST_ROLE_NAME)
        time.sleep(1.5)

        assign_btn = driver.find_element(By.XPATH, "//button[@type='submit'][contains(., 'Assign')]")
        print(f"  -> Clicking 'Assign' button for role '{TEST_ROLE_NAME}'...")
        assign_btn.click()

        # Wait for page update: Role badge appears
        print(f"  -> Waiting for page update to display role '{TEST_ROLE_NAME}'...")
        role_badge = self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, f"//span[contains(@class, 'rounded-full')][contains(., '{TEST_ROLE_NAME}')]")
            )
        )
        self.assertTrue(role_badge.is_displayed(), f"Role badge for '{TEST_ROLE_NAME}' was not displayed.")
        print(f"  -> SUCCESS: Role '{TEST_ROLE_NAME}' badge is visible on the page!")

        # Verify in database
        role_in_db = EmployeeRole.objects.filter(
            employee=self.mgr,
            role__name=TEST_ROLE_NAME
        ).exists()
        self.assertTrue(role_in_db, f"Database check failed: Role '{TEST_ROLE_NAME}' not found for employee in DB.")
        print(f"  -> Database verified: EmployeeRole for '{TEST_ROLE_NAME}' created.")

        time.sleep(4)  # Pause 4 seconds to view the newly assigned role badge!

        # [Step 7] Revoke Role: Team Lead
        print(f"[Step 7] Revoking Role '{TEST_ROLE_NAME}' from '{MANAGER_CODE}'...")
        revoke_btn = role_badge.find_element(By.XPATH, ".//button[@title='Revoke role']")
        revoke_btn.click()
        time.sleep(1)

        # Accept browser confirmation alert
        print("  -> Accepting confirmation alert...")
        alert = driver.switch_to.alert
        alert.accept()

        # Wait for page update: Role badge disappears
        print(f"  -> Waiting for page update: verifying role '{TEST_ROLE_NAME}' is removed...")
        self.wait.until(
            EC.invisibility_of_element_located(
                (By.XPATH, f"//span[contains(@class, 'rounded-full')][contains(., '{TEST_ROLE_NAME}')]")
            )
        )
        print(f"  -> SUCCESS: Role '{TEST_ROLE_NAME}' badge was removed from the page!")

        # Verify in database
        role_revoked_in_db = not EmployeeRole.objects.filter(
            employee=self.mgr,
            role__name=TEST_ROLE_NAME
        ).exists()
        self.assertTrue(role_revoked_in_db, f"Database check failed: Role '{TEST_ROLE_NAME}' still exists in DB.")
        print(f"  -> Database verified: EmployeeRole for '{TEST_ROLE_NAME}' successfully deleted.")

        time.sleep(4)  # Pause 4 seconds to view updated page without the role!


if __name__ == "__main__":
    unittest.main()
