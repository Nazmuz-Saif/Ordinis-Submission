"""
Selenium Test:
Log in as an Employee without the manage_departments Permission
and try to add a Department — expect an error message and no record created.
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

from organization.models import Company, Department, Employee
from rbac.models import EmployeeRole

User = get_user_model()

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
EMPLOYEE_EMAIL = "mahinabc@gmail.com"
PASSWORD = "TestPass123!"
DEPARTMENT_NAME = "HR"


def setup_test_data():
    """Sets up an employee without the manage_departments permission under active company."""
    # 1. Fetch active company (abc or first active)
    company = Company.objects.filter(subdomain="abc", is_active=True).first()
    if not company:
        company = Company.objects.filter(is_active=True).first()
    if not company:
        company = Company.objects.create(name="ABC Corp", subdomain="abc", is_active=True)

    # 2. Fetch or create test user
    user, _ = User.objects.get_or_create(
        email=EMPLOYEE_EMAIL,
        defaults={"company": company}
    )
    user.company = company
    user.set_password(PASSWORD)
    user.save()

    # 3. Fetch or create employee profile
    employee, _ = Employee.objects.get_or_create(
        user=user,
        defaults={"company": company, "employee_code": "ABC-EMP002"}
    )

    # 4. Remove any role containing manage_departments permission
    EmployeeRole.objects.filter(
        employee=employee,
        role__permissions__codename="manage_departments"
    ).delete()

    # 5. Clean up any existing 'HR' department
    Department.objects.filter(company=company, name__iexact=DEPARTMENT_NAME).delete()

    return company, employee


class DepartmentPermissionSeleniumTest(unittest.TestCase):
    def setUp(self):
        self.company, self.employee = setup_test_data()
        options = webdriver.ChromeOptions()
        # Headless mode can be toggled via environment variable if desired
        if os.environ.get("HEADLESS", "0") == "1":
            options.add_argument("--headless=new")
        self.driver = webdriver.Chrome(options=options)
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 20)

    def tearDown(self):
        self.driver.quit()

    def test_unauthorized_employee_cannot_add_department(self):
        """
        Test flow:
        1. Navigate to /login and submit credentials.
        2. Wait for successful authentication and redirect to /organization.
        3. Attempt to add 'HR' department.
        4. Expect an error message on screen.
        5. Verify no record was created in the database.
        """
        driver = self.driver
        print("\n[Step 1] Navigating to Login page...")
        driver.get(f"{FRONTEND_URL}/login")
        time.sleep(2)  # Pause to clearly see the login page

        # 1. Fill login credentials
        email_input = self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
        )
        email_input.clear()
        email_input.send_keys(EMPLOYEE_EMAIL)

        password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password_input.clear()
        password_input.send_keys(PASSWORD)
        time.sleep(1.5)  # Pause to see typed credentials

        login_btn = driver.find_element(By.XPATH, "//button[normalize-space()='Login']")
        login_btn.click()
        print(f"[Step 2] Submitted login for {EMPLOYEE_EMAIL}...")

        # 2. Wait until React redirects to /organization after authentication
        print("[Step 3] Waiting for authentication and navigation to /organization...")
        self.wait.until(EC.url_contains("/organization"))

        # 3. Wait for Departments heading to be visible
        self.wait.until(
            EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Departments']"))
        )
        print("  -> Departments page loaded successfully.")
        time.sleep(2.5)  # Pause to clearly view the loaded Departments page

        # 4. Find the department input and Add button
        dept_input = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='New department name']"))
        )
        add_btn = driver.find_element(By.XPATH, "//button[@type='submit'][contains(., 'Add')]")

        # 5. Type 'HR' and click Add
        dept_input.clear()
        dept_input.send_keys(DEPARTMENT_NAME)
        print(f"[Step 4] Typed '{DEPARTMENT_NAME}' into form...")
        time.sleep(2.5)  # Pause to clearly see 'HR' written in the input box!

        print("  -> Clicking '+ Add' button now...")
        add_btn.click()

        # 6. Expect an error message to appear on screen
        print("[Step 5] Checking for error message on screen...")
        error_element = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, "//p[contains(@class, 'text-[#DC2626]')]"))
        )
        error_text = error_element.text.strip()
        print(f"  -> Error Message Displayed: \"{error_text}\"")

        self.assertTrue(
            len(error_text) > 0,
            "Security Test Failed: Expected an error message, but none was displayed."
        )

        # Pause 5 full seconds so user can clearly see the red error message on screen!
        print("  -> Pausing for 5 seconds to let you view the red error message...")
        time.sleep(5)

        # 7. Expect no record created in database
        print(f"[Step 6] Checking database for '{DEPARTMENT_NAME}' department...")
        time.sleep(1)
        department_exists = Department.objects.filter(
            company=self.company,
            name__iexact=DEPARTMENT_NAME
        ).exists()

        self.assertFalse(
            department_exists,
            f"Security Failure: Department '{DEPARTMENT_NAME}' was created in the database!"
        )
        print(f"  -> Database verified: '{DEPARTMENT_NAME}' does NOT exist in DB.")
        print("\n=======================================================")
        print("✅ TEST PASSED: Unauthorized employee correctly blocked!")
        print("  - Error message was displayed on the screen.")
        print("  - No department record was created in the database.")
        print("=======================================================\n")


if __name__ == "__main__":
    unittest.main()
