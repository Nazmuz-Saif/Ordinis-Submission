import os
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5177")

LOGIN_URL = f"{FRONTEND_URL}/login"
ATTENDANCE_URL = f"{FRONTEND_URL}/attendance"


class ST119AttendanceSeleniumTest(unittest.TestCase):

    def setUp(self):
        options = webdriver.ChromeOptions()
        self.driver = webdriver.Chrome(options=options)
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 15)

    def tearDown(self):
        self.driver.quit()

    def test_st119_attendance_page_loads(self):
        """
        ST-119:
        Attendance page should load successfully after login and expose
        the Check In and Check Out actions.

        This smoke test intentionally does not click Check In/Check Out,
        so running Selenium does not create or modify attendance records.
        """

        # 1. Open login page
        self.driver.get(LOGIN_URL)

        # 2. Wait for login form
        self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//input[@type='email']")
            )
        )

        # 3. Enter CEO credentials
        self.driver.find_element(
            By.XPATH, "//input[@type='email']"
        ).send_keys("ceo@acme.com")

        self.driver.find_element(
            By.XPATH, "//input[@type='password']"
        ).send_keys("TestPass123")

        # 4. Login
        self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[normalize-space()='Login']")
            )
        ).click()

        # 5. Wait until login/navigation completes
        self.wait.until(
            lambda driver: "/login" not in driver.current_url
        )

        # 6. Open Attendance page
        self.driver.get(ATTENDANCE_URL)

        # 7. Verify page heading
        self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//h1[normalize-space()='Attendance']")
            )
        )

        # 8. Verify page description
        description = self.driver.find_elements(
            By.XPATH,
            "//*[contains(normalize-space(), 'Manage and monitor attendance')]"
        )

        self.assertTrue(
            description,
            "Attendance page description was not found."
        )

        # 9. Verify Today's Record section
        self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//h2[normalize-space()=\"Today's Record\"]")
            )
        )

        # 10. Verify Check In button
        check_in_button = self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//button[normalize-space()='Check In']")
            )
        )

        # 11. Verify Check Out button
        check_out_button = self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//button[normalize-space()='Check Out']")
            )
        )

        self.assertTrue(check_in_button.is_enabled())
        self.assertTrue(check_out_button.is_enabled())

        # 12. Verify Current Status is displayed
        status_text = self.driver.find_elements(
            By.XPATH,
            "//*[normalize-space()='Current Status']/following-sibling::*[1]"
        )

        self.assertTrue(
            status_text,
            "Current Status value was not found."
        )

        # 13. Verify page URL
        self.assertEqual(
            self.driver.current_url,
            ATTENDANCE_URL
        )

        print(
            "\nST-119 PASS: Attendance page and "
            "Check In/Check Out actions loaded successfully."
        )


if __name__ == "__main__":
    unittest.main()