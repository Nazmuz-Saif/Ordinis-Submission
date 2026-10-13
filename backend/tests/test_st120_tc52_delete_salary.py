"""
ST-120 Selenium Test — TC-52: Delete Salary Structure & No Permission Menu
File: test_st120_tc52_delete_salary.py

Description:
  [Selenium] Delete a Salary Structure — expect it gone from the list;
  log in without the Permission — expect no menu item

Credentials:
    Finance Admin: siam@gmail.com (Password: 1234) [Has manage_finance]
    Regular Employee: dev_siam@acme.com (Password: 1234) [No finance permission]

Run:
    cd backend
    python tests/test_st120_tc52_delete_salary.py
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
REGULAR_EMPLOYEE_EMAIL = "dev_siam@acme.com"


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

    regular_user, _ = User.objects.get_or_create(
        email=REGULAR_EMPLOYEE_EMAIL,
        defaults={"company": company, "is_active": True},
    )
    regular_user.company = company
    regular_user.is_active = True
    regular_user.set_password(PASSWORD)
    regular_user.save()

    regular_employee, _ = Employee.objects.get_or_create(
        user=regular_user,
        defaults={"company": company, "employee_code": "DEV-SIAM-001"},
    )

    # Ensure regular employee does NOT have manage_finance
    EmployeeRole.objects.filter(
        employee=regular_employee,
        role__permissions__codename="manage_finance",
    ).delete()

    # Pre-create salary structure so there is something to delete
    SalaryStructure.objects.update_or_create(
        employee=regular_employee,
        defaults={
            "company": company,
            "base_salary": "50000.00",
            "allowances": {"Transport": 2000},
        },
    )

    return company, finance_employee, regular_employee


class TC52DeleteSalaryStructureTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company, cls.finance_emp, cls.regular_emp = prepare_test_data()

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

    def login(self, email, password):
        driver = self.driver
        wait = self.wait

        driver.get(f"{FRONTEND_URL}/login")
        time.sleep(2)

        email_input = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
        )
        password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")

        email_input.clear()
        email_input.send_keys(email)
        time.sleep(1)

        password_input.clear()
        password_input.send_keys(password)
        time.sleep(1.5)

        driver.find_element(By.XPATH, "//button[normalize-space()='Login']").click()
        wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)

    def clear_session(self):
        self.driver.execute_script("window.localStorage.clear();")
        self.driver.delete_all_cookies()
        time.sleep(1.5)

    def test_delete_salary_structure_and_no_permission_menu(self):
        driver = self.driver
        wait = self.wait

        print("\n=======================================================")
        print("  TC-52: Delete Salary Structure & No Permission Menu")
        print(f"  User: {FINANCE_EMAIL}")
        print("=======================================================")

        # Part 1: Login with finance permission and delete the salary structure
        print(f"\n[1/4] Logging in as {FINANCE_EMAIL} (has manage_finance)...")
        self.login(FINANCE_EMAIL, PASSWORD)
        print("✓ Logged in as Finance Admin.")

        print("      Navigating to /payroll/salary-structures...")
        driver.get(f"{FRONTEND_URL}/payroll/salary-structures")
        time.sleep(2)

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='salary-row']")))
        self.assertIn(REGULAR_EMPLOYEE_EMAIL, driver.page_source)
        time.sleep(2)

        print(f"\n[2/4] Deleting Salary Structure for {REGULAR_EMPLOYEE_EMAIL}...")
        delete_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='delete-salary']"))
        )
        delete_btn.click()
        time.sleep(1.5)

        # Accept confirmation alert
        alert = driver.switch_to.alert
        print(f"      Accepting alert: '{alert.text}'")
        alert.accept()
        time.sleep(2.5)

        # Expect it gone from list
        driver.refresh()
        time.sleep(2)
        self.assertNotIn(
            REGULAR_EMPLOYEE_EMAIL,
            driver.page_source,
            "Deleted salary structure should be gone from the list",
        )
        print("✓ Salary Structure successfully deleted and gone from list.")

        # Part 2: Login as regular employee without finance permission
        print(f"\n[3/4] Clearing session & logging in as {REGULAR_EMPLOYEE_EMAIL} (No finance permission)...")
        self.clear_session()
        self.login(REGULAR_EMPLOYEE_EMAIL, PASSWORD)
        print(f"✓ Logged in as {REGULAR_EMPLOYEE_EMAIL}.")

        # Part 3: Verify no menu item in sidebar
        print("\n[4/4] Verifying 'Salary Structures' menu item is HIDDEN in sidebar...")
        time.sleep(2)

        salary_links = driver.find_elements(
            By.CSS_SELECTOR, "[data-testid='sidebar-link-Salary Structures']"
        )
        self.assertEqual(
            len(salary_links),
            0,
            "User without manage_finance must NOT see 'Salary Structures' menu item.",
        )

        all_salary_hrefs = driver.find_elements(
            By.CSS_SELECTOR, "a[href='/payroll/salary-structures']"
        )
        self.assertEqual(
            len(all_salary_hrefs),
            0,
            "No link to /payroll/salary-structures should exist in the navigation.",
        )
        print("✓ Verified: No 'Salary Structures' menu item present in sidebar.")

        # Check direct URL navigation
        print("      Checking direct URL navigation to /payroll/salary-structures...")
        driver.get(f"{FRONTEND_URL}/payroll/salary-structures")
        time.sleep(2)

        no_access_elem = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='salary-no-access']"))
        )
        self.assertTrue(no_access_elem.is_displayed(), "Direct access should show restricted access screen.")
        print("✓ Verified: Direct URL displays 'Salary data is restricted'.")

        print("\n=======================================================")
        print("🎉 ST-120 / TC-52 Selenium Test: 100% PASSED!")
        print("=======================================================")


if __name__ == "__main__":
    unittest.main()
