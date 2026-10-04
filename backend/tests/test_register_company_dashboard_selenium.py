"""
Selenium Test:
Register a new company from the registration page —
expect a redirect to the dashboard as CEO of that company only.
Company: Onnorokom Pathshala (subdomain: onnorokom)
CEO: ceo.onnorokom@gmail.com
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


class RegisterCompanyDashboardSeleniumTest(unittest.TestCase):
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

    def test_register_company_redirects_to_dashboard_as_ceo_only(self):
        driver = self.driver

        # [Step 1] Navigate to Register Page
        print("\n[Step 1] Navigating to Registration page...")
        driver.get(f"{FRONTEND_URL}/register")
        # Ensure fresh local storage session
        driver.execute_script("localStorage.clear();")
        driver.refresh()
        time.sleep(2)

        # [Step 2] Fill Registration Form
        print(f"[Step 2] Filling registration form for '{COMPANY_NAME}'...")
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

        # [Step 3] Expect redirect to dashboard (/organization)
        print("[Step 3] Waiting for automatic redirect to dashboard...")
        self.wait.until(EC.url_contains("/organization"))
        print("  -> Redirected to dashboard (/organization) successfully!")

        # Wait for dashboard content to load
        self.wait.until(
            EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Departments']"))
        )
        time.sleep(2)

        # [Step 4] Verify UI shows CEO of that company ONLY
        print(f"[Step 4] Verifying Navbar displays company '{COMPANY_NAME}'...")
        navbar_company = self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='navbar-company']"))
        )
        displayed_company_name = navbar_company.text.strip()
        print(f"  -> Displayed Company in Navbar: '{displayed_company_name}'")
        self.assertEqual(
            displayed_company_name,
            COMPANY_NAME,
            f"Expected company name '{COMPANY_NAME}' but found '{displayed_company_name}'"
        )

        # Check user menu to verify CEO designation
        print("[Step 5] Checking User Menu for CEO Designation and Email...")
        user_menu_btn = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='user-menu-button']"))
        )
        user_menu_btn.click()
        time.sleep(1)

        user_menu = self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='user-menu']"))
        )
        menu_text = user_menu.text
        print(f"  -> User Menu Content:\n{menu_text}")

        self.assertIn(CEO_EMAIL, menu_text, f"Expected CEO email '{CEO_EMAIL}' in user menu")
        self.assertIn("CEO", menu_text, "Expected 'CEO' designation in user menu")

        # Verify no data from other companies is displayed
        print("[Step 6] Verifying multi-tenant isolation in UI...")
        self.assertNotIn("ABC Corp", displayed_company_name, "Security Failure: Data from another company leaked!")

        # Pause 5 seconds so the user can clearly see the dashboard with Onnorokom Pathshala and CEO profile
        print("  -> Pausing for 5 seconds to let you view the dashboard as CEO of Onnorokom Pathshala...")
        time.sleep(5)

        # [Step 7] Verify Database Multi-tenant Scoping (CEO of that company only)
        print("[Step 7] Verifying backend database records and tenant isolation...")
        user = User.objects.get(email=CEO_EMAIL)
        company = Company.objects.get(subdomain=SUBDOMAIN)
        employee = Employee.objects.get(user=user)

        # User belongs to this company only
        self.assertEqual(user.company, company, "User is not bound to the registered company.")

        # Employee belongs to this company only
        self.assertEqual(employee.company, company, "Employee is not bound to the registered company.")

        # Designation is CEO
        self.assertEqual(employee.designation.title, "CEO", "Employee designation is not CEO.")

        # Roles belong to this company only
        employee_roles = EmployeeRole.objects.filter(employee=employee)
        for er in employee_roles:
            self.assertEqual(
                er.company,
                company,
                f"Security Failure: Role {er.role.name} belongs to wrong company {er.company}!"
            )
            self.assertEqual(
                er.role.company,
                company,
                f"Security Failure: Role definition belongs to wrong company {er.role.company}!"
            )

        print("  -> ALL CHECKS PASSED: User is authenticated as CEO of Onnorokom Pathshala only!")


if __name__ == "__main__":
    unittest.main()
