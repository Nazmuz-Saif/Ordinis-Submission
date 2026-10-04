"""
ST-116 Selenium tests (TC-36 to TC-41): Tasks.

Run (backend on :8000 and frontend running, company "acme" already registered):

    cd backend
    python tests/test_st116_selenium.py

The frontend address defaults to http://localhost:5174. Override it if yours differs:

    set FRONTEND_URL=http://localhost:5173        (Windows)
"""
import json
import os
import sys
import time
import unittest
from urllib.error import HTTPError, URLError
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
from selenium.webdriver.support.ui import Select, WebDriverWait

from organization.models import Employee
from rbac.models import EmployeeRole, Permission, Role
from tasks.models import Task
from tenants.models import Company

User = get_user_model()

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5174")
BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://127.0.0.1:8000/api/v1")
COMPANY_SUBDOMAIN = os.environ.get("COMPANY_SUBDOMAIN", "acme")
PASSWORD = "TestPass123"

MANAGER_EMAIL = "sel116-manager@acme.com"      # holds create_task
ASSIGNEE_EMAIL = "sel116-assignee@acme.com"    # no roles
OTHER_EMAIL = "sel116-other@acme.com"          # no roles, not involved in any task
FOREIGN_EMAIL = "sel116-foreign@beta.com"      # belongs to a different company

PREFIX = "SEL116"


# ---------------------------------------------------------------------------
# Test data (created straight in the database)
# ---------------------------------------------------------------------------

def _employee(company, email, code):
    user, _ = User.objects.get_or_create(email=email, defaults={"company": company})
    user.company = company
    user.set_password(PASSWORD)
    user.save()
    employee, _ = Employee.objects.get_or_create(
        user=user, defaults={"company": company, "employee_code": code}
    )
    return employee


def prepare_test_data():
    company = Company.objects.get(subdomain=COMPANY_SUBDOMAIN)
    beta, _ = Company.objects.get_or_create(
        subdomain="selenium-beta", defaults={"name": "Selenium Beta"}
    )

    manager = _employee(company, MANAGER_EMAIL, "SEL116-M")
    assignee = _employee(company, ASSIGNEE_EMAIL, "SEL116-A")
    other = _employee(company, OTHER_EMAIL, "SEL116-O")
    foreign = _employee(beta, FOREIGN_EMAIL, "SEL116-F")

    role, _ = Role.objects.get_or_create(
        company=company, name="Selenium Task Manager",
        defaults={"description": "ST-116 Selenium role"},
    )
    role.permissions.set(Permission.objects.filter(codename="create_task"))
    EmployeeRole.objects.get_or_create(employee=manager, role=role, defaults={"company": company})
    EmployeeRole.objects.filter(employee__in=[assignee, other]).delete()

    Task.objects.filter(title__startswith=PREFIX).delete()
    return company, manager, assignee, other, foreign


