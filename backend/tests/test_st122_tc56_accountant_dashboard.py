"""
ST-122 Selenium Test — TC-56: Accountant Dashboard (Finance Metrics Visible, Task Management Hidden)
File: test_st122_tc56_accountant_dashboard.py

Description:
  [Selenium] Log in as an Accountant — expect finance metrics and no Task management numbers

Assignee:
    Montasim Kabir Mahin

Credentials:
    Accountant User: siam@gmail.com (Password: 1234) [Holds manage_finance ONLY]

Run:
    cd backend
    python tests/test_st122_tc56_accountant_dashboard.py
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
from rbac.models import EmployeeRole, Permission, Role
from tenants.models import Company

User = get_user_model()

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://127.0.0.1:8000/api/v1")
COMPANY_SUBDOMAIN = "acme"

ACCOUNTANT_EMAIL = "siam@gmail.com"
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

    dept, _ = Department.objects.get_or_create(company=company, name="Finance")
    desig, _ = Designation.objects.get_or_create(company=company, title="Senior Accountant")

    # 2. Accountant User: siam@gmail.com
    user, _ = User.objects.get_or_create(
        email=ACCOUNTANT_EMAIL,
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
            "employee_code": "SIAM-ACC-001",
        },
    )

    # 3. Grant manage_finance permission ONLY (strip other roles like create_task, manage_employees)
    perm, _ = Permission.objects.get_or_create(
        codename="manage_finance",
        defaults={"name": "Manage Finance", "module": "payroll"},
    )
    accountant_role, _ = Role.objects.get_or_create(
        company=company,
        name="Accountant ST122",
        defaults={"description": "Finance only role"},
    )
    accountant_role.permissions.set([perm])

    EmployeeRole.objects.filter(employee=employee).delete()
    EmployeeRole.objects.create(
        employee=employee,
        role=accountant_role,
        company=company,
    )

    # 4. Seed Salary Structure so Finance metrics and chart show real numbers
    SalaryStructure.objects.update_or_create(
        employee=employee,
        defaults={
            "company": company,
            "base_salary": "75000.00",
            "allowances": {"Transport": 3000, "Medical": 2000},
        },
    )

    return company, employee


class TC56AccountantDashboardSeleniumTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company, cls.accountant_emp = prepare_test_data()

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

    def test_tc56_accountant_dashboard_finance_visible_tasks_hidden(self):
        driver = self.driver
        wait = self.wait

        print("\n=======================================================")
        print("  ST-122 / TC-56: Accountant Dashboard Verification")
        print("  Assignee: Montasim Kabir Mahin")
        print(f"  User: {ACCOUNTANT_EMAIL} (Accountant: Has manage_finance)")
        print("=======================================================")

        # Step 1: Open Login Page
        print(f"\n[1/4] Logging in as Accountant ({ACCOUNTANT_EMAIL})...")
        driver.get(f"{FRONTEND_URL}/login")
        time.sleep(2)

        email_input = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
        )
        password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")

        email_input.clear()
        email_input.send_keys(ACCOUNTANT_EMAIL)
        time.sleep(1)

        password_input.clear()
        password_input.send_keys(PASSWORD)
        time.sleep(1.5)

        driver.find_element(By.XPATH, "//button[normalize-space()='Login']").click()
        wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)
        print("✓ Accountant logged in successfully.")

        # Step 2: Navigate to Dashboard
        print("\n[2/4] Navigating to /dashboard...")
        driver.get(f"{FRONTEND_URL}/dashboard")
        time.sleep(2.5)

        # Step 3: Expect Finance Section with Metrics and Chart
        print("\n[3/4] Expecting Finance section with salary metrics & payroll chart...")
        finance_section = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='dashboard-section-finance']"))
        )
        self.assertTrue(finance_section.is_displayed(), "Finance section MUST be visible to Accountant.")
        print("✓ Verified: Finance section is visible.")

        finance_cards = finance_section.find_elements(By.CSS_SELECTOR, "[data-testid='metric-card']")
        self.assertGreaterEqual(len(finance_cards), 3, "Accountant must see Finance MetricCards.")

        finance_labels = [c.find_element(By.CSS_SELECTOR, "p.text-sm").text for c in finance_cards]
        print(f"      Finance metrics shown: {finance_labels}")
        self.assertIn("Total base payroll / month", finance_labels)
        self.assertIn("Average base salary", finance_labels)
        self.assertIn("Salary structures", finance_labels)

        # Check Finance chart
        finance_chart = finance_section.find_elements(By.CSS_SELECTOR, "[data-testid='chart-card']")
        self.assertGreaterEqual(len(finance_chart), 1, "Finance payroll chart must be present.")
        print("✓ Verified: Finance payroll chart is displayed.")

        # Step 4: Expect NO Task Management numbers and NO People section
        print("\n[4/4] Verifying NO Task management (Team tasks) or People numbers exist...")
        time.sleep(2)

        # Team tasks section (create_task permission required) must NOT be visible
        team_section = driver.find_elements(By.CSS_SELECTOR, "[data-testid='dashboard-section-team']")
        self.assertEqual(len(team_section), 0, "Company Task management numbers must NOT be visible to Accountant.")

        # People section (manage_employees permission required) must NOT be visible
        people_section = driver.find_elements(By.CSS_SELECTOR, "[data-testid='dashboard-section-people']")
        self.assertEqual(len(people_section), 0, "People/Headcount section must NOT be visible to Accountant.")

        # Verify task management metrics are not on the page
        page_source = driver.page_source
        self.assertNotIn("Awaiting review", page_source, "Task management metric 'Awaiting review' must not be shown.")
        self.assertNotIn("Completion rate", page_source, "Task management metric 'Completion rate' must not be shown.")
        print("✓ Verified: Task management numbers (Team tasks) and People numbers are completely HIDDEN.")

        print("\n=======================================================")
        print("🎉 ST-122 / TC-56 Selenium Test: 100% PASSED!")
        print("=======================================================\n")


if __name__ == "__main__":
    unittest.main()
