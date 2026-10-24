"""
ST-124 Selenium Test — TC-60: CEO Blocked from Admin Panel & No Admin Menu Items
File: test_st124_tc60_ceo_blocked_from_admin.py

Description:
  [Selenium] As a CEO open the admin panel address — expect access blocked and no menu item.

Credentials:
    CEO: siam@gmail.com (Password: 1234, Company: Acme Corp)

Run:
    cd backend
    python tests/test_st124_tc60_ceo_blocked_from_admin.py
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
from tenants.models import Company

User = get_user_model()

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from selenium_helpers import FRONTEND_URL  # noqa: E402  (one shared place: tests/selenium_helpers.py)
COMPANY_SUBDOMAIN = "acme"
CEO_EMAIL = "siam@gmail.com"
PASSWORD = "1234"


def prepare_test_data():
    """Ensure Acme Corp and CEO exist with proper non-platform-admin privileges."""
    company, _ = Company.objects.get_or_create(
        subdomain=COMPANY_SUBDOMAIN,
        defaults={"name": "Acme Corp", "is_active": True},
    )

    ceo_user, _ = User.objects.get_or_create(
        email=CEO_EMAIL,
        defaults={"company": company, "is_active": True, "is_platform_admin": False},
    )
    ceo_user.set_password(PASSWORD)
    ceo_user.company = company
    ceo_user.is_active = True
    ceo_user.is_platform_admin = False
    ceo_user.save()

    dept, _ = Department.objects.get_or_create(
        company=company, name="Executive"
    )
    desig, _ = Designation.objects.get_or_create(
        company=company, title="CEO"
    )
    ceo_emp, _ = Employee.objects.get_or_create(
        user=ceo_user,
        defaults={
            "company": company,
            "employee_code": "EMP-ACME-CEO",
            "department": dept,
            "designation": desig,
        },
    )

    ceo_role, _ = Role.objects.get_or_create(
        company=company,
        name="CEO",
        defaults={"description": "Chief Executive Officer"},
    )
    all_perms = Permission.objects.all()
    ceo_role.permissions.set(all_perms)

    EmployeeRole.objects.get_or_create(
        employee=ceo_emp,
        role=ceo_role,
        defaults={"company": company},
    )

    return company, ceo_user, ceo_emp


class TC60CEOBlockedFromAdminSeleniumTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company, cls.ceo_user, cls.ceo_emp = prepare_test_data()

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

    def test_tc60_ceo_blocked_from_admin_flow(self):
        driver = self.driver
        wait = self.wait

        print("\n=======================================================")
        print("  ST-124 / TC-60: CEO Blocked from Admin Panel & Menu")
        print("=======================================================")

        # Step 1: Log in as CEO
        print(f"\n[1/4] Logging in as CEO ({CEO_EMAIL})...")
        driver.get(f"{FRONTEND_URL}/login")
        time.sleep(2)

        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']"))).send_keys(CEO_EMAIL)
        driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(PASSWORD)
        driver.find_element(By.XPATH, "//button[normalize-space()='Login']").click()
        wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)
        print("✓ CEO logged in successfully.")

        # Step 2: Verify Sidebar does NOT contain Platform Admin menu items
        print("\n[2/4] Inspecting sidebar navigation for Platform Admin links...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='sidebar']")))
        time.sleep(1.5)

        admin_links_to_check = [
            ("Companies", "[data-testid='sidebar-link-Companies']"),
            ("Payments", "[data-testid='sidebar-link-Payments']"),
            ("Subscriptions", "[data-testid='sidebar-link-Subscriptions']"),
            ("Support Tickets", "[data-testid='sidebar-link-Support Tickets']"),
            ("Access Requests", "[data-testid='sidebar-link-Access Requests']"),
            ("Activity", "[data-testid='sidebar-link-Activity']"),
        ]

        for label, selector in admin_links_to_check:
            found = driver.find_elements(By.CSS_SELECTOR, selector)
            self.assertEqual(
                len(found), 0,
                f"Platform Admin item '{label}' should NOT appear in CEO sidebar!"
            )
            print(f"      ✓ Checked '{label}': Not present in CEO menu.")

        print("✓ Verified: CEO sidebar contains NO Platform Admin menu items.")

        # Step 3: Directly navigate to /admin/companies
        print("\n[3/4] CEO attempting direct URL navigation to /admin/companies...")
        driver.get(f"{FRONTEND_URL}/admin/companies")
        time.sleep(2.5)

        # Expect access blocked screen
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='admin-denied']")))
        denied_element = driver.find_element(By.CSS_SELECTOR, "[data-testid='admin-denied']")
        denied_text = denied_element.text
        print(f"      Access Denied message displayed:\n      '{denied_text.strip()}'")

        self.assertIn(
            "Platform Admin access only",
            denied_text,
            "Expected 'Platform Admin access only' notice."
        )
        # Ensure company data table is NOT exposed
        companies_tables = driver.find_elements(By.CSS_SELECTOR, "[data-testid='companies-table']")
        self.assertEqual(len(companies_tables), 0, "Companies table must NOT be rendered when access is denied.")
        print("✓ Verified: CEO direct access to /admin/companies is BLOCKED.")

        # Step 4: Directly navigate to /admin/tickets
        print("\n[4/4] CEO attempting direct URL navigation to /admin/tickets...")
        driver.get(f"{FRONTEND_URL}/admin/tickets")
        time.sleep(2)

        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='admin-denied']")))
        tickets_denied = driver.find_element(By.CSS_SELECTOR, "[data-testid='admin-denied']").text
        self.assertIn("Platform Admin access only", tickets_denied)
        print("✓ Verified: CEO direct access to /admin/tickets is also BLOCKED.")

        print("\n=======================================================")
        print("🎉 ST-124 / TC-60 Selenium Test: 100% PASSED!")
        print("=======================================================\n")


if __name__ == "__main__":
    unittest.main()
