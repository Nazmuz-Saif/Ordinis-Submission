"""
ST-121 Selenium Test — TC-53: List Pagination and Page Controls
File: test_st121_tc53_pagination.py

Description:
  [Selenium] Open a list with more than one page — expect page controls and that the next page loads

Credentials:
    Logged in User: siam@gmail.com (Password: 1234)

Run:
    cd backend
    python tests/test_st121_tc53_pagination.py
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
from rbac.models import EmployeeRole, Permission, Role
from tasks.models import Task
from tenants.models import Company

User = get_user_model()

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from selenium_helpers import FRONTEND_URL, BACKEND_API_URL, login  # noqa: E402  (one shared place: tests/selenium_helpers.py)
COMPANY_SUBDOMAIN = "acme"

LOGIN_EMAIL = "siam@gmail.com"
PASSWORD = "1234"
TOTAL_TEST_TASKS = 25  # Page size is 20; 25 tasks creates 2 pages


def prepare_test_data():
    # 1. Company: Acme Corp
    company, _ = Company.objects.get_or_create(
        subdomain=COMPANY_SUBDOMAIN,
        defaults={"name": "Acme Corp", "is_active": True},
    )
    if not company.is_active:
        company.is_active = True
        company.save()

    # 2. User: siam@gmail.com
    user, _ = User.objects.get_or_create(
        email=LOGIN_EMAIL,
        defaults={"company": company, "is_active": True},
    )
    user.company = company
    user.is_active = True
    user.set_password(PASSWORD)
    user.save()

    employee, _ = Employee.objects.get_or_create(
        user=user,
        defaults={"company": company, "employee_code": "SIAM-EMP-001"},
    )

    perm, _ = Permission.objects.get_or_create(
        codename="create_task",
        defaults={"name": "Create Task", "module": "tasks"},
    )
    role, _ = Role.objects.get_or_create(
        company=company,
        name="Task Manager Role",
        defaults={"description": "Role with create_task permission"},
    )
    role.permissions.add(perm)

    EmployeeRole.objects.get_or_create(
        employee=employee,
        role=role,
        defaults={"company": company},
    )

    # 3. Create 25 clean tasks in Acme Corp
    Task.objects.filter(company=company).delete()

    created_tasks = []
    for i in range(1, TOTAL_TEST_TASKS + 1):
        task = Task.objects.create(
            company=company,
            title=f"Task {i:02d}",
            description="",  # Clean title, no unwanted text
            assigned_to=employee,
            assigned_by=employee,
            priority="medium",
            status="not_started",
        )
        created_tasks.append(task)

    return company, employee, created_tasks


class TC53PaginationSeleniumTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company, cls.employee, cls.tasks = prepare_test_data()

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

    def login(self, email, password):
        login(self.driver, self.wait, email, password)

    def test_tc53_pagination_controls_and_next_page(self):
        driver = self.driver
        wait = self.wait

        print("\n=======================================================")
        print("  ST-121 / TC-53: Pagination Controls & Next Page Load")
        print(f"  User: {LOGIN_EMAIL}")
        print("=======================================================")

        # Step 1: Login
        print(f"\n[1/5] Logging in as {LOGIN_EMAIL}...")
        self.login(LOGIN_EMAIL, PASSWORD)
        print("✓ Logged in successfully.")

        # Step 2: Open paginated list (/tasks)
        print("\n[2/5] Opening paginated list at /tasks...")
        driver.get(f"{FRONTEND_URL}/tasks")
        time.sleep(2)

        wait.until(EC.presence_of_element_located((By.XPATH, "//h1[normalize-space()='Tasks']")))
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='task-row']")))
        print("✓ Tasks page loaded.")

        # Step 3: Expect Page Controls on Page 1
        print("\n[3/5] Expecting Page Controls on Page 1...")
        time.sleep(2)

        pagination = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='pagination']"))
        )
        self.assertTrue(pagination.is_displayed(), "Pagination container must be visible when items > 20.")

        page_label = driver.find_element(By.CSS_SELECTOR, "[data-testid='pagination-page']").text
        info_label = driver.find_element(By.CSS_SELECTOR, "[data-testid='pagination-info']").text

        print(f"      Current Page: '{page_label}'")
        print(f"      Summary: '{info_label}'")
        print(f"      Total tasks: {TOTAL_TEST_TASKS}")

        self.assertIn("Page 1 of", page_label, "Should initially be on Page 1.")
        self.assertIn("Showing 1–20 of 25", info_label, "Page 1 should display items 1 to 20 of 25.")

        prev_button = driver.find_element(By.CSS_SELECTOR, "[data-testid='pagination-prev']")
        next_button = driver.find_element(By.CSS_SELECTOR, "[data-testid='pagination-next']")

        self.assertFalse(prev_button.is_enabled(), "Previous button should be disabled on first page.")
        self.assertTrue(next_button.is_enabled(), "Next button should be enabled when multiple pages exist.")
        print("✓ Page controls verified: Previous is disabled, Next is enabled, 'Page 1 of 2' is shown.")

        # Step 4: Click Next Page and expect Page 2 loads
        print("\n[4/5] Clicking 'Next' button to load Page 2...")
        time.sleep(2)
        next_button.click()

        wait.until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, "[data-testid='pagination-page']"),
                "Page 2 of",
            )
        )
        time.sleep(2)

        page2_label = driver.find_element(By.CSS_SELECTOR, "[data-testid='pagination-page']").text
        info2_label = driver.find_element(By.CSS_SELECTOR, "[data-testid='pagination-info']").text

        print(f"      Updated Page: '{page2_label}'")
        print(f"      Updated Summary: '{info2_label}'")

        self.assertIn("Page 2 of", page2_label, "Should now be on Page 2.")
        self.assertIn("Showing 21–25 of 25", info2_label, "Page 2 should show 21–25 of 25.")
        print("✓ Next page loaded successfully with expected Page 2 records (21–25 of 25)!")

        # Step 5: Click Previous Page to navigate back to Page 1
        print("\n[5/5] Clicking 'Previous' button to navigate back to Page 1...")
        time.sleep(2)
        prev_button = driver.find_element(By.CSS_SELECTOR, "[data-testid='pagination-prev']")
        self.assertTrue(prev_button.is_enabled(), "Previous button should now be enabled on Page 2.")
        prev_button.click()

        wait.until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, "[data-testid='pagination-page']"),
                "Page 1 of",
            )
        )
        time.sleep(2)

        page1_returned = driver.find_element(By.CSS_SELECTOR, "[data-testid='pagination-page']").text
        self.assertIn("Page 1 of", page1_returned, "Should return back to Page 1.")
        print("✓ Returned to Page 1 successfully.")

        print("\n=======================================================")
        print("🎉 ST-121 / TC-53 Selenium Test: 100% PASSED!")
        print("=======================================================\n")


if __name__ == "__main__":
    unittest.main()
