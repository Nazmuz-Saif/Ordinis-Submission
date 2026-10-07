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
from payroll.models import SalaryStructure
from rbac.models import EmployeeRole, Permission, Role
from tenants.models import Company

User = get_user_model()

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://127.0.0.1:8000/api/v1")
COMPANY_SUBDOMAIN = os.environ.get("COMPANY_SUBDOMAIN", "selenium-st118")
PASSWORD = "TestPass123"

ACCOUNTANT_EMAIL = "sel118-accountant@acme.com"   # finance Permission ase
MANAGER_EMAIL = "sel118-manager@acme.com"         # Accountant er upore, finance nai
PLAIN_EMAIL = "sel118-plain@acme.com"             # kono Role nai
TARGET_CODE = "SEL118-T"                          # jar Salary Structure banabo
TARGET_EMAIL = "sel118-target@acme.com"

SALARY_URL = f"{FRONTEND_URL}/payroll/salary-structures"


# ---------------------------------------------------------------------------
# Test data (database e shorashori)
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
    company, _ = Company.objects.get_or_create(
        subdomain=COMPANY_SUBDOMAIN, defaults={"name": "Selenium ST118"}
    )
        

    manager = _employee(company, MANAGER_EMAIL, "SEL118-M")
    accountant = _employee(company, ACCOUNTANT_EMAIL, "SEL118-A")
    plain = _employee(company, PLAIN_EMAIL, "SEL118-P")
    target = _employee(company, TARGET_EMAIL, TARGET_CODE)

    # Hierarchy: manager -> accountant (manager Accountant er upore)
    accountant.reports_to = manager
    accountant.save()

    finance_perm, _ = Permission.objects.get_or_create(
        codename="finance", defaults={"name": "Finance", "module": "payroll"}
    )

    finance_role, _ = Role.objects.get_or_create(
        company=company, name="Selenium Finance",
        defaults={"description": "ST-118 Selenium role"},
    )
    finance_role.permissions.set([finance_perm])

    other_role, _ = Role.objects.get_or_create(
        company=company, name="Selenium Plain Manager",
        defaults={"description": "ST-118 Selenium role without finance"},
    )
    other_role.permissions.set(Permission.objects.filter(codename="create_task"))

    # Role assignment poriskar kore abar set kori
    EmployeeRole.objects.filter(employee__in=[manager, accountant, plain, target]).delete()
    EmployeeRole.objects.create(employee=accountant, role=finance_role, company=company)
    EmployeeRole.objects.create(employee=manager, role=other_role, company=company)

    # Ager run er salary data muche, Accountant er jonno ekta structure rakhi (TC-47 er jonno)
    SalaryStructure.objects.filter(employee__employee_code__startswith="SEL118").delete()
    protected = SalaryStructure.objects.create(
        employee=accountant, company=company, base_salary=75000,
        allowances={}, effective_from="2026-01-01",
    )
    return company, manager, accountant, plain, target, protected


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

