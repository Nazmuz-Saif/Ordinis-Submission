"""
ST-122 Selenium Test — TC-54: CEO Dashboard with MetricCards and Charts
File: test_st122_tc54_ceo_dashboard.py

Description:
  [Selenium] Log in as a CEO — expect the dashboard with MetricCards showing numbers and a chart

Assignee:
    Montasim Kabir Mahin

Credentials:
    CEO User: siam@gmail.com (Password: 1234)

Run:
    cd backend
    python tests/test_st122_tc54_ceo_dashboard.py
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
from rbac.models import EmployeeRole, Permission, Role
from tasks.models import Task
from tenants.models import Company

User = get_user_model()

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://127.0.0.1:8000/api/v1")
COMPANY_SUBDOMAIN = "acme"

CEO_EMAIL = "siam@gmail.com"
PASSWORD = "1234"


def prepare_test_data():
    company, _ = Company.objects.get_or_create(
        subdomain=COMPANY_SUBDOMAIN,
        defaults={"name": "Acme Corp", "is_active": True},
    )
    if not company.is_active:
        company.is_active = True
        company.save()

    dept, _ = Department.objects.get_or_create(company=company, name="Engineering")
    desig, _ = Designation.objects.get_or_create(company=company, title="CEO")

    # CEO User: siam@gmail.com
    ceo_user, _ = User.objects.get_or_create(
        email=CEO_EMAIL,
        defaults={"company": company, "is_active": True},
    )
    ceo_user.company = company
    ceo_user.is_active = True
    ceo_user.set_password(PASSWORD)
    ceo_user.save()

    ceo_employee, _ = Employee.objects.get_or_create(
        user=ceo_user,
        defaults={
            "company": company,
            "department": dept,
            "designation": desig,
            "employee_code": "SIAM-CEO-001",
        },
    )

    # Grant all permissions for CEO
    ceo_role, _ = Role.objects.get_or_create(
        company=company,
        name="CEO Full Access Role",
        defaults={"description": "Full access CEO role"},
    )
    all_perms = Permission.objects.filter(
        codename__in=["create_task", "manage_employees", "manage_finance", "manage_departments"]
    )
    ceo_role.permissions.set(all_perms)

    EmployeeRole.objects.get_or_create(
        employee=ceo_employee,
        role=ceo_role,
        defaults={"company": company},
    )

    # Seed tasks for chart visualization
    Task.objects.filter(company=company, title__startswith="ST122-").delete()
    for status in ["not_started", "in_progress", "completed"]:
        Task.objects.create(
            company=company,
            title=f"ST122-Dashboard Task {status}",
            assigned_to=ceo_employee,
            assigned_by=ceo_employee,
            priority="high",
            status=status,
        )

    return company, ceo_employee


class TC54CeoDashboardSeleniumTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company, cls.ceo_emp = prepare_test_data()

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

    def test_tc54_ceo_dashboard_metric_cards_and_charts(self):
        driver = self.driver
        wait = self.wait

        print("\n=======================================================")
        print("  ST-122 / TC-54: CEO Dashboard with MetricCards & Charts")
        print("  Assignee: Montasim Kabir Mahin")
        print(f"  User: {CEO_EMAIL}")
        print("=======================================================")

        # Step 1: Open Login Page
        print(f"\n[1/4] Opening Login Page at {FRONTEND_URL}/login...")
        driver.get(f"{FRONTEND_URL}/login")
        time.sleep(2)

        email_input = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
        )
        password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")

        print(f"      Entering Email: {CEO_EMAIL}")
        email_input.clear()
        email_input.send_keys(CEO_EMAIL)
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

        # Step 2: Navigate to Dashboard
        print("\n[2/4] Navigating to /dashboard...")
        driver.get(f"{FRONTEND_URL}/dashboard")
        time.sleep(2)

        # Step 3: Verify MetricCards
        print("\n[3/4] Expecting Dashboard MetricCards showing numbers...")
        metric_cards = wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-testid='metric-card']"))
        )
        time.sleep(2)

        self.assertGreaterEqual(len(metric_cards), 4, "CEO should see multiple MetricCards on dashboard.")
        print(f"✓ Found {len(metric_cards)} MetricCards on the CEO dashboard.")

        sample_values = []
        for card in metric_cards[:6]:
            try:
                label = card.find_element(By.CSS_SELECTOR, "p.text-sm").text
                val = card.find_element(By.CSS_SELECTOR, "[data-testid='metric-value']").text
                sample_values.append(f"{label}: {val}")
            except Exception:
                pass

        print("      Sample MetricCard values found:")
        for sample in sample_values:
            print(f"        • {sample}")

        metric_values = driver.find_elements(By.CSS_SELECTOR, "[data-testid='metric-value']")
        self.assertTrue(any(v.text.strip() != "" for v in metric_values), "MetricCards must display numeric values.")
        print("✓ Verified: MetricCards successfully display numbers.")

        # Step 4: Verify Charts
        print("\n[4/4] Expecting Charts on the Dashboard...")
        time.sleep(2)

        chart_cards = wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-testid='chart-card']"))
        )
        self.assertGreaterEqual(len(chart_cards), 1, "At least one ChartCard must be present on dashboard.")
        print(f"✓ Found {len(chart_cards)} ChartCards on the CEO dashboard.")

        svg_charts = driver.find_elements(By.CSS_SELECTOR, "[data-testid='chart-card'] svg")
        self.assertGreaterEqual(len(svg_charts), 1, "ChartCard must contain rendered chart SVG elements.")
        print(f"✓ Found {len(svg_charts)} rendered SVG chart visualizations.")

        print("\n=======================================================")
        print("🎉 ST-122 / TC-54 Selenium Test: 100% PASSED!")
        print("=======================================================\n")


if __name__ == "__main__":
    unittest.main()
