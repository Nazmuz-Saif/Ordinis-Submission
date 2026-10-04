"""
Selenium Test:
Log in as a CEO right after registration and add a Department —
expect success (CEO Role assigned automatically).
Company: Onnorokom Pathshala (subdomain: onnorokom)
CEO: ceo.onnorokom@gmail.com
Department: HR
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
from selenium.webdriver.support.ui import WebDriverWait

from organization.models import Company, Department, Designation, Employee
from rbac.models import EmployeeRole, Permission, Role
from tenants.models import CompanySettings

User = get_user_model()

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
COMPANY_NAME = "Onnorokom Pathshala"
SUBDOMAIN = "onnorokom"
INDUSTRY = "Education"
CEO_EMAIL = "ceo.onnorokom@gmail.com"
PASSWORD = "TestPass123!"
DEPARTMENT_NAME = "HR"


def cleanup_test_data():
    """Removes test company and user data specifically for 'onnorokom' to ensure clean state."""
    try:
        company = Company.objects.filter(subdomain=SUBDOMAIN).first()
        if company:
            Department.objects.filter(company=company).delete()
            EmployeeRole.objects.filter(company=company).delete()
            Employee.objects.filter(company=company).delete()
            Role.objects.filter(company=company).delete()
            Designation.objects.filter(company=company).delete()
            CompanySettings.objects.filter(company=company).delete()
            User.objects.filter(company=company).delete()
            company.delete()
        User.objects.filter(email=CEO_EMAIL).delete()
    except Exception as e:
        print(f"Warning during cleanup: {e}")


class CeoRegistrationDepartmentSeleniumTest(unittest.TestCase):
    def setUp(self):
        cleanup_test_data()
        options = webdriver.ChromeOptions()
        if os.environ.get("HEADLESS", "0") == "1":
            options.add_argument("--headless=new")
        self.driver = webdriver.Chrome(options=options)
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 20)

    def tearDown(self):
        self.driver.quit()

    def test_ceo_registration_and_add_department(self):
        driver = self.driver

        # [Step 1] Navigate to Register Page
        print("\n[Step 1] Navigating to Registration page...")
        driver.get(f"{FRONTEND_URL}/register")
        time.sleep(2)

        # [Step 2] Fill Registration Form
        print(f"[Step 2] Filling registration form for '{COMPANY_NAME}' with CEO '{CEO_EMAIL}'...")
        name_input = self.wait.until(
            EC.visibility_of_element_located((By.NAME, "company_name"))
        )
        name_input.clear()
        name_input.send_keys(COMPANY_NAME)
        time.sleep(1)

        subdomain_input = driver.find_element(By.NAME, "subdomain")
        subdomain_input.clear()
        subdomain_input.send_keys(SUBDOMAIN)
        time.sleep(1)

        industry_input = driver.find_element(By.NAME, "industry")
        industry_input.clear()
        industry_input.send_keys(INDUSTRY)
        time.sleep(1)

        email_input = driver.find_element(By.NAME, "ceo_email")
        email_input.clear()
        email_input.send_keys(CEO_EMAIL)
        time.sleep(1)

        password_input = driver.find_element(By.NAME, "ceo_password")
        password_input.clear()
        password_input.send_keys(PASSWORD)
        time.sleep(2)

        # Submit registration
        register_btn = driver.find_element(By.XPATH, "//button[@type='submit'][contains(., 'Create company')]")
        print("  -> Submitting registration form...")
        register_btn.click()

        # [Step 3] Wait for registration to complete and redirect
        print("[Step 3] Waiting for registration to complete...")
        self.wait.until(EC.url_contains("/organization"))
        print(f"  -> Company '{COMPANY_NAME}' and CEO '{CEO_EMAIL}' successfully registered!")
        time.sleep(2)

        # [Step 4] Explicitly log in as CEO right after registration
        print("[Step 4] Navigating to /login to log in as CEO right after registration...")
        driver.get(f"{FRONTEND_URL}/login")
        driver.execute_script("localStorage.clear();")
        driver.refresh()
        time.sleep(2)

        login_email = self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
        )
        login_email.clear()
        login_email.send_keys(CEO_EMAIL)

        login_pass = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        login_pass.clear()
        login_pass.send_keys(PASSWORD)
        time.sleep(1.5)

        login_btn = driver.find_element(By.XPATH, "//button[normalize-space()='Login']")
        print(f"  -> Submitting login for CEO {CEO_EMAIL}...")
        login_btn.click()

        # Wait until redirected to /organization
        print("[Step 5] Waiting for authentication and navigation to /organization...")
        self.wait.until(EC.url_contains("/organization"))
        self.wait.until(
            EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Departments']"))
        )
        print("  -> CEO logged in successfully and navigated to Departments page.")
        time.sleep(2.5)

        # [Step 6] Add 'HR' Department
        print(f"[Step 6] Adding department '{DEPARTMENT_NAME}' as CEO...")
        dept_input = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='New department name']"))
        )
        dept_input.clear()
        dept_input.send_keys(DEPARTMENT_NAME)
        time.sleep(2.5)  # Pause to clearly see 'HR' written in the input box!

        add_btn = driver.find_element(By.XPATH, "//button[@type='submit'][contains(., 'Add')]")
        print("  -> Clicking '+ Add' button now...")
        add_btn.click()

        # [Step 7] Verify Department is added in UI and NO error message is shown
        print("[Step 7] Verifying Department creation success...")
        # Verify no error message
        error_elements = driver.find_elements(By.XPATH, "//p[contains(@class, 'text-[#DC2626]')]")
        self.assertEqual(len(error_elements), 0, f"Unexpected error message displayed: {[e.text for e in error_elements]}")

        # Verify department name is displayed in the list
        dept_badge = self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, f"//span[normalize-space()='{DEPARTMENT_NAME}']")
            )
        )
        print(f"  -> SUCCESS! Department '{dept_badge.text}' is visible on screen.")

        # Pause 5 seconds so user can clearly see the newly added HR department on screen
        print("  -> Pausing for 5 seconds to let you view the newly created department in the UI...")
        time.sleep(5)

        # [Step 8] Verify record in database
        print(f"[Step 8] Verifying database record for '{DEPARTMENT_NAME}' under company '{SUBDOMAIN}'...")
        dept_exists = Department.objects.filter(
            company__subdomain=SUBDOMAIN,
            name__iexact=DEPARTMENT_NAME
        ).exists()
        self.assertTrue(dept_exists, f"Database check failed: Department '{DEPARTMENT_NAME}' was not found in DB.")
        print(f"  -> Database verified: Department '{DEPARTMENT_NAME}' successfully saved in database!")

        # [Step 9] Verify CEO Role assigned automatically
        print("[Step 9] Verifying CEO Role was assigned automatically with full permissions...")
        user = User.objects.get(email=CEO_EMAIL)
        employee = Employee.objects.get(user=user)
        has_ceo_role = EmployeeRole.objects.filter(
            employee=employee,
            role__name="CEO",
            role__permissions__codename="manage_departments"
        ).exists()
        self.assertTrue(has_ceo_role, "Verification failed: CEO role with manage_departments permission was not found.")
        print("  -> CEO Role verification passed: CEO automatically has 'manage_departments' permission!")


if __name__ == "__main__":
    unittest.main()
