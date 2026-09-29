import json
import os
import sys
import time
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.development",
)

import django

django.setup()

from django.contrib.auth import get_user_model
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from organization.models import Designation, Employee, EmployeeRole
from roles.models import Permission, Role
from tenants.models import Company


User = get_user_model()

FRONTEND_URL = "http://localhost:5174"
BACKEND_API_URL = "http://127.0.0.1:8000/api/v1"

NO_PERMISSION_EMAIL = "selenium-nopermission@acme.com"
WITH_PERMISSION_EMAIL = "selenium-permission@acme.com"
PASSWORD = "TestPass123"

NO_PERMISSION_CODE = "SEL-NO-001"
WITH_PERMISSION_CODE = "SEL-YES-001"

ROLE_NAME = "Selenium Department Tester"
DEPARTMENT_NAME = f"Selenium Allowed Department {int(time.time())}"


def prepare_test_data():
    company = Company.objects.get(
        subdomain="acme"
    )

    designation = Designation.objects.get(
        company=company,
        title="CEO",
    )

    permission = Permission.objects.get(
        codename="manage_departments"
    )

    no_permission_user = User.objects.filter(
        email=NO_PERMISSION_EMAIL
    ).first()

    if no_permission_user is None:
        no_permission_user = User.objects.create_user(
            email=NO_PERMISSION_EMAIL,
            password=PASSWORD,
            company=company,
        )
    else:
        no_permission_user.set_password(PASSWORD)
        no_permission_user.company = company
        no_permission_user.save()

    no_permission_employee = Employee.objects.filter(
        user=no_permission_user
    ).first()

    if no_permission_employee is None:
        no_permission_employee = Employee.objects.create(
            user=no_permission_user,
            company=company,
            designation=designation,
            employee_code=NO_PERMISSION_CODE,
        )

    EmployeeRole.objects.filter(
        employee=no_permission_employee
    ).delete()

    with_permission_user = User.objects.filter(
        email=WITH_PERMISSION_EMAIL
    ).first()

    if with_permission_user is None:
        with_permission_user = User.objects.create_user(
            email=WITH_PERMISSION_EMAIL,
            password=PASSWORD,
            company=company,
        )
    else:
        with_permission_user.set_password(PASSWORD)
        with_permission_user.company = company
        with_permission_user.save()

    with_permission_employee = Employee.objects.filter(
        user=with_permission_user
    ).first()

    if with_permission_employee is None:
        with_permission_employee = Employee.objects.create(
            user=with_permission_user,
            company=company,
            designation=designation,
            employee_code=WITH_PERMISSION_CODE,
        )

    role, _ = Role.objects.get_or_create(
        company=company,
        name=ROLE_NAME,
        defaults={
            "description": "Selenium test role",
        },
    )

    role.permissions.set([permission])

    EmployeeRole.objects.update_or_create(
        employee=with_permission_employee,
        role=role,
        defaults={
            "company": company,
        },
    )

    return no_permission_user, with_permission_user


class ST110SeleniumTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        (
            cls.no_permission_user,
            cls.with_permission_user,
        ) = prepare_test_data()

    def setUp(self):
        options = webdriver.ChromeOptions()

        self.driver = webdriver.Chrome(
            options=options
        )

        self.driver.maximize_window()

        self.wait = WebDriverWait(
            self.driver,
            15,
        )

    def login(self, email):
        self.driver.get(
            f"{FRONTEND_URL}/login"
        )

        email_input = self.wait.until(
            EC.visibility_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "input[type='email']",
                )
            )
        )

        password_input = self.driver.find_element(
            By.CSS_SELECTOR,
            "input[type='password']",
        )

        email_input.send_keys(email)

        password_input.send_keys(
            PASSWORD
        )

        self.driver.find_element(
            By.XPATH,
            "//button[normalize-space()='Login']",
        ).click()

        self.wait.until(
            EC.url_contains(
                "/organization"
            )
        )

        self.driver.refresh()

        self.wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//h1[normalize-space()='Departments']",
                )
            )
        )

        time.sleep(1)

    def clear_session(self):
        self.driver.execute_script(
            "window.localStorage.clear();"
        )

        self.driver.delete_all_cookies()

    def get_api_token(self, email):
        payload = json.dumps(
            {
                "email": email,
                "password": PASSWORD,
            }
        ).encode("utf-8")

        request = Request(
            f"{BACKEND_API_URL}/auth/login/",
            data=payload,
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(
                request,
                timeout=10,
            ) as response:
                data = json.loads(
                    response.read().decode("utf-8")
                )

                return {
                    "status": response.status,
                    "access": data.get("access"),
                    "body": data,
                }

        except HTTPError as error:
            body = error.read().decode(
                "utf-8"
            )

            return {
                "status": error.code,
                "access": None,
                "body": body,
            }

        except URLError as error:
            return {
                "status": 0,
                "access": None,
                "body": str(error),
            }

    def api_create_department(
        self,
        email,
        department_name,
    ):
        login_response = self.get_api_token(
            email
        )

        if login_response["status"] != 200:
            return login_response

        token = login_response["access"]

        payload = json.dumps(
            {
                "name": department_name,
            }
        ).encode("utf-8")

        request = Request(
            f"{BACKEND_API_URL}/organization/departments/",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="POST",
        )

        try:
            with urlopen(
                request,
                timeout=10,
            ) as response:
                body = response.read().decode(
                    "utf-8"
                )

                return {
                    "status": response.status,
                    "body": body,
                }

        except HTTPError as error:
            body = error.read().decode(
                "utf-8"
            )

            return {
                "status": error.code,
                "body": body,
            }

        except URLError as error:
            return {
                "status": 0,
                "body": str(error),
            }

    def test_st110_permission_enforcement(self):
        self.login(
            NO_PERMISSION_EMAIL
        )

        department_form = self.driver.find_elements(
            By.CSS_SELECTOR,
            "input[placeholder='New department name']",
        )

        self.assertEqual(
            len(department_form),
            0,
            "Department create form should be hidden without permission",
        )

        denied_response = self.api_create_department(
            NO_PERMISSION_EMAIL,
            f"Selenium Unauthorized Department {int(time.time())}",
        )

        self.assertEqual(
            denied_response["status"],
            403,
            f"Expected 403 without permission, got {denied_response}",
        )

        self.clear_session()

        self.login(
            WITH_PERMISSION_EMAIL
        )

        department_input = self.wait.until(
            EC.visibility_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "input[placeholder='New department name']",
                )
            )
        )

        department_input.send_keys(
            DEPARTMENT_NAME
        )

        self.driver.find_element(
            By.XPATH,
            "//button[normalize-space()='Add']",
        ).click()

        self.wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    f"//*[normalize-space()='{DEPARTMENT_NAME}']",
                )
            )
        )

        self.assertIn(
            DEPARTMENT_NAME,
            self.driver.page_source,
        )

        print(
            "ST-110 Selenium Self-Test: PASS"
        )

        print(
            "Without permission: UI hidden and API returned 403"
        )

        print(
            "With permission: UI visible and department creation succeeded"
        )

    def tearDown(self):
        time.sleep(1)

        self.driver.quit()


if __name__ == "__main__":
    unittest.main()