class ST118SalarySeleniumTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        (cls.company, cls.manager, cls.accountant,
         cls.plain, cls.target, cls.protected) = prepare_test_data()

    def setUp(self):
        SalaryStructure.objects.filter(employee=self.target).delete()
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
        # sidebar load hoyeche kina
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='sidebar']")))

    def by_testid(self, testid):
        return self.driver.find_elements(By.CSS_SELECTOR, f"[data-testid='{testid}']")

    def open_payroll_from_sidebar(self):
        """Sidebar theke Finance > Payroll e jai (full page reload chhara)."""
        group = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='sidebar-group-finance']"))
        )
        if group.get_attribute("aria-expanded") != "true":
            group.click()
        link = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='sidebar-link-Payroll']"))
        )
        link.click()
        self.wait.until(EC.url_contains("/payroll/salary-structures"))
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Payroll']")))
        # loading shesh: table ba empty state
        self.wait.until(lambda d: "Loading payroll" not in d.find_element(By.TAG_NAME, "body").text)

    def set_value(self, element, value):
        # React controlled input e value set korar shothik upay
        self.driver.execute_script(
            """
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(arguments[0], arguments[1]);
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            """,
            element, str(value),
        )

    def field(self, name):
        return self.driver.find_element(By.CSS_SELECTOR, f"[name='{name}']")

    def row(self):
        xpath = f"//tr[.//div[normalize-space()='{TARGET_CODE}']]"
        return self.wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))

    def wait_modal_closed_or_error(self):
        def done(driver):
            if driver.find_elements(By.XPATH, "//div[contains(@class,'bg-red-50')]"):
                return "error"
            modal_title = "//h2[normalize-space()='Add Salary Structure' or normalize-space()='Edit Salary Structure']"
            if not driver.find_elements(By.XPATH, modal_title):
                return "closed"
            return False
        result = self.wait.until(done)
        if result == "error":
            message = self.driver.find_element(By.XPATH, "//div[contains(@class,'bg-red-50')]").text
            self.fail(f"UI error message dekhacche: {message}")

    # --- TC-45 ---------------------------------------------------------------
    def test_tc45_without_finance_no_menu_and_api_403(self):
        self.login(PLAIN_EMAIL)

        # 1) sidebar e Payroll item nai
        self.assertEqual(self.by_testid("sidebar-link-Payroll"), [],
                         "finance permission chhara Payroll menu dekha jacche")

        # 2) shorashori URL e gele payroll page khole na
        self.driver.get(SALARY_URL)
        self.wait.until(lambda d: "/payroll/salary-structures" not in d.current_url)
        self.assertEqual(
            self.driver.find_elements(By.XPATH, "//button[normalize-space()='Add Structure']"), []
        )

        # 3) API 403 dey
        token = api_token(PLAIN_EMAIL)
        status, body = _request("GET", "/payroll/salary-structures/", token)
        self.assertEqual(status, 403, body)
        self.assertNotIn("base_salary", body)

        status, body = _request(
            "POST", "/payroll/salary-structures/", token,
            {"employee": str(self.target.id), "base_salary": "1000", "effective_from": "2026-01-01"},
        )
        self.assertEqual(status, 403, body)
        self.assertFalse(SalaryStructure.objects.filter(employee=self.target).exists())

    # --- TC-46 (create) ------------------------------------------------------
    def test_tc46a_finance_user_can_create_salary_structure(self):
        self.login(ACCOUNTANT_EMAIL)
        self.open_payroll_from_sidebar()

        self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "(//button[normalize-space()='Add Structure'])[1]"))
        ).click()
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h2[normalize-space()='Add Salary Structure']")))

        Select(self.field("employee")).select_by_value(str(self.target.id))
        self.field("base_salary").send_keys("50000")
        self.field("house_rent").send_keys("5000")
        self.field("medical").send_keys("2000")
        self.field("transport").send_keys("1000")
        self.set_value(self.field("effective_from"), "2026-10-01")
        self.driver.find_element(By.XPATH, "//button[normalize-space()='Save Structure']").click()

        self.wait_modal_closed_or_error()

        # gross = 50000 + 5000 + 2000 + 1000 = 58000
        row = self.row()
        self.assertIn("$58,000.00", row.text)

        saved = SalaryStructure.objects.get(employee=self.target)
        self.assertEqual(int(saved.base_salary), 50000)
        self.assertEqual(saved.company_id, self.company.id)

    # --- TC-46 (edit) --------------------------------------------------------
    def test_tc46b_finance_user_can_edit_salary_structure(self):
        SalaryStructure.objects.create(
            employee=self.target, company=self.company, base_salary=50000,
            allowances={"house_rent": 5000, "medical": 2000, "transport": 1000, "other": 0},
            effective_from="2026-10-01",
        )
        self.login(ACCOUNTANT_EMAIL)
        self.open_payroll_from_sidebar()

        row = self.row()
        row.find_element(By.XPATH, ".//td[last()]//button").click()
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Edit']"))).click()
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h2[normalize-space()='Edit Salary Structure']")))

        self.set_value(self.field("base_salary"), "60000")
        self.driver.find_element(By.XPATH, "//button[normalize-space()='Update Structure']").click()

        self.wait_modal_closed_or_error()

        # notun gross = 60000 + 8000 = 68000
        self.wait.until(lambda d: "$68,000.00" in self.row().text)
        saved = SalaryStructure.objects.get(employee=self.target)
        self.assertEqual(int(saved.base_salary), 60000)

    # --- TC-47 ---------------------------------------------------------------
    def test_tc47_manager_above_accountant_without_finance_is_blocked(self):
        # hierarchy check: manager sotti Accountant er upore
        self.accountant.refresh_from_db()
        self.assertEqual(self.accountant.reports_to_id, self.manager.id)
        self.assertFalse(self.manager.has_permission("finance"))

        self.login(MANAGER_EMAIL)
        self.assertEqual(self.by_testid("sidebar-link-Payroll"), [])

        self.driver.get(SALARY_URL)
        self.wait.until(lambda d: "/payroll/salary-structures" not in d.current_url)
        self.assertEqual(
            self.driver.find_elements(By.XPATH, "//button[normalize-space()='Add Structure']"), []
        )

        token = api_token(MANAGER_EMAIL)

        # list: 403, ar Accountant er salary (75000) response e leak hobe na
        status, body = _request("GET", "/payroll/salary-structures/", token)
        self.assertEqual(status, 403, body)
        self.assertNotIn("75000", body)

        # Accountant er nijer structure id diye chaleo 200 pabe na
        status, body = _request("GET", f"/payroll/salary-structures/{self.protected.id}/", token)
        self.assertNotEqual(status, 200, body)
        self.assertNotIn("75000", body)

        # shudhu dekha na, change o kora jabe na
        status, body = _request(
            "PATCH", f"/payroll/salary-structures/{self.protected.id}/", token, {"base_salary": "1"}
        )
        self.assertNotEqual(status, 200, body)
        self.protected.refresh_from_db()
        self.assertEqual(int(self.protected.base_salary), 75000)


if __name__ == "__main__":
    unittest.main()