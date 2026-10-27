"""
ST-142 Selenium tests: Temporary password, must_change_password gate, and token revocation.

  TC-99   [Selenium] As the CEO add an Employee without typing a password — expect a temporary
          password shown once, and the browser not filling the email or password fields.
  TC-100  [Selenium] Log in as that Employee — expect to be sent to My Profile to set a new password
          before anything else; change it with a wrong current password first — expect an error, then success.
  TC-101  [Selenium] Change a password, then use an older refresh token — expect it refused.

Needs both servers running.
Run:  cd backend && python tests/test_st142_selenium.py        (HEADLESS=1 hides the window)
"""
import json
import os
import sys
import time
import unittest
import urllib.request
import urllib.error

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
    login_as_demo,
    make_driver,
)

from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402
from billing.models import Subscription, SubscriptionPlan  # noqa: E402
from accounts.models import User  # noqa: E402
from organization.models import Employee  # noqa: E402


def set_input_value(driver, elem, val):
    driver.execute_script("""
        const input = arguments[0];
        const val = arguments[1];
        const lastVal = input.value;
        input.value = val;
        const tracker = input._valueTracker;
        if (tracker) { tracker.setValue(lastVal); }
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
    """, elem, val)


class ST142PasswordSecuritySeleniumTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Temporarily increase demo company's limit so test employees can be added
        pro_plan = SubscriptionPlan.objects.get(name='Professional')
        Subscription.objects.filter(company__subdomain='demo-acme').update(plan=pro_plan)

    @classmethod
    def tearDownClass(cls):
        # Restore demo company to Basic plan and clean up test records
        basic_plan = SubscriptionPlan.objects.get(name='Basic')
        Subscription.objects.filter(company__subdomain='demo-acme').update(plan=basic_plan)
        test_users = User.objects.filter(email__contains='@acme.test')
        Employee.objects.filter(user__in=test_users).delete()
        test_users.delete()
        super().tearDownClass()
        test_users.delete()
        super().tearDownClass()

    def setUp(self):
        self.driver, self.wait = make_driver()

    def tearDown(self):
        try:
            self.driver.get(f'{FRONTEND_URL}/login')
            clear_session(self.driver)
        except Exception:
            pass
        self.driver.quit()

    def test_tc99_add_employee_temporary_password_and_autocomplete(self):
        """TC-99: CEO adds Employee with no password -> temporary password shown once, autocomplete off/new-password."""
        login_as_demo(self.driver, self.wait, 'CEO')
        self.driver.get(f"{FRONTEND_URL}/organization/employees")
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Employees']")))

        # Check autocomplete attributes on form inputs
        full_name_input = self.wait.until(EC.visibility_of_element_located((By.NAME, "full_name")))
        email_input = self.driver.find_element(By.NAME, "email")
        password_input = self.driver.find_element(By.NAME, "password")

        self.assertEqual(full_name_input.get_attribute("autocomplete"), "off")
        self.assertEqual(email_input.get_attribute("autocomplete"), "off")
        self.assertEqual(password_input.get_attribute("autocomplete"), "new-password")

        # Create new employee leaving password field empty
        ts = int(time.time())
        emp_name = f"Temp User {ts}"
        emp_email = f"temp.{ts}@acme.test"
        emp_code = f"TMP{ts % 10000:04d}"

        set_input_value(self.driver, full_name_input, emp_name)
        set_input_value(self.driver, email_input, emp_email)
        code_input = self.driver.find_element(By.NAME, "employee_code")
        set_input_value(self.driver, code_input, emp_code)

        # Ensure password input remains empty
        self.assertEqual(password_input.get_attribute("value"), "")

        # Submit create employee form
        self.driver.find_element(By.XPATH, "//form//button[contains(., 'Add Employee')]").click()

        # Temporary password box must appear
        temp_box = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='temp-password-box']")))
        self.assertTrue(temp_box.is_displayed())

        temp_pass_elem = temp_box.find_element(By.CSS_SELECTOR, "[data-testid='temp-password']")
        temp_password = temp_pass_elem.text.strip()
        self.assertGreaterEqual(len(temp_password), 8, "Temporary password must be generated and non-empty")

        # Copy button should be present
        copy_btn = temp_box.find_element(By.CSS_SELECTOR, "[data-testid='copy-temp-password']")
        self.assertTrue(copy_btn.is_displayed())

        # Reload page: temporary password is shown once only
        self.driver.refresh()
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Employees']")))
        self.assertEqual(len(self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='temp-password-box']")), 0,
                         "Temporary password must not persist across reloads (shown once only)")

    def test_tc100_temporary_password_redirects_and_password_change(self):
        """TC-100: Employee logs in with temp password -> gated to My Profile; wrong current pass errors, correct succeeds."""
        # 1. Create employee via API to get guaranteed temporary password
        ceo_login_req = urllib.request.Request(
            f"{BACKEND_API_URL}/auth/login/",
            data=json.dumps({"email": DEMO_USERS["CEO"], "password": DEMO_PASSWORD}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(ceo_login_req) as resp:
            ceo_token = json.loads(resp.read().decode("utf-8"))["access"]

        ts = int(time.time())
        emp_email = f"mustchange.{ts}@acme.test"
        emp_code = f"MC{ts % 10000:04d}"
        create_emp_req = urllib.request.Request(
            f"{BACKEND_API_URL}/organization/employees/",
            data=json.dumps({
                "full_name": f"Gated User {ts}",
                "email": emp_email,
                "employee_code": emp_code,
            }).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {ceo_token}"},
            method="POST",
        )
        with urllib.request.urlopen(create_emp_req) as resp:
            emp_data = json.loads(resp.read().decode("utf-8"))
        temp_password = emp_data["temporary_password"]

        # 2. Log in with temporary password in browser
        self.driver.get(f"{FRONTEND_URL}/login")
        clear_session(self.driver)

        email_input = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
        email_input.send_keys(emp_email)
        pw_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        pw_input.send_keys(temp_password)
        self.driver.find_element(By.XPATH, "//button[normalize-space()='Login' or normalize-space()='Log in']").click()

        # 3. Expect forced redirect to /profile
        self.wait.until(lambda d: "/profile" in d.current_url)
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='must-change-banner']")))

        # 4. Try changing password with WRONG current password
        current_pw_input = self.wait.until(EC.visibility_of_element_located((By.ID, "pw-current")))
        next_pw_input = self.driver.find_element(By.ID, "pw-next")
        confirm_pw_input = self.driver.find_element(By.ID, "pw-confirm")

        new_password = "BrandNewSecurePassword123!"

        set_input_value(self.driver, current_pw_input, "WrongCurrentPassword123!")
        set_input_value(self.driver, next_pw_input, new_password)
        set_input_value(self.driver, confirm_pw_input, new_password)

        save_pw_btn = self.wait.until(lambda d: d.find_element(By.CSS_SELECTOR, "[data-testid='password-save']"))
        self.wait.until(lambda d: not save_pw_btn.get_attribute("disabled"))
        save_pw_btn.click()

        # Expect error message
        self.wait.until(lambda d: (
            len(d.find_elements(By.CSS_SELECTOR, "[data-testid='password-error']")) > 0 or
            len(d.find_elements(By.CSS_SELECTOR, "[data-testid='error-password-current']")) > 0
        ))
        # Must change banner should still be present
        self.assertTrue(self.driver.find_element(By.CSS_SELECTOR, "[data-testid='must-change-banner']").is_displayed())

        # 5. Enter CORRECT current password and save
        set_input_value(self.driver, current_pw_input, temp_password)
        set_input_value(self.driver, next_pw_input, new_password)
        set_input_value(self.driver, confirm_pw_input, new_password)

        self.wait.until(lambda d: not save_pw_btn.get_attribute("disabled"))
        save_pw_btn.click()

        # Expect success message
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='password-success']")))

        # Banner should disappear
        self.wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, "[data-testid='must-change-banner']")) == 0)

    def test_tc101_change_password_blacklists_older_tokens(self):
        """TC-101: Change password -> older JWT refresh tokens are blacklisted and refused."""
        ceo_login = urllib.request.Request(
            f"{BACKEND_API_URL}/auth/login/",
            data=json.dumps({"email": DEMO_USERS["CEO"], "password": DEMO_PASSWORD}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(ceo_login) as resp:
            ceo_token = json.loads(resp.read().decode("utf-8"))["access"]

        ts = int(time.time())
        test_email = f"tokenrevocation.{ts}@acme.test"
        old_pass = "InitialPass123!"
        new_pass = "RevokedPass123!"

        create_req = urllib.request.Request(
            f"{BACKEND_API_URL}/organization/employees/",
            data=json.dumps({
                "full_name": f"Revoke User {ts}",
                "email": test_email,
                "password": old_pass,
                "employee_code": f"TR{ts % 10000:04d}",
            }).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {ceo_token}"},
            method="POST",
        )
        with urllib.request.urlopen(create_req):
            pass

        # Session 1: obtain tokens
        login_req_1 = urllib.request.Request(
            f"{BACKEND_API_URL}/auth/login/",
            data=json.dumps({"email": test_email, "password": old_pass}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(login_req_1) as resp:
            session_1 = json.loads(resp.read().decode("utf-8"))
        older_refresh_token = session_1["refresh"]

        # Session 2: obtain another set of tokens
        login_req_2 = urllib.request.Request(
            f"{BACKEND_API_URL}/auth/login/",
            data=json.dumps({"email": test_email, "password": old_pass}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(login_req_2) as resp:
            session_2 = json.loads(resp.read().decode("utf-8"))
        current_access = session_2["access"]
        current_refresh = session_2["refresh"]

        # Verify older refresh token works before password change
        refresh_check_req = urllib.request.Request(
            f"{BACKEND_API_URL}/auth/refresh/",
            data=json.dumps({"refresh": older_refresh_token}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(refresh_check_req) as resp:
            self.assertEqual(resp.status, 200, "Older refresh token should work before change")

        # Now change password using Session 2
        change_req = urllib.request.Request(
            f"{BACKEND_API_URL}/auth/change-password/",
            data=json.dumps({
                "current_password": old_pass,
                "new_password": new_pass,
                "confirm_password": new_pass,
                "refresh": current_refresh,
            }).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {current_access}"},
            method="POST",
        )
        with urllib.request.urlopen(change_req) as resp:
            self.assertEqual(resp.status, 200)

        # Now try to use the older refresh token -> MUST BE REFUSED (401)
        older_refresh_retry = urllib.request.Request(
            f"{BACKEND_API_URL}/auth/refresh/",
            data=json.dumps({"refresh": older_refresh_token}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(older_refresh_retry)
        self.assertEqual(ctx.exception.code, 401, "Older refresh token must be blacklisted and refused with 401")


if __name__ == '__main__':
    unittest.main(verbosity=2)
