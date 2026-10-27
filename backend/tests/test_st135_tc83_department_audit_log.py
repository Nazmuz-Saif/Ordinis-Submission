"""
ST-135 Selenium Test — TC-83: Create, Edit & Delete Department Audit Log
File: test_st135_tc83_department_audit_log.py

Description:
  [Selenium] Create, edit and delete a Department as the CEO
  — expect three new rows on the Audit Log page with the right actor and action.

Assignee:
    Montasim Kabir Mahin

Credentials:
    CEO User: siam@gmail.com (Password: 1234, Company: Acme Corp)

Run:
    cd backend
    python tests/test_st135_tc83_department_audit_log.py
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
from selenium.webdriver.support.ui import WebDriverWait

from organization.models import Department, Designation, Employee
from rbac.models import EmployeeRole, Permission, Role
from tenants.models import Company

User = get_user_model()

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from selenium_helpers import FRONTEND_URL, login, clear_session  # noqa: E402

COMPANY_SUBDOMAIN = "acme"
CEO_EMAIL = "siam@gmail.com"
PASSWORD = "1234"


def prepare_test_data():
    """Ensure Acme Corp and CEO exist with proper permissions (manage_departments & view_audit_log)."""
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

    Department.objects.filter(
        company=company,
        name__in=["Human Resources", "Human Resources & Talent"]
    ).delete()

    return company, ceo_user, ceo_emp


class TC83DepartmentAuditLogSeleniumTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company, cls.ceo_user, cls.ceo_emp = prepare_test_data()

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

    def test_tc83_create_edit_delete_department_audit_log(self):
        """TC-83: Create, edit and delete a Department as CEO — expect 3 audit log rows."""
        driver = self.driver
        wait = self.wait

        dept_name = "Human Resources"
        updated_dept_name = "Human Resources & Talent"

        print("\n=======================================================")
        print("  ST-135 / TC-83: Department Lifecycle & Audit Log Rows")
        print(f"  CEO User: {CEO_EMAIL}")
        print(f"  Target Department: {dept_name}")
        print("=======================================================")

        # Step 1: Login as CEO
        print(f"\n[1/6] Logging in as CEO ({CEO_EMAIL})...")
        driver.get(f"{FRONTEND_URL}/login")
        time.sleep(1.5)
        login(driver, wait, CEO_EMAIL, PASSWORD)
        time.sleep(2)
        print("✓ Logged in successfully.")

        # Step 2: Navigate to Organization / Departments page
        print("\n[2/6] Navigating to Organization / Departments page...")
        driver.get(f"{FRONTEND_URL}/organization")
        wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Departments']")))
        time.sleep(2.5)
        print("✓ Departments page loaded.")

        def set_react_input(element, val):
            driver.execute_script("""
                const el = arguments[0];
                const val = arguments[1];
                const lastVal = el.value;
                el.value = val;
                const tracker = el._valueTracker;
                if (tracker) {
                    tracker.setValue(lastVal);
                }
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            """, element, val)

        # Step 3: Create Department
        print(f"\n[3/6] Creating department '{dept_name}'...")
        dept_input = wait.until(
            EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='New department name']"))
        )
        set_react_input(dept_input, dept_name)
        time.sleep(1)
        add_btn = driver.find_element(By.XPATH, "//form//button[@type='submit']")
        driver.execute_script("arguments[0].click();", add_btn)
        time.sleep(2)

        wait.until(
            lambda d: any(dept_name in el.text for el in d.find_elements(By.CSS_SELECTOR, "div.divide-y span"))
        )
        print(f"✓ Department '{dept_name}' created and visible in list.")
        time.sleep(2)

        # Step 4: Edit Department
        print(f"\n[4/6] Editing department '{dept_name}' -> '{updated_dept_name}'...")
        dept_row = wait.until(
            lambda d: [r for r in d.find_elements(By.CSS_SELECTOR, "div.divide-y > div") if dept_name in r.text][0]
        )
        edit_btn = dept_row.find_element(By.CSS_SELECTOR, "button[title='Edit']")
        driver.execute_script("arguments[0].click();", edit_btn)
        time.sleep(1.5)

        edit_input = wait.until(
            EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'divide-y')]//input[@type='text']"))
        )
        set_react_input(edit_input, updated_dept_name)
        time.sleep(1)

        save_btn = driver.find_element(
            By.XPATH, "//div[contains(@class, 'divide-y')]//button[contains(@class, 'text-[#16A34A]')]"
        )
        driver.execute_script("arguments[0].click();", save_btn)
        time.sleep(2)

        wait.until(
            lambda d: any(updated_dept_name in el.text for el in d.find_elements(By.CSS_SELECTOR, "div.divide-y span"))
        )
        print(f"✓ Department renamed to '{updated_dept_name}'.")
        time.sleep(2)

        # Step 5: Delete Department
        print(f"\n[5/6] Deleting department '{updated_dept_name}'...")
        driver.execute_script("window.confirm = () => true;")
        updated_row = wait.until(
            lambda d: [r for r in d.find_elements(By.CSS_SELECTOR, "div.divide-y > div") if updated_dept_name in r.text][0]
        )
        del_btn = updated_row.find_element(By.CSS_SELECTOR, "button[title='Delete']")
        driver.execute_script("arguments[0].click();", del_btn)
        time.sleep(2)

        wait.until(
            lambda d: not any(updated_dept_name in el.text for el in d.find_elements(By.CSS_SELECTOR, "div.divide-y span"))
        )
        print(f"✓ Department '{updated_dept_name}' deleted successfully.")
        time.sleep(2)

        # Step 6: Navigate to Audit Logs page & verify 3 rows
        print("\n[6/6] Opening Audit Logs page and inspecting rows...")
        driver.get(f"{FRONTEND_URL}/audit-logs")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='audit-table']")))
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "tr[data-testid='audit-row']")))
        time.sleep(2)

        rows = driver.find_elements(By.CSS_SELECTOR, "tr[data-testid='audit-row']")
        print(f"      Found {len(rows)} audit log rows on page.")

        # Match rows belonging to this department lifecycle
        target_rows = []
        for r in rows:
            text = r.text
            if (dept_name in text or updated_dept_name in text) and "Department" in text:
                user_el = r.find_element(By.CSS_SELECTOR, "[data-testid='audit-user']")
                action_el = r.find_element(By.CSS_SELECTOR, "[data-testid='audit-action']")
                module_el = r.find_element(By.CSS_SELECTOR, "[data-testid='audit-module']")
                target_rows.append({
                    "user": user_el.text,
                    "action": action_el.text,
                    "module": module_el.text,
                })
                if len(target_rows) == 3:
                    break

        print(f"      Matched {len(target_rows)} audit rows belonging to department '{dept_name}':")
        for i, tr in enumerate(target_rows, 1):
            print(f"        Row {i}: Action='{tr['action']}' | User='{tr['user']}' | Module='{tr['module']}'")

        self.assertEqual(
            len(target_rows), 3,
            f"Expected exactly 3 audit rows for '{dept_name}', found {len(target_rows)}"
        )

        actions = [tr["action"] for tr in target_rows]
        self.assertTrue(
            any("Deleted" in a for a in actions),
            f"Expected a 'Deleted' audit row in {actions}"
        )
        self.assertTrue(
            any("Updated" in a for a in actions),
            f"Expected an 'Updated' audit row in {actions}"
        )
        self.assertTrue(
            any("Created" in a for a in actions),
            f"Expected a 'Created' audit row in {actions}"
        )

        for tr in target_rows:
            self.assertTrue(
                CEO_EMAIL in tr["user"] or "siam" in tr["user"].lower() or "reza" in tr["user"].lower(),
                f"Actor should match CEO ({CEO_EMAIL}), got '{tr['user']}'"
            )
            self.assertEqual(
                tr["module"].strip().lower(), "organization",
                f"Module should be 'Organization', got '{tr['module']}'"
            )

        print("\n=======================================================")
        print("🎉 ST-135 / TC-83 Selenium Test: 100% PASSED!")
        print("=======================================================\n")


if __name__ == "__main__":
    unittest.main()
