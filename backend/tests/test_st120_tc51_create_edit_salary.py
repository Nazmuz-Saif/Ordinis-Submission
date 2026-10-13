"""
ST-120 Selenium Test — TC-51: Create & Edit Salary Structure
File: test_st120_tc51_create_edit_salary.py

Description:
  [Selenium] Log in with the finance Permission, create a Salary Structure and edit it
  — expect the saved values in the list (TC-46 run again)

Credentials:
    Finance Admin: siam@gmail.com (Password: 1234) [Has manage_finance]
    Target Employee: dev_siam@acme.com (Password: 1234)

Run:
    cd backend
    python tests/test_st120_tc51_create_edit_salary.py
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
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select

from organization.models import Designation, Employee
from payroll.models import SalaryStructure
from rbac.models import EmployeeRole, Permission, Role
from tenants.models import Company

User = get_user_model()

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://127.0.0.1:8000/api/v1")
COMPANY_SUBDOMAIN = "acme"

FINANCE_EMAIL = "siam@gmail.com"
PASSWORD = "1234"
TARGET_EMPLOYEE_EMAIL = "dev_siam@acme.com"


def prepare_test_data():
    company, _ = Company.objects.get_or_create(
        subdomain=COMPANY_SUBDOMAIN,
        defaults={"name": "Acme Corp", "is_active": True},
    )
    if not company.is_active:
        company.is_active = True
        company.save()

    finance_user, _ = User.objects.get_or_create(
        email=FINANCE_EMAIL,
        defaults={"company": company, "is_active": True},
    )
    finance_user.company = company
    finance_user.is_active = True
    finance_user.set_password(PASSWORD)
    finance_user.save()

    finance_employee, _ = Employee.objects.get_or_create(
        user=finance_user,
        defaults={"company": company, "employee_code": "SIAM-FIN-001"},
    )

    perm, _ = Permission.objects.get_or_create(
        codename="manage_finance",
        defaults={"name": "Manage Finance", "module": "payroll"},
    )
    finance_role, _ = Role.objects.get_or_create(
        company=company,
        name="Finance Officer Role",
        defaults={"description": "Role with finance permission"},
    )
    finance_role.permissions.add(perm)

    EmployeeRole.objects.get_or_create(
        employee=finance_employee,
        role=finance_role,
        defaults={"company": company},
    )

    target_user, _ = User.objects.get_or_create(
        email=TARGET_EMPLOYEE_EMAIL,
        defaults={"company": company, "is_active": True},
    )
    target_user.company = company
    target_user.is_active = True
    target_user.set_password(PASSWORD)
    target_user.save()

    desig, _ = Designation.objects.get_or_create(company=company, title="Developer")

    target_employee, _ = Employee.objects.get_or_create(
        user=target_user,
        defaults={"company": company, "designation": desig, "employee_code": "DEV-SIAM-001"},
    )

    # Clean up previous salary structure for target employee before test
    SalaryStructure.objects.filter(employee=target_employee).delete()

    return company, finance_employee, target_employee


class TC51CreateEditSalaryStructureTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company, cls.finance_emp, cls.target_emp = prepare_test_data()

    def setUp(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 20)

    def tearDown(self):
        time.sleep(2)
        try:
            self.driver.quit()
        except Exception:
            pass

    def test_create_and_edit_salary_structure(self):
        driver = self.driver
        wait = self.wait

        print("\n=======================================================")
        print("  TC-51: Create & Edit Salary Structure")
        print(f"  User: {FINANCE_EMAIL}")
        print("=======================================================")

        # Step 1: Open Login Page
        print(f"\n[1/6] Opening Login Page ({FRONTEND_URL}/login)...")
        driver.get(f"{FRONTEND_URL}/login")
        time.sleep(2)

        email_input = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
        )
        password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")

        print(f"      Entering Email: {FINANCE_EMAIL}")
        email_input.clear()
        email_input.send_keys(FINANCE_EMAIL)
        time.sleep(1)

        print("      Entering Password: ****")
        password_input.clear()
        password_input.send_keys(PASSWORD)
        time.sleep(1.5)

        print("      Clicking Login button...")
        driver.find_element(By.XPATH, "//button[normalize-space()='Login']").click()

        wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)
        print("✓ Logged in successfully.")

        # Step 2: Navigate to Salary Structures page
        print("\n[2/6] Navigating to /payroll/salary-structures...")
        driver.get(f"{FRONTEND_URL}/payroll/salary-structures")
        time.sleep(2)

        new_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='new-salary-button']"))
        )
        self.assertTrue(new_btn.is_displayed(), "New Salary Structure button must be visible.")
        print("✓ Salary Structures page loaded with finance access.")
        time.sleep(2)

        # Step 3: Open Modal & Create Salary Structure
        print(f"\n[3/6] Creating Salary Structure for {TARGET_EMPLOYEE_EMAIL}...")
        new_btn.click()
        time.sleep(2)

        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='salary-form']")))

        print(f"      Selecting employee: {TARGET_EMPLOYEE_EMAIL}")
        emp_select = Select(driver.find_element(By.CSS_SELECTOR, "[data-testid='salary-employee']"))
        emp_select.select_by_value(str(self.target_emp.id))
        time.sleep(1.5)

        print("      Entering Base Salary: 50000")
        base_salary_input = driver.find_element(By.CSS_SELECTOR, "[data-testid='salary-base']")
        base_salary_input.clear()
        base_salary_input.send_keys("50000")
        time.sleep(1.5)

        print("      Adding Allowance: House Rent = 8000")
        add_allowance_btn = driver.find_element(By.CSS_SELECTOR, "[data-testid='add-allowance']")
        add_allowance_btn.click()
        time.sleep(1)

        name_input = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='salary-allowance-name']"))
        )
        amount_input = driver.find_element(By.CSS_SELECTOR, "[data-testid='salary-allowance-amount']")

        name_input.clear()
        name_input.send_keys("House Rent")
        time.sleep(1)
        amount_input.clear()
        amount_input.send_keys("8000")
        time.sleep(1.5)

        print("      Submitting form (Clicking Create)...")
        save_btn = driver.find_element(By.CSS_SELECTOR, "[data-testid='salary-save']")
        save_btn.click()

        wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "[data-testid='salary-form']")))
        time.sleep(2.5)
        print("✓ Salary Structure created successfully.")

        # Step 4: Verify in List
        print("\n[4/6] Verifying created Salary Structure in list table...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='salary-row']")))
        time.sleep(2)

        page_source = driver.page_source
        self.assertIn(TARGET_EMPLOYEE_EMAIL, page_source, f"Expected {TARGET_EMPLOYEE_EMAIL} in table.")
        self.assertIn("50,000.00", page_source, "Expected Base Salary 50,000.00 in table.")
        self.assertIn("House Rent", page_source, "Expected House Rent allowance in table.")
        self.assertIn("8,000.00", page_source, "Expected Allowance amount 8,000.00 in table.")
        self.assertIn("58,000.00", page_source, "Expected Gross amount 58,000.00 in table.")
        print("✓ Verified created values: Base=50,000.00, House Rent=8,000.00, Gross=58,000.00")

        # Step 5: Edit the Salary Structure
        print(f"\n[5/6] Editing Salary Structure for {TARGET_EMPLOYEE_EMAIL}...")
        edit_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='edit-salary']"))
        )
        time.sleep(1.5)
        edit_btn.click()
        time.sleep(2)

        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='salary-form']")))

        print("      Updating Base Salary to: 65000")
        edit_base_input = driver.find_element(By.CSS_SELECTOR, "[data-testid='salary-base']")
        edit_base_input.send_keys(Keys.CONTROL + "a")
        edit_base_input.send_keys(Keys.BACKSPACE)
        edit_base_input.send_keys("65000")
        time.sleep(2)

        print("      Saving changes...")
        edit_save_btn = driver.find_element(By.CSS_SELECTOR, "[data-testid='salary-save']")
        edit_save_btn.click()

        wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "[data-testid='salary-form']")))
        time.sleep(2.5)
        print("✓ Changes saved!")

        # Step 6: Verify Updated Values in List
        print("\n[6/6] Verifying updated values in list table...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='salary-row']")))
        time.sleep(3)

        updated_source = driver.page_source
        self.assertIn("65,000.00", updated_source, "Expected updated base salary 65,000.00 in table.")
        self.assertIn("73,000.00", updated_source, "Expected updated gross amount 73,000.00 in table.")
        print("✓ Verified updated values: Base=65,000.00, Gross=73,000.00")

        print("\n=======================================================")
        print("🎉 ST-120 / TC-51 Selenium Test: 100% PASSED!")
        print("=======================================================\n")


if __name__ == "__main__":
    unittest.main()
