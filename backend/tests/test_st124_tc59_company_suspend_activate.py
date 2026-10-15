"""
ST-124 Selenium Test — TC-59: Suspend & Activate Company via Platform Admin Panel
File: test_st124_tc59_company_suspend_activate.py

Description:
  [Selenium] As a Platform Admin open the panel and suspend a company — expect its users
  cannot log in; activate it — expect they can.

Credentials:
    Platform Admin: platform_admin@ordinis.com (Password: 1234)
    Company User: suspend_user@ordinis.com (Password: 1234, Company: Suspend Test Corp)

Run:
    cd backend
    python tests/test_st124_tc59_company_suspend_activate.py
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
from tenants.models import Company

User = get_user_model()

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from selenium_helpers import FRONTEND_URL  # noqa: E402  (one shared place: tests/selenium_helpers.py)
ADMIN_EMAIL = "platform_admin@ordinis.com"
COMPANY_SUBDOMAIN = "suspend-corp"
COMPANY_NAME = "Suspend Test Corp"
USER_EMAIL = "suspend_user@ordinis.com"
PASSWORD = "1234"


def prepare_test_data():
    """Ensure Platform Admin and a dedicated test company exist and are active."""
    # 1. Platform Admin
    admin_user, _ = User.objects.get_or_create(
        email=ADMIN_EMAIL,
        defaults={"is_platform_admin": True, "company": None},
    )
    admin_user.set_password(PASSWORD)
    admin_user.is_platform_admin = True
    admin_user.company = None
    admin_user.save()

    # 2. Test Company (Suspend Test Corp)
    company, _ = Company.objects.get_or_create(
        subdomain=COMPANY_SUBDOMAIN,
        defaults={"name": COMPANY_NAME, "is_active": True},
    )
    company.is_active = True
    company.save()

    # 3. Test Company User
    user, _ = User.objects.get_or_create(
        email=USER_EMAIL,
        defaults={"company": company, "is_active": True},
    )
    user.set_password(PASSWORD)
    user.company = company
    user.is_active = True
    user.save()

    dept, _ = Department.objects.get_or_create(company=company, name="Operations")
    desig, _ = Designation.objects.get_or_create(company=company, title="Ops Lead")
    Employee.objects.get_or_create(
        user=user,
        defaults={
            "company": company,
            "employee_code": "EMP-SUS-001",
            "department": dept,
            "designation": desig,
        },
    )

    return company, admin_user, user


class TC59CompanySuspendActivateSeleniumTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company, cls.admin_user, cls.user = prepare_test_data()

    @classmethod
    def tearDownClass(cls):
        # Guarantee company is restored to active status
        try:
            cls.company.refresh_from_db()
            cls.company.is_active = True
            cls.company.save()
        except Exception:
            pass
        super().tearDownClass()

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

    def clear_session(self):
        driver = self.driver
        driver.execute_script("localStorage.clear(); sessionStorage.clear();")
        driver.delete_all_cookies()
        time.sleep(1)

    def find_company_row(self):
        """Finds table row for Suspend Test Corp."""
        rows = self.driver.find_elements(By.CSS_SELECTOR, "tr[data-testid='company-row']")
        for row in rows:
            if COMPANY_NAME in row.text or COMPANY_SUBDOMAIN in row.text:
                return row
        return None

    def test_tc59_suspend_and_activate_company_flow(self):
        driver = self.driver
        wait = self.wait

        print("\n=======================================================")
        print("  ST-124 / TC-59: Platform Admin Suspend & Activate Company")
        print("=======================================================")

        # Step 1: Platform Admin logs in
        print(f"\n[1/6] Logging in as Platform Admin ({ADMIN_EMAIL})...")
        driver.get(f"{FRONTEND_URL}/login")
        time.sleep(2)

        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']"))).send_keys(ADMIN_EMAIL)
        driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(PASSWORD)
        driver.find_element(By.XPATH, "//button[normalize-space()='Login']").click()
        wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)
        print("✓ Platform Admin logged in successfully.")

        # Step 2: Open Companies panel
        print("\n[2/6] Navigating to Platform Admin Companies page (/admin/companies)...")
        driver.get(f"{FRONTEND_URL}/admin/companies")
        time.sleep(2)

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='companies-table']")))
        company_row = self.find_company_row()
        self.assertIsNotNone(company_row, f"Row for '{COMPANY_NAME}' should be visible in companies table.")
        print(f"✓ Found '{COMPANY_NAME}' row in table.")

        # Step 3: Suspend the company
        print(f"\n[3/6] Suspending '{COMPANY_NAME}'...")
        suspend_btn = company_row.find_element(By.CSS_SELECTOR, "[data-testid='suspend-btn']")
        time.sleep(1.5)
        suspend_btn.click()
        time.sleep(1.5)

        # Confirm in modal
        confirm_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='confirm-btn']"))
        )
        confirm_btn.click()
        time.sleep(2.5)

        # Verify notice and table status
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='admin-message']")))
        message_text = driver.find_element(By.CSS_SELECTOR, "[data-testid='admin-message']").text
        print(f"      Message banner: '{message_text}'")
        self.assertIn("suspended", message_text.lower(), "Expected suspension success message.")

        # Verify button in row is now 'Activate'
        company_row = self.find_company_row()
        self.assertTrue(
            len(company_row.find_elements(By.CSS_SELECTOR, "[data-testid='activate-btn']")) > 0,
            "Row should now offer Activate button."
        )
        print("✓ Verified: Company is suspended. Status updated in table.")

        # Step 4: Verify company users CANNOT log in
        print(f"\n[4/6] Verifying user ({USER_EMAIL}) of suspended company CANNOT log in...")
        self.clear_session()
        driver.get(f"{FRONTEND_URL}/login")
        time.sleep(2)

        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']"))).send_keys(USER_EMAIL)
        driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(PASSWORD)
        time.sleep(1)
        driver.find_element(By.XPATH, "//button[normalize-space()='Login']").click()
        time.sleep(2.5)

        # Expect user remains on login page with error
        self.assertIn("/login", driver.current_url, "Suspended user must NOT be permitted past the login page.")
        error_elements = driver.find_elements(By.XPATH, "//form//p[contains(@class, 'DC2626')]")
        self.assertTrue(len(error_elements) > 0, "Error message must be shown when suspended user attempts login.")
        print(f"      Login error displayed: '{error_elements[0].text}'")
        print(f"      Current URL: {driver.current_url}")
        print("✓ Verified: User of suspended company cannot log in.")

        # Step 5: Log back in as Platform Admin and Activate the company
        print(f"\n[5/6] Logging in as Platform Admin ({ADMIN_EMAIL}) to Activate '{COMPANY_NAME}'...")
        self.clear_session()
        driver.get(f"{FRONTEND_URL}/login")
        time.sleep(2)

        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']"))).send_keys(ADMIN_EMAIL)
        driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(PASSWORD)
        driver.find_element(By.XPATH, "//button[normalize-space()='Login']").click()
        wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)

        driver.get(f"{FRONTEND_URL}/admin/companies")
        time.sleep(2)

        company_row = self.find_company_row()
        activate_btn = company_row.find_element(By.CSS_SELECTOR, "[data-testid='activate-btn']")
        time.sleep(1.5)
        activate_btn.click()
        time.sleep(1.5)

        confirm_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='confirm-btn']"))
        )
        confirm_btn.click()
        time.sleep(2.5)

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='admin-message']")))
        message_text = driver.find_element(By.CSS_SELECTOR, "[data-testid='admin-message']").text
        print(f"      Message banner: '{message_text}'")
        self.assertIn("active", message_text.lower(), "Expected activation success message.")
        print("✓ Verified: Company has been activated again.")

        # Step 6: Verify company user CAN now log in
        print(f"\n[6/6] Verifying user ({USER_EMAIL}) CAN now log in successfully...")
        self.clear_session()
        driver.get(f"{FRONTEND_URL}/login")
        time.sleep(2)

        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']"))).send_keys(USER_EMAIL)
        driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(PASSWORD)
        time.sleep(1)
        driver.find_element(By.XPATH, "//button[normalize-space()='Login']").click()

        wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2.5)

        self.assertIn("/dashboard", driver.current_url, "User should be redirected to dashboard on successful login.")
        print(f"      Logged in successfully! Current URL: {driver.current_url}")
        print("✓ Verified: User can log in normally after company reactivation.")

        print("\n=======================================================")
        print("🎉 ST-124 / TC-59 Selenium Test: 100% PASSED!")
        print("=======================================================\n")


if __name__ == "__main__":
    unittest.main()
