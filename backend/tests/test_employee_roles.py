import os
import sys
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def test_employee_role_page():
    email = os.getenv("TEST_EMAIL")
    password = os.getenv("TEST_PASSWORD")

    assert email, "TEST_EMAIL environment variable is not set"
    assert password, "TEST_PASSWORD environment variable is not set"

    driver = webdriver.Chrome()
    wait = WebDriverWait(driver, 15)

    try:
        # 1. Open Login page
        driver.get("http://localhost:5173/login")

        # 2. Find login inputs
        inputs = wait.until(
            lambda d: d.find_elements(By.TAG_NAME, "input")
        )

        assert len(inputs) >= 2, "Login inputs not found"

        # 3. Login
        inputs[0].send_keys(email)
        inputs[1].send_keys(password)

        driver.find_element(
            By.XPATH, "//button[contains(normalize-space(), 'Login')]"
        ).click()

        # 4. Wait until login completes
        wait.until(lambda d: "/login" not in d.current_url)

        # 5. Open Employee Roles page
        driver.get("http://localhost:5173/roles/employee-roles")

        # 6. Verify Employee Roles heading
        heading = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//*[contains(normalize-space(), 'Employee Roles')]"
                )
            )
        )

        assert heading.is_displayed()

        # 7. Verify Employee dropdown
        employee_select = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//select[option[contains(normalize-space(), 'Select Employee')]]"
                )
            )
        )

        assert employee_select.is_displayed()

        # 8. Verify Role dropdown
        role_select = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//select[option[contains(normalize-space(), 'Select Role')]]"
                )
            )
        )

        assert role_select.is_displayed()

        # 9. Verify Assign Role button
        assign_button = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//button[contains(normalize-space(), 'Assign Role')]"
                )
            )
        )

        assert assign_button.is_displayed()

        # 10. Verify Assigned Roles section
        assigned_roles = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//*[contains(normalize-space(), 'Assigned Roles')]"
                )
            )
        )

        assert assigned_roles.is_displayed()

        print("\n================ SELF-TEST RESULT ================")
        print("Login: PASS")
        print("Employee Roles page: PASS")
        print("Employee dropdown: PASS")
        print("Role dropdown: PASS")
        print("Assign Role button: PASS")
        print("Assigned Roles section: PASS")
        print("===================================================")

    finally:
        driver.quit()