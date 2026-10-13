"""
ST-123 Selenium Test — TC-58: Support Access Approval, Expiry, Access Log & Enforcement
File: test_st123_tc58_support_access_approval.py

Description:
  [Selenium] As the CEO approve the request — expect an expiry time and a log entry;
  without an approved request — expect access blocked

Credentials:
    Platform Admin: platform_admin@ordinis.com (Password: 1234)
    CEO: siam@gmail.com (Password: 1234)

Run:
    cd backend
    python tests/test_st123_tc58_support_access_approval.py
"""
import json
import os
import sys
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

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
from platform_admin.models import SupportAccessRequest
from platform_admin.services import create_request
from rbac.models import EmployeeRole, Permission, Role
from tenants.models import Company

User = get_user_model()

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://127.0.0.1:8000/api/v1")
COMPANY_SUBDOMAIN = "acme"

ADMIN_EMAIL = "platform_admin@ordinis.com"
CEO_EMAIL = "siam@gmail.com"
PASSWORD = "1234"


def prepare_test_data():
    # 1. Company
    company, _ = Company.objects.get_or_create(
        subdomain=COMPANY_SUBDOMAIN,
        defaults={"name": "Acme Corp", "is_active": True},
    )
    if not company.is_active:
        company.is_active = True
        company.save()

    dept, _ = Department.objects.get_or_create(company=company, name="Core Engineering")
    desig, _ = Designation.objects.get_or_create(company=company, title="CEO")

    # 2. Platform Admin
    admin_user, _ = User.objects.get_or_create(
        email=ADMIN_EMAIL,
        defaults={"is_platform_admin": True, "company": None},
    )
    admin_user.is_platform_admin = True
    admin_user.company = None
    admin_user.set_password(PASSWORD)
    admin_user.save()

    # 3. CEO User
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

    # Clean old requests and create fresh pending request
    SupportAccessRequest.objects.filter(company=company, requested_by=admin_user).delete()
    req = create_request(admin_user, company, "Support investigation for database crash")

    # Another unapproved company for access enforcement check
    other_company, _ = Company.objects.get_or_create(
        subdomain="unapproved-corp",
        defaults={"name": "Unapproved Corp", "is_active": True},
    )

    return company, admin_user, ceo_employee, req, other_company


def get_admin_token():
    payload = json.dumps({"email": ADMIN_EMAIL, "password": PASSWORD}).encode("utf-8")
    req = Request(f"{BACKEND_API_URL}/auth/login/", data=payload, headers={"Content-Type": "application/json"})
    with urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))["access"]


def access_support_data(token, company_id, resource="departments"):
    url = f"{BACKEND_API_URL}/platform-admin/support/{company_id}/{resource}/"
    req = Request(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        return e.code, e.read().decode("utf-8")


class TC58SupportAccessApprovalSeleniumTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company, cls.admin_user, cls.ceo_emp, cls.req, cls.other_co = prepare_test_data()

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

    def test_tc58_approval_expiry_log_and_enforcement(self):
        driver = self.driver
        wait = self.wait

        print("\n=======================================================")
        print("  ST-123 / TC-58: Support Access Approval & Enforcement")
        print("=======================================================")

        # Step 1: Log in as CEO
        print(f"\n[1/6] Logging in as CEO ({CEO_EMAIL})...")
        driver.get(f"{FRONTEND_URL}/login")
        time.sleep(2)

        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']"))).send_keys(CEO_EMAIL)
        driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(PASSWORD)
        driver.find_element(By.XPATH, "//button[normalize-space()='Login']").click()
        wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)
        print("✓ CEO logged in successfully.")

        # Step 2: Navigate to Support Access Page
        print("\n[2/6] Navigating to /settings/support-access...")
        driver.get(f"{FRONTEND_URL}/settings/support-access")
        time.sleep(2)

        # Step 3: Approve the request
        print("\n[3/6] Approving the pending support access request...")
        approve_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='approve-btn']"))
        )
        time.sleep(1.5)
        approve_btn.click()
        time.sleep(1.5)

        # Confirm in modal
        confirm_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='confirm-btn']"))
        )
        confirm_btn.click()
        time.sleep(2.5)
        print("✓ Approved button clicked and confirmed.")

        # Step 4: Expect an expiry time
        print("\n[4/6] Verifying expiry time is shown...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='request-expiry']")))
        expiry_text = driver.find_element(By.CSS_SELECTOR, "[data-testid='request-expiry']").text
        print(f"      Expiry text displayed: '{expiry_text}'")
        self.assertIn("until", expiry_text, "Approved request must display expiry time.")
        print("✓ Verified: Expiry time is displayed for approved access grant.")

        # Step 5: Platform Admin accesses data and creates log entry
        print("\n[5/6] Platform Admin uses approved grant; verifying access log entry...")
        admin_token = get_admin_token()
        code, body = access_support_data(admin_token, self.company.id, "departments")
        self.assertEqual(code, 200, "Support data read should succeed with approved grant.")
        print("✓ Support access allowed (200 OK) under approved grant.")

        # Switch to Access Log tab in UI
        log_tab = driver.find_element(By.CSS_SELECTOR, "[data-testid='tab-log']")
        time.sleep(1.5)
        log_tab.click()
        time.sleep(2.5)

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='access-log-table']")))
        log_rows = driver.find_elements(By.CSS_SELECTOR, "[data-testid='log-row']")
        self.assertGreaterEqual(len(log_rows), 1, "Access log must contain entries of support reads.")
        self.assertIn(ADMIN_EMAIL, driver.page_source, "Access log should record actor email.")
        print(f"✓ Found {len(log_rows)} access log row(s) recording Platform Admin activity.")

        # Step 6: Without an approved request — expect access blocked (403)
        print("\n[6/6] Verifying access is BLOCKED (403) without an approved request...")
        blocked_code, blocked_body = access_support_data(admin_token, self.other_co.id, "departments")
        print(f"      Attempting access to unapproved company returned HTTP: {blocked_code}")
        self.assertEqual(blocked_code, 403, f"Expected 403 Forbidden without grant, got {blocked_code}")
        print("✓ Verified: Platform Admin access without approved grant is strictly BLOCKED (403 Forbidden).")

        print("\n=======================================================")
        print("🎉 ST-123 / TC-58 Selenium Test: 100% PASSED!")
        print("=======================================================\n")


if __name__ == "__main__":
    unittest.main()
