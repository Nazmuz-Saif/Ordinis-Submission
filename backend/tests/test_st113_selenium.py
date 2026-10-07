
import os
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5177")

LOGIN_URL = f"{FRONTEND_URL}/login"
APPROVALS_URL = f"{FRONTEND_URL}/approvals/pending"


class ST113ApprovalSeleniumTest(unittest.TestCase):

    def setUp(self):
        options = webdriver.ChromeOptions()
        self.driver = webdriver.Chrome(options=options)
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 15)

    def tearDown(self):
        self.driver.quit()

    def test_st113_approvals_page_loads(self):
        """
        ST-113:
        Approvals page should load successfully after login.
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
        email = self.driver.find_element(
            By.XPATH, "//input[@type='email']"
        )
        password = self.driver.find_element(
            By.XPATH, "//input[@type='password']"
        )

        email.send_keys("ceo@acme.com")
        password.send_keys("TestPass123")

        # 4. Click Login
        login_button = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[normalize-space()='Login']")
            )
        )
        login_button.click()

        # 5. Wait until login/navigation completes
        self.wait.until(
            lambda driver: "/login" not in driver.current_url
        )

        # 6. Open Approvals page
        self.driver.get(APPROVALS_URL)

        # 7. Verify Approvals heading
        self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//h1[normalize-space()='Approvals']")
            )
        )

        # 8. Verify page description
        description = self.driver.find_elements(
            By.XPATH,
            "//*[contains(normalize-space(), "
            "'Requests that need your decision')]"
        )

        self.assertTrue(
            description,
            "Approvals page description was not found."
        )

        # 9. Verify page URL
        self.assertEqual(
            self.driver.current_url,
            APPROVALS_URL
        )

        print("\nST-113 PASS: Approvals page loaded successfully.")


if __name__ == "__main__":
    unittest.main()

