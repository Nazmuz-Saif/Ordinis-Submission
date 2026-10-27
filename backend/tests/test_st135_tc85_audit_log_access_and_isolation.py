"""
ST-135 Selenium Test — TC-85: Audit Log Access Control & Cross-Company Data Isolation
File: test_st135_tc85_audit_log_access_and_isolation.py

Description:
  [Selenium] Open the Audit Log as an Employee without the Permission,
  and as another company's CEO
  — expect no access and none of this company's rows.

Assignee:
    Montasim Kabir Mahin

Credentials:
    Restricted Employee: employee_no_perm@acme.com (Password: 1234, Acme Corp)
    Company B CEO: ceo@beta.com (Password: 1234, Beta Corp)
    Company A CEO: siam@gmail.com (Password: 1234, Acme Corp)

Run:
    cd backend
    python tests/test_st135_tc85_audit_log_access_and_isolation.py
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

from audit_log.services import safe_record
from organization.models import Department, Designation, Employee
from rbac.models import EmployeeRole, Permission, Role
from tenants.models import Company

User = get_user_model()

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from selenium_helpers import FRONTEND_URL, login, clear_session  # noqa: E402

PASSWORD = "1234"

# Company A (Acme Corp)
COMPANY_A_SUBDOMAIN = "acme"
COMPANY_A_NAME = "Acme Corp"
COMPANY_A_CEO = "siam@gmail.com"
COMPANY_A_EMPLOYEE = "employee_no_perm@acme.com"

# Company B (Beta Corp)
COMPANY_B_SUBDOMAIN = "beta-corp"
COMPANY_B_NAME = "Beta Corp"
COMPANY_B_CEO = "ceo@beta.com"


def prepare_test_data():
    """Ensure Company A & Company B exist with isolated audit logs and a restricted employee."""
    # 1. Company A Setup
    comp_a, _ = Company.objects.get_or_create(
        subdomain=COMPANY_A_SUBDOMAIN,
        defaults={"name": COMPANY_A_NAME, "is_active": True},
    )
    if not comp_a.is_active:
        comp_a.is_active = True
        comp_a.save()

    # Company A CEO
    ceo_a, _ = User.objects.get_or_create(
        email=COMPANY_A_CEO,
        defaults={"company": comp_a, "is_active": True},
    )
    ceo_a.company = comp_a
    ceo_a.is_active = True
    ceo_a.set_password(PASSWORD)
    ceo_a.save()

    emp_a_ceo, _ = Employee.objects.get_or_create(
        user=ceo_a,
        defaults={"company": comp_a, "employee_code": "EMP-A-CEO"},
    )
    role_ceo_a, _ = Role.objects.get_or_create(
        company=comp_a, name="CEO", defaults={"is_system_default": True}
    )
    role_ceo_a.permissions.set(Permission.objects.all())
    EmployeeRole.objects.get_or_create(employee=emp_a_ceo, role=role_ceo_a, defaults={"company": comp_a})

    # Company A Restricted Employee (NO view_audit_log permission)
    emp_user, _ = User.objects.get_or_create(
        email=COMPANY_A_EMPLOYEE,
        defaults={"company": comp_a, "is_active": True},
    )
    emp_user.company = comp_a
    emp_user.is_active = True
    emp_user.set_password(PASSWORD)
    emp_user.save()

    emp_record, _ = Employee.objects.get_or_create(
        user=emp_user,
        defaults={"company": comp_a, "employee_code": "EMP-A-NO-PERM"},
    )
    # Role with only basic attendance/task permissions, strictly NO view_audit_log
    basic_role, _ = Role.objects.get_or_create(
        company=comp_a, name="Regular Employee Role",
        defaults={"description": "Standard staff without audit access"}
    )
    basic_perms = Permission.objects.filter(codename__in=["check_in_attendance", "view_own_tasks"])
    basic_role.permissions.set(basic_perms)
    EmployeeRole.objects.filter(employee=emp_record).delete()
    EmployeeRole.objects.create(employee=emp_record, role=basic_role, company=comp_a)

    # Company A Confidential Audit Log
    safe_record(
        company=comp_a, actor=ceo_a, actor_email=ceo_a.email,
        action="create", module="organization", model_name="Department",
        object_repr="Acme Confidential Strategic Unit",
    )

    # 2. Company B Setup
    comp_b, _ = Company.objects.get_or_create(
        subdomain=COMPANY_B_SUBDOMAIN,
        defaults={"name": COMPANY_B_NAME, "is_active": True},
    )
    if not comp_b.is_active:
        comp_b.is_active = True
        comp_b.save()

    ceo_b, _ = User.objects.get_or_create(
        email=COMPANY_B_CEO,
        defaults={"company": comp_b, "is_active": True},
    )
    ceo_b.company = comp_b
    ceo_b.is_active = True
    ceo_b.set_password(PASSWORD)
    ceo_b.save()

    emp_b_ceo, _ = Employee.objects.get_or_create(
        user=ceo_b,
        defaults={"company": comp_b, "employee_code": "EMP-B-CEO"},
    )
    role_ceo_b, _ = Role.objects.get_or_create(
        company=comp_b, name="CEO", defaults={"is_system_default": True}
    )
    role_ceo_b.permissions.set(Permission.objects.all())
    EmployeeRole.objects.get_or_create(employee=emp_b_ceo, role=role_ceo_b, defaults={"company": comp_b})

    # Company B Audit Log
    safe_record(
        company=comp_b, actor=ceo_b, actor_email=ceo_b.email,
        action="create", module="organization", model_name="Department",
        object_repr="Beta Global Innovation Hub",
    )

    return comp_a, emp_user, comp_b, ceo_b


class TC85AuditLogAccessAndIsolationSeleniumTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.comp_a, cls.emp_user, cls.comp_b, cls.ceo_b = prepare_test_data()

    def setUp(self):
        options = webdriver.ChromeOptions()
        if os.environ.get("HEADLESS") == "1":
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1440,900")
        else:
            options.add_argument("--start-maximized")
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 20)

    def tearDown(self):
        time.sleep(2)
        try:
            self.driver.quit()
        except Exception:
            pass

    def test_tc85_audit_log_access_and_isolation(self):
        """TC-85: Employee without permission gets no access; Company B CEO sees none of Company A's rows."""
        driver = self.driver
        wait = self.wait

        print("\n=======================================================")
        print("  ST-135 / TC-85: Audit Log Access Control & Isolation")
        print(f"  Employee (No Perm): {COMPANY_A_EMPLOYEE}")
        print(f"  Company B CEO:      {COMPANY_B_CEO}")
        print("=======================================================")

        # -----------------------------------------------------------------
        # PART 1: Employee without view_audit_log permission
        # -----------------------------------------------------------------
        print(f"\n[1/6] Part 1: Logging in as Employee without permission ({COMPANY_A_EMPLOYEE})...")
        driver.get(f"{FRONTEND_URL}/login")
        time.sleep(1.5)
        login(driver, wait, COMPANY_A_EMPLOYEE, PASSWORD)
        time.sleep(2)
        print("✓ Logged in as restricted employee.")

        # Check Sidebar menu item is NOT present
        print("\n[2/6] Checking sidebar for 'Audit Logs' link...")
        time.sleep(1)
        audit_links = driver.find_elements(By.CSS_SELECTOR, "[data-testid='sidebar-link-Audit Logs']")
        self.assertEqual(
            len(audit_links), 0,
            "Audit Logs link must NOT be visible in sidebar for an employee without view_audit_log permission."
        )
        print("✓ Confirmed: 'Audit Logs' link is completely hidden from the sidebar.")

        # Try direct access to /audit-logs
        print("\n[3/6] Navigating directly to /audit-logs URL...")
        driver.get(f"{FRONTEND_URL}/audit-logs")
        time.sleep(2)

        # Expect EmptyState with Access Denied message, and NO audit table
        page_source = driver.page_source
        self.assertTrue(
            "You do not have access to this page" in page_source or "view audit log permission" in page_source.lower(),
            "Expected 'You do not have access to this page' EmptyState banner."
        )
        table_elements = driver.find_elements(By.CSS_SELECTOR, "[data-testid='audit-table']")
        self.assertEqual(
            len(table_elements), 0,
            "Audit table must NOT be rendered when user has no permission."
        )
        print("✓ Confirmed: Access is blocked with 'You do not have access to this page'.")
        time.sleep(1.5)

        # -----------------------------------------------------------------
        # PART 2: Company B CEO — Cross-Company Data Isolation
        # -----------------------------------------------------------------
        print(f"\n[4/6] Part 2: Clearing session and logging in as Company B CEO ({COMPANY_B_CEO})...")
        clear_session(driver)
        time.sleep(1.5)

        driver.get(f"{FRONTEND_URL}/login")
        time.sleep(1.5)
        login(driver, wait, COMPANY_B_CEO, PASSWORD)
        time.sleep(2)
        print("✓ Logged in as Company B CEO.")

        # Navigate to /audit-logs
        print("\n[5/6] Navigating to /audit-logs as Company B CEO...")
        driver.get(f"{FRONTEND_URL}/audit-logs")
        time.sleep(2)

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='audit-table']")))
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "tr[data-testid='audit-row']")))
        print("✓ Company B Audit Logs page loaded successfully.")
        time.sleep(2)

        # Verify None of Company A's rows or information appear
        print("\n[6/6] Verifying strict cross-company isolation (none of Company A's rows)...")
        b_page_source = driver.page_source

        # 1. Company A's CEO email must NOT appear anywhere
        self.assertNotIn(
            COMPANY_A_CEO, b_page_source,
            f"Company A's email ({COMPANY_A_CEO}) must NOT leak into Company B's audit log!"
        )

        # 2. Company A's confidential record must NOT appear anywhere
        self.assertNotIn(
            "Acme Confidential Strategic Unit", b_page_source,
            "Company A's audit record must NOT leak into Company B's audit log!"
        )

        # 3. Company B's own audit record MUST appear
        self.assertIn(
            COMPANY_B_CEO, b_page_source,
            f"Company B's CEO ({COMPANY_B_CEO}) should be visible in Company B's audit log."
        )
        self.assertIn(
            "Beta Global Innovation Hub", b_page_source,
            "Company B's own audit record should be visible."
        )

        print(f"✓ Confirmed: Company B audit log contains Company B records ('Beta Global Innovation Hub').")
        print(f"✓ Confirmed: ZERO records or email addresses from Company A ('{COMPANY_A_NAME}') leaked.")

        print("\n=======================================================")
        print("🎉 ST-135 / TC-85 Selenium Test: 100% PASSED!")
        print("=======================================================")


if __name__ == "__main__":
    unittest.main()
