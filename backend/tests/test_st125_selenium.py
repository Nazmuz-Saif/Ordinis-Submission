"""
ST-125 Selenium tests (TC-61 to TC-63): Kanban board and daily progress.

TC-61  Open the Kanban board: the four columns with counts and Task cards are shown.
TC-62  As the assignee add a daily progress entry: it appears on the Task timeline.
TC-63  As a different Employee try to add progress to someone else's Task: it is blocked.

Run (backend on :8000 and frontend running, company "acme" already registered, ST-125 applied):

    cd backend
    python tests/test_st125_selenium.py

The frontend address defaults to http://localhost:5173. Override it if yours differs:

    set FRONTEND_URL=http://localhost:5174        (Windows)

The test users are created in the database by the test itself (password TestPass123).
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
from selenium.webdriver.support.ui import WebDriverWait

from attendance.services import local_today
from organization.models import Employee
from rbac.models import EmployeeRole, Permission, Role
from tasks.models import Task, TaskProgressLog
from tenants.models import Company

User = get_user_model()

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from selenium_helpers import FRONTEND_URL, login, BACKEND_API_URL  # noqa: E402  (one shared place: tests/selenium_helpers.py)
COMPANY_SUBDOMAIN = os.environ.get("COMPANY_SUBDOMAIN", "acme")
PASSWORD = "TestPass123"

MANAGER_EMAIL = "sel125-manager@acme.com"      # holds create_task: sees every task of the company
ASSIGNEE_EMAIL = "sel125-assignee@acme.com"    # no roles: the one task owner
OTHER_EMAIL = "sel125-other@acme.com"          # no roles, not involved in any task

PREFIX = "SEL125"

# Board columns: key -> (label shown on the board, task statuses that belong in it)
COLUMNS = {
    "todo": ("To Do", ["not_started", "rejected"]),
    "in_progress": ("In Progress", ["in_progress"]),
    "review": ("Review", ["submitted"]),
    "done": ("Done", ["completed"]),
}


# ---------------------------------------------------------------------------
# Selectors (one place, so a change in the page is a one-line fix here)
# ---------------------------------------------------------------------------

def css(testid):
    return f"[data-testid='{testid}']"


def column_css(key):
    return css(f"kanban-column-{key}")


def card_xpath(title, column=None):
    """A card on the board, found by its title (optionally only inside one column)."""
    scope = f"//section[@data-testid='kanban-column-{column}']" if column else ""
    return f"{scope}//div[@data-testid='kanban-card'][.//button[@data-testid='card-title'][normalize-space()='{title}']]"


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

    manager = _employee(company, MANAGER_EMAIL, "SEL125-M")
    assignee = _employee(company, ASSIGNEE_EMAIL, "SEL125-A")
    other = _employee(company, OTHER_EMAIL, "SEL125-O")

    role, _ = Role.objects.get_or_create(
        company=company, name="Selenium Task Manager",
        defaults={"description": "ST-116 / ST-125 Selenium role"},
    )
    role.permissions.set(Permission.objects.filter(codename="create_task"))
    EmployeeRole.objects.get_or_create(employee=manager, role=role, defaults={"company": company})
    EmployeeRole.objects.filter(employee__in=[assignee, other]).delete()

    Task.objects.filter(title__startswith=PREFIX).delete()   # progress entries go with them
    return company, manager, assignee, other


def make_task(company, manager, assignee, title, status="not_started", priority="high"):
    # High priority and an early deadline put these cards at the top of their column,
    # so they are on the board even when the company has other tasks too.
    return Task.objects.create(
        company=company, title=title, assigned_to=assignee, assigned_by=manager,
        priority=priority, status=status, deadline="2020-01-01",
    )


def column_of(status):
    return next(key for key, (_, statuses) in COLUMNS.items() if status in statuses)


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

class ST125SeleniumTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.company, cls.manager, cls.assignee, cls.other = prepare_test_data()

    def setUp(self):
        self.driver = webdriver.Chrome(options=webdriver.ChromeOptions())
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 15)

    def tearDown(self):
        self.driver.quit()

    # --- browser helpers ----------------------------------------------------
    def login(self, email):
        login(self.driver, self.wait, email, PASSWORD)

    def open_board(self):
        self.driver.get(f"{FRONTEND_URL}/tasks/board")
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css("kanban-board"))))
        # the cards are drawn only after the board data arrives
        self.wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, css("kanban-card")))

    def find_card(self, title, column=None):
        return self.wait.until(EC.visibility_of_element_located((By.XPATH, card_xpath(title, column))))

    def open_panel(self, title):
        self.find_card(title).find_element(By.CSS_SELECTOR, css("card-title")).click()
        return self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, css("progress-panel"))))

    def close_panel(self):
        self.driver.find_element(By.CSS_SELECTOR, "[aria-label='Close']").click()
        self.wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, css("progress-panel"))))

    def set_value(self, element, value):
        # a range slider cannot be typed into; set it the way React expects
        self.driver.execute_script(
            """
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(arguments[0], arguments[1]);
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            """,
            element, value,
        )

    def by_testid(self, testid):
        return self.driver.find_elements(By.CSS_SELECTOR, css(testid))

    # --- checks that need no browser (also used to try the test without Chrome) -----------------
    def db_count_for_column(self, key):
        return Task.objects.filter(company=self.company, status__in=COLUMNS[key][1]).count()

    def check_progress_saved(self, task, text, percent, blocker, link):
        """The entry is stored for the assignee, with TODAY's date in the company's time zone."""
        entry = TaskProgressLog.objects.get(task=task)
        self.assertEqual(entry.employee_id, self.assignee.id)
        self.assertEqual(entry.update_text, text)
        self.assertEqual(entry.progress_percent, percent)
        self.assertEqual(entry.blocker_text, blocker)
        self.assertEqual(entry.external_reference_url, link)
        self.assertEqual(entry.date, local_today(self.company)[0])

    def check_progress_blocked_by_api(self, task):
        """Someone who is not the assignee cannot add progress, however they ask."""
        payload = {"update_text": "I did it", "progress_percent": 90}
        path = f"/tasks/tasks/{task.id}/progress/"

        # an uninvolved employee cannot even see the task
        status, body = _request("POST", path, api_token(OTHER_EMAIL), payload)
        self.assertEqual(status, 404, body)
        status, body = _request("GET", path, api_token(OTHER_EMAIL))
        self.assertEqual(status, 404, body)

        # the manager sees the task but is still not the assignee
        status, body = _request("POST", path, api_token(MANAGER_EMAIL), payload)
        self.assertEqual(status, 403, body)
        self.assertIn("Only the assignee", body)

        self.assertEqual(TaskProgressLog.objects.filter(task=task).count(), 0)

    # --- TC-61 ---------------------------------------------------------------
    def test_tc61_board_shows_four_columns_with_counts_and_cards(self):
        stamp = int(time.time())
        titles = {
            "todo": f"{PREFIX} todo {stamp}",
            "rejected": f"{PREFIX} rejected {stamp}",
            "in_progress": f"{PREFIX} doing {stamp}",
            "review": f"{PREFIX} review {stamp}",
            "done": f"{PREFIX} done {stamp}",
        }
        make_task(self.company, self.manager, self.assignee, titles["todo"], "not_started")
        make_task(self.company, self.manager, self.assignee, titles["rejected"], "rejected")
        make_task(self.company, self.manager, self.assignee, titles["in_progress"], "in_progress")
        make_task(self.company, self.manager, self.assignee, titles["review"], "submitted")
        make_task(self.company, self.manager, self.assignee, titles["done"], "completed")

        self.login(MANAGER_EMAIL)
        self.open_board()

        # the four columns, in order, with their names
        keys = [c.get_attribute("data-testid") for c in self.driver.find_elements(By.CSS_SELECTOR, "[data-testid^='kanban-column-']")]
        self.assertEqual(keys, [f"kanban-column-{k}" for k in COLUMNS])
        for key, (label, _) in COLUMNS.items():
            column = self.driver.find_element(By.CSS_SELECTOR, column_css(key))
            self.assertIn(label, column.find_element(By.TAG_NAME, "h2").text)

        # each column's count badge equals the number of tasks in that column
        for key in COLUMNS:
            badge = self.driver.find_element(By.CSS_SELECTOR, css(f"column-count-{key}"))
            self.assertEqual(int(badge.text), self.db_count_for_column(key), f"count of {key}")

        # every task is a card in the right column
        self.find_card(titles["todo"], "todo")
        self.find_card(titles["rejected"], "todo")
        self.find_card(titles["in_progress"], "in_progress")
        self.find_card(titles["review"], "review")
        self.find_card(titles["done"], "done")

        # a card shows the priority, the assignee, the deadline and a progress bar
        card = self.find_card(titles["todo"], "todo")
        self.assertIn("high", card.text.lower())          # the page shows it as "High" (CSS capitalizes it)
        self.assertIn(ASSIGNEE_EMAIL, card.text)
        self.assertIn("2020-01-01", card.text)
        self.assertEqual(card.find_element(By.CSS_SELECTOR, css("card-progress")).text, "0%")
        self.assertTrue(card.find_elements(By.CSS_SELECTOR, "[role='progressbar']"))

        # a rejected task sits in To Do and says so
        rejected = self.find_card(titles["rejected"], "todo")
        self.assertTrue(rejected.find_elements(By.CSS_SELECTOR, css("card-rejected")))
        self.assertFalse(card.find_elements(By.CSS_SELECTOR, css("card-rejected")))

    # --- TC-62 ---------------------------------------------------------------
    def test_tc62_assignee_adds_a_daily_progress_entry(self):
        title = f"{PREFIX} progress {int(time.time())}"
        task = make_task(self.company, self.manager, self.assignee, title, "in_progress")
        text = "Built the login form and the API call"
        blocker = "Waiting for the API keys"
        link = "https://github.com/acme/app/commit/abc123"

        self.login(ASSIGNEE_EMAIL)
        self.open_board()
        panel = self.open_panel(title)

        # the assignee gets the form; there is no file upload anywhere
        form = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, css("progress-form"))))
        self.assertEqual(panel.find_elements(By.CSS_SELECTOR, "input[type='file']"), [])
        self.assertEqual(self.by_testid("progress-entry"), [])      # a fresh task has no timeline yet

        form.find_element(By.CSS_SELECTOR, css("progress-text")).send_keys(text)
        self.set_value(form.find_element(By.CSS_SELECTOR, css("progress-percent")), "60")
        form.find_element(By.CSS_SELECTOR, css("progress-blocker")).send_keys(blocker)
        form.find_element(By.CSS_SELECTOR, css("progress-link")).send_keys(link)
        form.find_element(By.CSS_SELECTOR, css("progress-submit")).click()

        # the entry is on the timeline with the percent, the blocker and a safe link
        entry = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, css("progress-entry"))))
        self.assertIn(text, entry.text)
        self.assertIn("60%", entry.text)
        self.assertIn(f"Blocker: {blocker}", entry.text)
        anchor = entry.find_element(By.TAG_NAME, "a")
        self.assertEqual(anchor.get_attribute("href"), link)
        self.assertEqual(anchor.get_attribute("target"), "_blank")
        self.assertIn("noopener", anchor.get_attribute("rel"))
        # the form is ready for the next day's note
        self.assertEqual(form.find_element(By.CSS_SELECTOR, css("progress-text")).get_attribute("value"), "")

        # stored for the assignee, dated by the server
        self.check_progress_saved(task, text, 60, blocker, link)

        # the card on the board now shows the new percent and the blocker flag
        self.close_panel()
        self.wait.until(lambda d: d.find_element(By.XPATH, card_xpath(title)).find_element(
            By.CSS_SELECTOR, css("card-progress")).text == "60%")
        self.assertTrue(self.find_card(title).find_elements(By.CSS_SELECTOR, css("card-blocked")))

    # --- TC-63 ---------------------------------------------------------------
    def test_tc63_other_employee_cannot_add_progress_to_someones_task(self):
        title = f"{PREFIX} not-mine {int(time.time())}"
        task = make_task(self.company, self.manager, self.assignee, title, "in_progress")

        # asking the server directly: blocked, and nothing is saved
        self.check_progress_blocked_by_api(task)

        # the manager can open the task but only gets the timeline, never the form
        self.login(MANAGER_EMAIL)
        self.open_board()
        self.open_panel(title)
        self.assertEqual(self.by_testid("progress-form"), [])
        note = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, css("progress-readonly-note"))))
        self.assertIn("Only the assignee can add progress.", note.text)
        self.assertEqual(self.by_testid("progress-submit"), [])
        self.assertEqual(TaskProgressLog.objects.filter(task=task).count(), 0)

        # an uninvolved employee does not even see the card
        self.driver.execute_script("window.localStorage.clear();")
        self.driver.delete_all_cookies()
        self.login(OTHER_EMAIL)
        self.driver.get(f"{FRONTEND_URL}/tasks/board")
        self.wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, "[data-testid='kanban-board'], [data-testid='empty-state']"))
        self.assertEqual(self.driver.find_elements(By.XPATH, card_xpath(title)), [])
        self.assertEqual(TaskProgressLog.objects.filter(task=task).count(), 0)


if __name__ == "__main__":
    unittest.main()
