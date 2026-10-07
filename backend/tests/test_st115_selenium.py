import os
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")


class ST115SeleniumTest(unittest.TestCase):

    def setUp(self):
        options = webdriver.ChromeOptions()
        self.driver = webdriver.Chrome(options=options)
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 15)

        self.driver.get(f"{FRONTEND_URL}/login")

        self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "input[type='email']")
            )
        )

        self.driver.find_element(
            By.CSS_SELECTOR, "input[type='email']"
        ).send_keys("ceo@acme.com")

        self.driver.find_element(
            By.CSS_SELECTOR, "input[type='password']"
        ).send_keys(os.environ["TEST_PASSWORD"])

        self.driver.find_element(
            By.CSS_SELECTOR, "button[type='submit']"
        ).click()

        self.wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "[data-testid='sidebar']")
            )
        )

    def tearDown(self):
        self.driver.quit()

    def test_tc24_sidebar_groups_and_active_item(self):
        sidebar = self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[data-testid='sidebar']")
            )
        )

        self.assertTrue(sidebar.is_displayed())

        for group in [
            "organization",
            "workflow",
            "tasks",
            "attendance",
            "finance",
        ]:
            group_button = self.wait.until(
                EC.visibility_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        f"[data-testid='sidebar-group-{group}']",
                    )
                )
            )

            self.assertTrue(group_button.is_displayed())

        active_item = self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[aria-current='page']")
            )
        )

        self.assertTrue(active_item.is_displayed())

    def test_tc25_sidebar_collapse_and_expand(self):
        group_button = self.wait.until(
            EC.element_to_be_clickable(
                (
                    By.CSS_SELECTOR,
                    "[data-testid='sidebar-group-organization']",
                )
            )
        )

        self.assertEqual(
            group_button.get_attribute("aria-expanded"),
            "true",
        )

        group_button.click()

        self.wait.until(
            lambda d: group_button.get_attribute("aria-expanded") == "false"
        )

        self.assertEqual(
            group_button.get_attribute("aria-expanded"),
            "false",
        )

        group_button.click()

        self.wait.until(
            lambda d: group_button.get_attribute("aria-expanded") == "true"
        )

        self.assertEqual(
            group_button.get_attribute("aria-expanded"),
            "true",
        )

    def test_tc26_topbar_notification_and_user_menu(self):
        page_title = self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[data-testid='page-title']")
            )
        )

        self.assertTrue(page_title.text.strip())

        search = self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[data-testid='navbar-search']")
            )
        )

        self.assertTrue(search.is_displayed())

        company = self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[data-testid='navbar-company']")
            )
        )

        self.assertTrue(company.text.strip())

        bell = self.wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "[data-testid='notification-bell']")
            )
        )

        bell.click()

        dropdown = self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[data-testid='notification-dropdown']")
            )
        )

        self.assertIn("Notifications", dropdown.text)
        self.assertIn("You're all caught up", dropdown.text)

        bell.click()

        user_button = self.wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "[data-testid='user-menu-button']")
            )
        )

        user_button.click()

        user_menu = self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[data-testid='user-menu']")
            )
        )

        self.assertIn("ceo@acme.com", user_menu.text)
        self.assertIn("Logout", user_menu.text)


if __name__ == "__main__":
    unittest.main()