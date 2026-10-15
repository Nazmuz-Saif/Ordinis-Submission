"""
ST-123 Selenium Test — TC-57: Support Access Request Creation and CEO Listing
File: test_st123_tc57_support_access_request.py

Description:
  [Selenium] As a Platform Admin send a Support Access Request with a reason
  — expect it Pending; as the CEO see it in the list

Credentials:
    Platform Admin: platform_admin@ordinis.com (Password: 1234)
    CEO: siam@gmail.com (Password: 1234)

Run:
    cd backend
    python tests/test_st123_tc57_support_access_request.py
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
from platform_admin.models import SupportAccessRequest
from platform_admin.services import create_request
from rbac.models import EmployeeRole, Permission, Role
from tenants.models import Company

User = get_user_model()

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from selenium_helpers import FRONTEND_URL, BACKEND_API_URL  # noqa: E402  (one shared place: tests/selenium_helpers.py)
COMPANY_SUBDOMAIN = "acme"

ADMIN_EMAIL = "platform_admin@ordinis.com"
CEO_EMAIL = "siam@gmail.com"
PASSWORD = "1234"
REQUEST_REASON = f"Investigating system performance issue {int(time.time())}"


def prepare_test_data():
    # 1. Company
    company, _ = Company.objects.get_or_create(
        subdomain=COMPANY_SUBDOMAIN,
        defaults={"name": "Acme Corp", "is_active": True},
    )
    if not company.is_active:
        company.is_active = True
        company.save()

    # 2. Platform Admin (Company-less)
    admin_user, _ = User.objects.get_or_create(
        email=ADMIN_EMAIL,
        defaults={"is_platform_admin": True, "company": None},
    )
    admin_user.is_platform_admin = True
    admin_user.company = None
    admin_user.set_password(PASSWORD)
    admin_user.save()

    # 3. CEO User: siam@gmail.com
    ceo_user, _ = User.objects.get_or_create(
        email=CEO_EMAIL,
        defaults={"company": company, "is_active": True},
    )
    ceo_user.company = company
    ceo_user.is_active = True
    ceo_user.set_password(PASSWORD)
    ceo_user.save()

    desig, _ = Designation.objects.get_or_create(company=company, title="CEO")
    ceo_employee, _ = Employee.objects.get_or_create(
        user=ceo_user,
        defaults={"company": company, "designation": desig, "employee_code": "SIAM-CEO-123"},
    )

    perm, _ = Permission.objects.get_or_create(
        codename="approve_support_access",
        defaults={"name": "Approve Support Access", "module": "settings"},
    )
    ceo_role, _ = Role.objects.get_or_create(
        company=company,
        name="CEO Support Access Role",
        defaults={"description": "Role with approve_support_access permission"},
    )
    ceo_role.permissions.add(perm)

    EmployeeRole.objects.get_or_create(
        employee=ceo_employee,
        role=ceo_role,
        defaults={"company": company},
    )

    # 4. Clean previous open requests for this company & admin
    SupportAccessRequest.objects.filter(company=company, requested_by=admin_user).delete()

    # 5. Platform Admin sends Support Access Request
    req = create_request(admin_user, company, REQUEST_REASON)

    return company, admin_user, ceo_employee, req


class TC57SupportAccessRequestSeleniumTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company, cls.admin_user, cls.ceo_emp, cls.req = prepare_test_data()

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

    def test_tc57_support_access_request_flow(self):
        driver = self.driver
        wait = self.wait

        print("\n=======================================================")
        print("  ST-123 / TC-57: Support Access Request & CEO Listing")
        print("=======================================================")

        # Step 1: Verify the request is created in 'pending' status
        print(f"\n[1/4] Platform Admin ({ADMIN_EMAIL}) sent request for {self.company.name}...")
        self.assertEqual(self.req.status, "pending")
        print(f"      Request ID: {self.req.id}")
        print(f"      Reason: '{self.req.reason}'")
        print("✓ Verified: Request status is 'pending'.")

        # Step 2: Log in as the CEO
        print(f"\n[2/4] Logging in as CEO ({CEO_EMAIL})...")
        driver.get(f"{FRONTEND_URL}/login")
        time.sleep(2)

        email_input = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
        )
        password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")

        email_input.clear()
        email_input.send_keys(CEO_EMAIL)
        time.sleep(1)

        password_input.clear()
        password_input.send_keys(PASSWORD)
        time.sleep(1.5)

        driver.find_element(By.XPATH, "//button[normalize-space()='Login']").click()
        wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)
        print("✓ CEO logged in successfully.")

        # Step 3: Open Support Access Page (/settings/support-access)
        print("\n[3/4] Navigating to /settings/support-access...")
        driver.get(f"{FRONTEND_URL}/settings/support-access")
        time.sleep(2)

        wait.until(EC.presence_of_element_located((By.XPATH, "//h1[normalize-space()='Support access']")))
        print("✓ Support access page loaded.")

        # Step 4: Verify request appears in the list with Pending status and reason
        print("\n[4/4] Verifying the pending request in the CEO list table...")
        time.sleep(2)

        table = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='support-requests-table']"))
        )
        rows = table.find_elements(By.CSS_SELECTOR, "[data-testid='request-row']")
        self.assertGreaterEqual(len(rows), 1, "At least one support access request should appear in table.")

        page_source = driver.page_source
        self.assertIn(ADMIN_EMAIL, page_source, f"Expected {ADMIN_EMAIL} in requests table.")
        self.assertIn(self.req.reason, page_source, f"Expected reason '{self.req.reason}' in table.")
        self.assertIn("Pending", page_source, "Expected 'Pending' status pill in table.")
        print(f"✓ Found request from '{ADMIN_EMAIL}' with reason '{self.req.reason}' and status 'Pending'.")

        # Verify action buttons for CEO
        approve_btn = driver.find_element(By.CSS_SELECTOR, "[data-testid='approve-btn']")
        deny_btn = driver.find_element(By.CSS_SELECTOR, "[data-testid='deny-btn']")
        self.assertTrue(approve_btn.is_displayed(), "Approve button should be available for pending request.")
        self.assertTrue(deny_btn.is_displayed(), "Deny button should be available for pending request.")
        print("✓ Action buttons (Approve / Deny) are active and displayed.")

        print("\n=======================================================")
        print("🎉 ST-123 / TC-57 Selenium Test: 100% PASSED!")
        print("=======================================================\n")


if __name__ == "__main__":
    unittest.main()
