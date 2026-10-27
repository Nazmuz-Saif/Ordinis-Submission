"""
ST-140 tests: Full name support and profile endpoint whitelist.

  TC-95  [Selenium] Register a new company with a full name — expect the top bar
         and the Employees list to show that name.
  TC-96  [API] PATCH the profile with a new phone and also with email, department and salary
         — expect only the phone changed and the other fields ignored or refused.

Needs both servers running.
Run:  cd backend && python tests/test_st140_selenium.py        (HEADLESS=1 hides the window)
"""
import os
import sys
import time
import unittest
import urllib.request
import json

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(TESTS_DIR)
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, TESTS_DIR)
sys.path.insert(0, os.path.join(BACKEND_DIR, 'apps'))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
import django
django.setup()

from selenium_helpers import (  # noqa: E402
    BACKEND_API_URL,
    DEMO_PASSWORD,
    DEMO_USERS,
    FRONTEND_URL,
    clear_session,
    land_after_registration,
    login_as_demo,
    make_driver,
)

from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402


class ST140PersonNamesSeleniumTest(unittest.TestCase):
    def setUp(self):
        self.driver, self.wait = make_driver()

    def tearDown(self):
        try:
            self.driver.get(f'{FRONTEND_URL}/login')
            clear_session(self.driver)
        except Exception:
            pass
        self.driver.quit()

    def test_tc95_register_company_with_full_name_displayed(self):
        """TC-95: Register new company with full name -> top bar and Employees list show that name."""
        ts = int(time.time())
        company_name = f"Apex Labs {ts}"
        subdomain = f"apex-{ts}"
        full_name = f"Dr. Arham Chowdhury {ts}"
        email = f"ceo.{ts}@apex.test"
        password = "ValidPassword123!"

        self.driver.get(f"{FRONTEND_URL}/register")
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Create your company']")))

        # Fill registration form
        self.driver.find_element(By.NAME, "company_name").send_keys(company_name)
        # Clear and fill subdomain
        sub_elem = self.driver.find_element(By.NAME, "subdomain")
        sub_elem.clear()
        sub_elem.send_keys(subdomain)

        self.driver.find_element(By.NAME, "ceo_full_name").send_keys(full_name)
        self.driver.find_element(By.NAME, "ceo_email").send_keys(email)
        self.driver.find_element(By.NAME, "ceo_password").send_keys(password)

        # Submit
        self.driver.find_element(By.XPATH, "//button[@type='submit'][contains(., 'Create company')]").click()

        # Handle subscription activation for the new company
        self.wait.until(lambda d: '/subscribe' in d.current_url)
        from billing.models import Subscription
        Subscription.objects.filter(company__name=company_name).update(status=Subscription.STATUS_ACTIVE)
        self.driver.get(f"{FRONTEND_URL}/organization")
        self.wait.until(EC.url_contains("/organization"))

        # 1. Verify Top Bar shows the full name once user profile is loaded
        self.wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, "[data-testid='user-name']"), full_name))
        user_name_elem = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='user-name']")
        self.assertEqual(user_name_elem.text.strip(), full_name, f"Top bar should show full name '{full_name}'")

        # 2. Open /organization/employees and verify full name is in the list
        self.driver.get(f"{FRONTEND_URL}/organization/employees")
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Employees']")))

        body_text = self.wait.until(EC.visibility_of_element_located((By.TAG_NAME, "table"))).text
        self.assertIn(full_name, body_text, f"Employees table must display the full name '{full_name}'")

    def test_tc96_patch_profile_whitelist_refusal(self):
        """TC-96: [API] PATCH profile with new phone, email, department, salary -> refused/only phone changed."""
        # 1. Log in via API as demo Employee
        login_req = urllib.request.Request(
            f"{BACKEND_API_URL}/auth/login/",
            data=json.dumps({"email": DEMO_USERS["Employee"], "password": DEMO_PASSWORD}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(login_req) as resp:
            login_data = json.loads(resp.read().decode("utf-8"))
        access_token = login_data["access"]
        auth_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        # 2. Get initial profile
        get_req = urllib.request.Request(f"{BACKEND_API_URL}/auth/profile/", headers=auth_headers, method="GET")
        with urllib.request.urlopen(get_req) as resp:
            initial_profile = json.loads(resp.read().decode("utf-8"))["data"]

        initial_email = initial_profile["email"]
        initial_department = initial_profile.get("department_name")

        # 3. PATCH profile with phone AND non-whitelisted fields (email, department, salary)
        new_phone = "+880 1799-887766"
        attack_payload = {
            "phone": new_phone,
            "email": "hacked@evil.com",
            "department": "99999",
            "base_salary": "999999",
        }
        patch_req = urllib.request.Request(
            f"{BACKEND_API_URL}/auth/profile/",
            data=json.dumps(attack_payload).encode("utf-8"),
            headers=auth_headers,
            method="PATCH",
        )

        refused = False
        try:
            with urllib.request.urlopen(patch_req) as resp:
                pass
        except urllib.error.HTTPError as err:
            self.assertEqual(err.code, 400, "Disallowed fields in profile PATCH must return 400 Bad Request")
            err_body = json.loads(err.read().decode("utf-8"))
            field_errors = err_body.get("error", {}).get("field_errors", {})
            self.assertIn("email", field_errors, "Email should be refused in field_errors")
            self.assertIn("department", field_errors, "Department should be refused in field_errors")
            self.assertIn("base_salary", field_errors, "Base salary should be refused in field_errors")
            refused = True

        self.assertTrue(refused, "Server must refuse non-whitelisted fields")

        # Verify nothing changed after refusal
        with urllib.request.urlopen(get_req) as resp:
            current_profile = json.loads(resp.read().decode("utf-8"))["data"]
        self.assertEqual(current_profile["email"], initial_email)
        self.assertEqual(current_profile.get("department_name"), initial_department)

        # 4. Now PATCH with only the whitelisted field (phone)
        valid_req = urllib.request.Request(
            f"{BACKEND_API_URL}/auth/profile/",
            data=json.dumps({"phone": new_phone}).encode("utf-8"),
            headers=auth_headers,
            method="PATCH",
        )
        with urllib.request.urlopen(valid_req) as resp:
            self.assertEqual(resp.status, 200)
            updated_profile = json.loads(resp.read().decode("utf-8"))["data"]

        self.assertEqual(updated_profile["phone"], new_phone, "Whitelisted phone should be updated")
        self.assertEqual(updated_profile["email"], initial_email, "Email must remain untouched")


if __name__ == '__main__':
    unittest.main(verbosity=2)