def make_task(company, manager, assignee, title, status="not_started"):
    return Task.objects.create(
        company=company, title=title, assigned_to=assignee,
        assigned_by=manager, priority="medium", status=status,
    )


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _request(method, path, token=None, payload=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(f"{BACKEND_API_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, response.read().decode("utf-8")
    except HTTPError as error:
        return error.code, error.read().decode("utf-8")
    except URLError as error:
        return 0, str(error)


def api_token(email):
    status, body = _request("POST", "/auth/login/", payload={"email": email, "password": PASSWORD})
    assert status == 200, f"login failed for {email}: {status} {body}"
    return json.loads(body)["access"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class ST116SeleniumTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        (cls.company, cls.manager, cls.assignee, cls.other, cls.foreign) = prepare_test_data()

    def setUp(self):
        self.driver = webdriver.Chrome(options=webdriver.ChromeOptions())
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 15)

    def tearDown(self):
        self.driver.quit()

    # --- browser helpers ----------------------------------------------------
    def login(self, email):
        self.driver.get(f"{FRONTEND_URL}/login")
        email_input = self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
        )
        email_input.send_keys(email)
        self.driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(PASSWORD)
        self.driver.find_element(By.XPATH, "//button[normalize-space()='Login']").click()
        self.wait.until(EC.url_contains("/organization"))

    def clear_session(self):
        self.driver.execute_script("window.localStorage.clear();")
        self.driver.delete_all_cookies()

    def open_tasks(self):
        self.driver.get(f"{FRONTEND_URL}/tasks")
        self.wait.until(
            EC.presence_of_element_located((By.XPATH, "//h1[normalize-space()='Tasks']"))
        )
        # wait until loading is over: either the table or the empty state is shown
        self.wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, "[data-testid='task-row'], [data-testid='empty-state']"))

    def row_xpath(self, title):
        return f"//tr[@data-testid='task-row'][.//p[normalize-space()='{title}']]"

    def find_row(self, title):
        return self.wait.until(EC.visibility_of_element_located((By.XPATH, self.row_xpath(title))))

    def set_date(self, element, value):
        # a date input cannot be typed into reliably; set it the way React expects
        self.driver.execute_script(
            """
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(arguments[0], arguments[1]);
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            """,
            element, value,
        )

    def by_testid(self, testid):
        return self.driver.find_elements(By.CSS_SELECTOR, f"[data-testid='{testid}']")

    # --- TC-36 ---------------------------------------------------------------
    def test_tc36_create_task_with_priority_and_deadline(self):
        title = f"{PREFIX} create {int(time.time())}"
        self.login(MANAGER_EMAIL)
        self.open_tasks()

        self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='new-task-button']"))).click()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='task-form']")))

        self.driver.find_element(By.CSS_SELECTOR, "[data-testid='task-title']").send_keys(title)
        Select(self.driver.find_element(By.CSS_SELECTOR, "[data-testid='task-assignee']")).select_by_value(str(self.assignee.id))
        Select(self.driver.find_element(By.CSS_SELECTOR, "[data-testid='task-priority']")).select_by_value("high")
        self.set_date(self.driver.find_element(By.CSS_SELECTOR, "[data-testid='task-deadline']"), "2026-12-31")
        self.driver.find_element(By.CSS_SELECTOR, "[data-testid='task-save']").click()

        row = self.find_row(title)
        text = row.text
        self.assertIn(ASSIGNEE_EMAIL, text)
        self.assertIn("High", text)
        self.assertIn("2026-12-31", text)
        self.assertIn("Not Started", text)

        task = Task.objects.get(title=title)
        self.assertEqual(task.assigned_to_id, self.assignee.id)
        self.assertEqual(task.assigned_by_id, self.manager.id)

    # --- TC-37 ---------------------------------------------------------------
    def test_tc37_cannot_assign_to_another_company(self):
        title = f"{PREFIX} foreign {int(time.time())}"
        token = api_token(MANAGER_EMAIL)

        status, body = _request(
            "POST", "/tasks/tasks/", token,
            {"title": title, "assigned_to": str(self.foreign.id), "priority": "low"},
        )
        self.assertEqual(status, 400, body)
        self.assertFalse(Task.objects.filter(title=title).exists())

        # the form does not even offer the other company's employee
        self.login(MANAGER_EMAIL)
        self.open_tasks()
        self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='new-task-button']"))).click()
        dropdown = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='task-assignee']")))
        values = [o.get_attribute("value") for o in Select(dropdown).options]
        self.assertIn(str(self.assignee.id), values)
        self.assertNotIn(str(self.foreign.id), values)

    # --- TC-38 ---------------------------------------------------------------
    def test_tc38_edit_delete_and_no_buttons_without_permission(self):
        title = f"{PREFIX} edit {int(time.time())}"
        new_title = f"{title} renamed"
        make_task(self.company, self.manager, self.assignee, title)

        self.login(MANAGER_EMAIL)
        self.open_tasks()
        row = self.find_row(title)
        row.find_element(By.CSS_SELECTOR, "[data-testid='edit-task']").click()
        title_input = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='task-title']")))
        title_input.clear()
        title_input.send_keys(new_title)
        self.driver.find_element(By.CSS_SELECTOR, "[data-testid='task-save']").click()

        row = self.find_row(new_title)
        row.find_element(By.CSS_SELECTOR, "[data-testid='delete-task']").click()
        self.wait.until(EC.alert_is_present())
        self.driver.switch_to.alert.accept()
        self.wait.until(EC.invisibility_of_element_located((By.XPATH, self.row_xpath(new_title))))
        self.assertFalse(Task.objects.filter(title__in=[title, new_title]).exists())

        # an employee without create_task sees the task but has no create/edit/delete controls
        visible_title = f"{PREFIX} view {int(time.time())}"
        make_task(self.company, self.manager, self.assignee, visible_title)
        self.clear_session()
        self.login(ASSIGNEE_EMAIL)
        self.open_tasks()
        self.find_row(visible_title)
        self.assertEqual(self.by_testid("new-task-button"), [])
        self.assertEqual(self.by_testid("edit-task"), [])
        self.assertEqual(self.by_testid("delete-task"), [])

    # --- TC-39 ---------------------------------------------------------------
    def test_tc39_assignee_submits_in_progress_task(self):
        title = f"{PREFIX} submit {int(time.time())}"
        task = make_task(self.company, self.manager, self.assignee, title, status="in_progress")

        self.login(ASSIGNEE_EMAIL)
        self.open_tasks()
        row = self.find_row(title)
        row.find_element(By.CSS_SELECTOR, "[data-testid='submit-task']").click()

        self.wait.until(lambda d: "Submitted" in d.find_element(By.XPATH, self.row_xpath(title)).text)
        task.refresh_from_db()
        self.assertEqual(task.status, "submitted")

    # --- TC-40 ---------------------------------------------------------------
    def test_tc40_completed_cannot_go_back_to_not_started(self):
        title = f"{PREFIX} completed {int(time.time())}"
        task = make_task(self.company, self.manager, self.assignee, title, status="completed")
        token = api_token(MANAGER_EMAIL)

        status, body = _request("PATCH", f"/tasks/tasks/{task.id}/", token, {"status": "not_started"})
        self.assertEqual(status, 400, body)
        self.assertIn("Completed to Not Started", body)

        task.refresh_from_db()
        self.assertEqual(task.status, "completed")

        self.login(MANAGER_EMAIL)
        self.open_tasks()
        row = self.find_row(title)
        self.assertIn("Completed", row.text)
        for button in ("start-task", "submit-task", "complete-task", "reject-task"):
            self.assertEqual(row.find_elements(By.CSS_SELECTOR, f"[data-testid='{button}']"), [])

    # --- TC-41 ---------------------------------------------------------------
    def test_tc41_other_employee_cannot_submit_someones_task(self):
        title = f"{PREFIX} not-mine {int(time.time())}"
        task = make_task(self.company, self.manager, self.assignee, title, status="in_progress")

        # an uninvolved employee cannot even see the task
        status, body = _request("POST", f"/tasks/tasks/{task.id}/submit/", api_token(OTHER_EMAIL))
        self.assertEqual(status, 404, body)
        # the manager can see it but is still not the assignee
        status, body = _request("POST", f"/tasks/tasks/{task.id}/submit/", api_token(MANAGER_EMAIL))
        self.assertEqual(status, 403, body)

        task.refresh_from_db()
        self.assertEqual(task.status, "in_progress")

        self.login(OTHER_EMAIL)
        self.open_tasks()
        self.assertEqual(self.driver.find_elements(By.XPATH, self.row_xpath(title)), [])
        self.assertEqual(self.by_testid("submit-task"), [])


if __name__ == "__main__":
    unittest.main()
