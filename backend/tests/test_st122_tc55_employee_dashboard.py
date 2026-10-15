"""
ST-122 Selenium Test — TC-55: Regular Employee Dashboard Privacy
File: test_st122_tc55_employee_dashboard.py

Description:
  [Selenium] Log in as an Employee — expect only Employee metrics and no salary or company-wide numbers

Assignee:
    Montasim Kabir Mahin

Credentials:
    Regular Employee: siam@gmail.com (Password: 1234) [No management/finance roles]

Run:
    cd backend
    python tests/test_st122_tc55_employee_dashboard.py
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

from organization.models import Department, Designation, Employee
from payroll.models import SalaryStructure
from rbac.models import EmployeeRole
from tasks.models import Task
from tenants.models import Company

User = get_user_model()

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from selenium_helpers import FRONTEND_URL, BACKEND_API_URL  # noqa: E402  (one shared place: tests/selenium_helpers.py)
COMPANY_SUBDOMAIN = "acme"

EMPLOYEE_EMAIL = "siam@gmail.com"
PASSWORD = "1234"


def prepare_test_data():
    # 1. Company: Acme Corp
    company, _ = Company.objects.get_or_create(
        subdomain=COMPANY_SUBDOMAIN,
        defaults={"name": "Acme Corp", "is_active": True},
    )
    if not company.is_active:
        company.is_active = True
        company.save()

    dept, _ = Department.objects.get_or_create(company=company, name="Engineering")
    desig, _ = Designation.objects.get_or_create(company=company, title="Junior Developer")

    # 2. Regular Employee User: siam@gmail.com
    user, _ = User.objects.get_or_create(
        email=EMPLOYEE_EMAIL,
        defaults={"company": company, "is_active": True},
    )
    user.company = company
    user.is_active = True
    user.set_password(PASSWORD)
    user.save()

    employee, _ = Employee.objects.get_or_create(
        user=user,
        defaults={
            "company": company,
            "department": dept,
            "designation": desig,
            "employee_code": "SIAM-REG-001",
        },
    )

    # 3. Strip all roles so user is a pure regular employee without management/finance permissions
    EmployeeRole.objects.filter(employee=employee).delete()

    # 4. Seed company confidential salary data (to prove it is hidden from this employee)
    SalaryStructure.objects.update_or_create(
        employee=employee,
        defaults={"company": company, "base_salary": "95000.00", "allowances": {"Bonus": 5000}},
    )

    # 5. Seed a personal task for the employee
    Task.objects.filter(company=company, assigned_to=employee).delete()
    Task.objects.create(
        company=company,
        title="My Assigned Task",
        assigned_to=employee,
        priority="medium",
        status="in_progress",
    )

    return company, employee


class TC55EmployeeDashboardSeleniumTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company, cls.employee = prepare_test_data()

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

    def test_tc55_employee_dashboard_privacy(self):
        driver = self.driver
        wait = self.wait

        print("\n=======================================================")
        print("  ST-122 / TC-55: Regular Employee Dashboard Privacy")
        print("  Assignee: Montasim Kabir Mahin")
        print(f"  User: {EMPLOYEE_EMAIL} (Regular Employee, No Admin Roles)")
        print("=======================================================")

        # Step 1: Open Login Page
        print(f"\n[1/4] Logging in as regular employee {EMPLOYEE_EMAIL}...")
        driver.get(f"{FRONTEND_URL}/login")
        time.sleep(2)

        email_input = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
        )
        password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")

        email_input.clear()
        email_input.send_keys(EMPLOYEE_EMAIL)
        time.sleep(1)

        password_input.clear()
        password_input.send_keys(PASSWORD)
        time.sleep(1.5)

        driver.find_element(By.XPATH, "//button[normalize-space()='Login']").click()
        wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)
        print("✓ Regular employee logged in successfully.")

        # Step 2: Navigate to Dashboard
        print("\n[2/4] Navigating to /dashboard...")
        driver.get(f"{FRONTEND_URL}/dashboard")
        time.sleep(2.5)

        # Step 3: Expect ONLY Employee Section ("My work")
        print("\n[3/4] Expecting ONLY Employee personal metrics ('My work')...")
        me_section = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='dashboard-section-me']"))
        )
        self.assertTrue(me_section.is_displayed(), "Employee personal 'My work' section must be visible.")
        print("✓ Verified: Employee personal section ('My work') is displayed.")

        # Inspect personal cards
        personal_cards = me_section.find_elements(By.CSS_SELECTOR, "[data-testid='metric-card']")
        self.assertEqual(len(personal_cards), 4, "Regular employee must see exactly 4 personal MetricCards.")

        personal_labels = [c.find_element(By.CSS_SELECTOR, "p.text-sm").text for c in personal_cards]
        print(f"      Personal metrics shown: {personal_labels}")
        self.assertIn("Open tasks", personal_labels)
        self.assertIn("Attendance today", personal_labels)

        # Step 4: Expect NO salary or company-wide numbers
        print("\n[4/4] Verifying NO salary or company-wide sections exist...")
        time.sleep(2)

        # Team section (Company-wide tasks) should NOT exist
        team_section = driver.find_elements(By.CSS_SELECTOR, "[data-testid='dashboard-section-team']")
        self.assertEqual(len(team_section), 0, "Company-wide Team tasks section must NOT be visible to regular employee.")

        # People section (Headcount & company attendance) should NOT exist
        people_section = driver.find_elements(By.CSS_SELECTOR, "[data-testid='dashboard-section-people']")
        self.assertEqual(len(people_section), 0, "Company-wide People/Headcount section must NOT be visible to regular employee.")

        # Finance section (Confidential salaries) should NOT exist
        finance_section = driver.find_elements(By.CSS_SELECTOR, "[data-testid='dashboard-section-finance']")
        self.assertEqual(len(finance_section), 0, "Confidential Finance/Salary section must NOT be visible to regular employee.")

        # Verify page text does not expose confidential salary keywords
        page_source = driver.page_source
        self.assertNotIn("Total base payroll", page_source, "Salary totals must not be visible to employee.")
        self.assertNotIn("Average base salary", page_source, "Average salary must not be visible to employee.")
        self.assertNotIn("Salary structures", page_source, "Salary structures metrics must not be visible to employee.")
        print("✓ Verified: Team tasks, People headcount, and Finance salary sections are completely HIDDEN.")

        print("\n=======================================================")
        print("🎉 ST-122 / TC-55 Selenium Test: 100% PASSED!")
        print("=======================================================")


if __name__ == "__main__":
    unittest.main()
