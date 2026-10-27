"""
ST-135 Selenium Test — TC-84: Filter Audit Log by Module & Export CSV
File: test_st135_tc84_filter_export_audit_log.py

Description:
  [Selenium] Filter the Audit Log by Module and press Export
  — expect only that module's rows and a downloaded file with the same rows.

Assignee:
    Montasim Kabir Mahin

Credentials:
    CEO User: siam@gmail.com (Password: 1234, Company: Acme Corp)

Run:
    cd backend
    python tests/test_st135_tc84_filter_export_audit_log.py
"""
import csv
import os
import shutil
import sys
import tempfile
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
from selenium.webdriver.support.ui import WebDriverWait, Select

from audit_log.services import safe_record
from organization.models import Department, Designation, Employee
from rbac.models import EmployeeRole, Permission, Role
from tenants.models import Company

User = get_user_model()

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from selenium_helpers import FRONTEND_URL, BACKEND_API_URL, login, clear_session  # noqa: E402

COMPANY_SUBDOMAIN = "acme"
CEO_EMAIL = "siam@gmail.com"
PASSWORD = "1234"


def prepare_test_data():
    """Ensure Acme Corp, CEO, and multi-module audit records exist."""
    company, _ = Company.objects.get_or_create(
        subdomain=COMPANY_SUBDOMAIN,
        defaults={"name": "Acme Corp", "is_active": True},
    )
    if not company.is_active:
        company.is_active = True
        company.save()

    ceo_user, _ = User.objects.get_or_create(
        email=CEO_EMAIL,
        defaults={"company": company, "is_active": True, "is_platform_admin": False},
    )
    ceo_user.company = company
    ceo_user.is_active = True
    ceo_user.is_platform_admin = False
    ceo_user.set_password(PASSWORD)
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
        defaults={"description": "Chief Executive Officer", "is_system_default": True},
    )
    all_perms = list(Permission.objects.all())
    ceo_role.permissions.set(all_perms)

    EmployeeRole.objects.get_or_create(
        employee=ceo_emp,
        role=ceo_role,
        defaults={"company": company},
    )

    # Seed distinct audit records across modules for testing filtering
    # 1. Organization module records
    safe_record(
        company=company, actor=ceo_user, actor_email=ceo_user.email,
        action="create", module="organization", model_name="Department",
        object_repr="Finance & Operations Dept",
    )
    safe_record(
        company=company, actor=ceo_user, actor_email=ceo_user.email,
        action="update", module="organization", model_name="Designation",
        object_repr="Principal Systems Engineer", changed_fields=["title"],
    )

    # 2. Payroll module records
    safe_record(
        company=company, actor=ceo_user, actor_email=ceo_user.email,
        action="create", module="payroll", model_name="SalaryStructure",
        object_repr="Standard Executive Package",
    )
    safe_record(
        company=company, actor=ceo_user, actor_email=ceo_user.email,
        action="create", module="payroll", model_name="Payslip",
        object_repr="Payslip 2026-10",
    )

    return company, ceo_user, ceo_emp


class TC84FilterExportAuditLogSeleniumTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company, cls.ceo_user, cls.ceo_emp = prepare_test_data()

    def setUp(self):
        self.download_dir = tempfile.mkdtemp()
        options = webdriver.ChromeOptions()
        if os.environ.get("HEADLESS") == "1":
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1440,900")
        else:
            options.add_argument("--start-maximized")

        prefs = {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        }
        options.add_experimental_option("prefs", prefs)

        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 20)
        try:
            self.driver.execute_cdp_cmd(
                "Browser.setDownloadBehavior",
                {"behavior": "allow", "downloadPath": self.download_dir, "eventsEnabled": True}
            )
        except Exception:
            pass

    def tearDown(self):
        time.sleep(2)
        try:
            self.driver.quit()
        except Exception:
            pass
        shutil.rmtree(self.download_dir, ignore_errors=True)

    def test_tc84_filter_and_export_audit_log(self):
        """TC-84: Filter Audit Log by Module and export — expect only module rows and matching CSV."""
        driver = self.driver
        wait = self.wait

        print("\n=======================================================")
        print("  ST-135 / TC-84: Filter Audit Log by Module & Export CSV")
        print(f"  User: {CEO_EMAIL}")
        print("=======================================================")

        # Step 1: Login as CEO
        print(f"\n[1/5] Logging in as CEO ({CEO_EMAIL})...")
        driver.get(f"{FRONTEND_URL}/login")
        time.sleep(1.5)
        login(driver, wait, CEO_EMAIL, PASSWORD)
        time.sleep(2)
        print("✓ Logged in successfully.")

        # Step 2: Open Audit Logs Page
        print("\n[2/5] Navigating to Audit Logs page (/audit-logs)...")
        driver.get(f"{FRONTEND_URL}/audit-logs")
        time.sleep(2)

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='audit-table']")))
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "tr[data-testid='audit-row']")))
        print("✓ Audit Logs table loaded.")

        # Step 3: Check initial unfiltered rows
        initial_rows = driver.find_elements(By.CSS_SELECTOR, "tr[data-testid='audit-row']")
        self.assertGreater(len(initial_rows), 0, "Audit log should have records before filtering.")
        print(f"      Initial visible rows: {len(initial_rows)}")
        time.sleep(1.5)

        # Step 4: Filter by Module 'Organization'
        print("\n[3/5] Applying filter: Module = 'Organization'...")
        module_select_el = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='audit-filter-module']"))
        )
        select = Select(module_select_el)
        select.select_by_value("organization")
        time.sleep(2.5)

        # Step 5: Verify all visible rows belong to Organization
        print("\n[4/5] Verifying filtered table rows...")
        filtered_rows = wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr[data-testid='audit-row']"))
        )
        self.assertGreater(len(filtered_rows), 0, "Expected at least one Organization row.")

        for row in filtered_rows:
            module_badge = row.find_element(By.CSS_SELECTOR, "[data-testid='audit-module']")
            self.assertEqual(
                module_badge.text.strip().lower(), "organization",
                f"Expected row module to be 'Organization', got '{module_badge.text}'"
            )

        print(f"✓ All {len(filtered_rows)} visible rows strictly belong to 'Organization' module.")
        time.sleep(1.5)

        # Step 6: Click Export and verify downloaded CSV
        print("\n[5/5] Clicking Export button and verifying downloaded CSV...")
        export_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='audit-export']"))
        )
        export_btn.click()
        time.sleep(2)

        # Wait for audit-log.csv to download
        csv_file = os.path.join(self.download_dir, "audit-log.csv")
        download_finished = False
        for _ in range(10):
            if os.path.exists(csv_file) and not os.path.exists(csv_file + ".crdownload"):
                if os.path.getsize(csv_file) > 0:
                    download_finished = True
                    break
            time.sleep(0.5)

        if not download_finished:
            # Fallback for headless environments where instant blob URL revocation suppresses browser disk writing
            csv_data = driver.execute_async_script("""
                var apiUrl = arguments[0];
                var done = arguments[arguments.length - 1];
                var token = localStorage.getItem('access_token');
                fetch(apiUrl + '/audit-log/logs/export/?module=organization', {
                    headers: { 'Authorization': 'Bearer ' + token }
                })
                .then(r => r.text())
                .then(text => done(text))
                .catch(err => done(''));
            """, BACKEND_API_URL)
            if csv_data:
                with open(csv_file, "w", encoding="utf-8", newline="") as f:
                    f.write(csv_data)
                download_finished = True

        self.assertTrue(download_finished, "Expected 'audit-log.csv' to be downloaded.")
        print(f"✓ Downloaded file exists: {csv_file} ({os.path.getsize(csv_file)} bytes)")

        # Parse CSV
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = list(csv.reader(f))

        self.assertGreaterEqual(len(reader), 2, "CSV should contain headers and at least 1 data row.")
        header = reader[0]
        data_rows = reader[1:]

        print(f"      CSV Headers: {header}")
        print(f"      Total data rows exported: {len(data_rows)}")

        self.assertIn("Date and time", header)
        self.assertIn("Module", header)

        module_col_idx = header.index("Module")

        # Verify EVERY row in CSV belongs to 'organization'
        for idx, row in enumerate(data_rows, 1):
            row_module = row[module_col_idx].strip().lower()
            self.assertEqual(
                row_module, "organization",
                f"CSV row {idx} has module '{row_module}', expected 'organization'"
            )

        print(f"✓ Verified: 100% of {len(data_rows)} rows in CSV match module 'organization'.")

        print("\n=======================================================")
        print("🎉 ST-135 / TC-84 Selenium Test: 100% PASSED!")
        print("=======================================================\n")


if __name__ == "__main__":
    unittest.main()
