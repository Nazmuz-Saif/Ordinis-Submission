import os
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
UI_KIT_URL = f"{FRONTEND_URL}/dev/ui-kit"


class ST114UiKitSeleniumTest(unittest.TestCase):

    def setUp(self):
        self.driver = webdriver.Chrome(options=webdriver.ChromeOptions())
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 15)
        self.driver.get(UI_KIT_URL)
        # page load hoyeche kina: <h1>UI Kit</h1> asa porjonto wait
        self.wait.until(
            EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='UI Kit']"))
        )

    def tearDown(self):
        self.driver.quit()

    # --- helper ---------------------------------------------------------------
    def pill(self, variant, text):
        xpath = f"//span[@data-testid='status-pill-{variant}'][normalize-space()='{text}']"
        return self.wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))

    # --- TC-30 ----------------------------------------------------------------
    def test_tc30_status_pills_have_color_and_text(self):
        """Success, Warning, Failed pill dekhabe; protiti te color + text (+ icon)."""
        for variant, text in (("success", "Success"), ("warning", "Warning"), ("failed", "Failed")):
            pill = self.pill(variant, text)

            # 1) text ase
            self.assertEqual(pill.text.strip(), text)

            # 2) color ase (background transparent na)
            background = pill.value_of_css_property("background-color")
            self.assertNotIn(background, ("rgba(0, 0, 0, 0)", "transparent"),
                             f"{text} pill e background color nai")

            # 3) text color ar background color alada
            self.assertNotEqual(pill.value_of_css_property("color"), background)

            # 4) icon ase, mane status shudhu color diye bojhano hoy nai
            self.assertTrue(pill.find_elements(By.TAG_NAME, "svg"), f"{text} pill e icon nai")

    # --- TC-31 ----------------------------------------------------------------
    def test_tc31_metric_card_and_empty_state_action(self):
        """MetricCard e value + delta thakbe; EmptyState er button click kora jabe."""
        # --- MetricCard ---
        card = self.wait.until(EC.visibility_of_element_located(
            (By.XPATH, "//div[@data-testid='metric-card'][.//p[normalize-space()='Total Employees']]")
        ))
        value = card.find_element(By.CSS_SELECTOR, "[data-testid='metric-value']")
        delta = card.find_element(By.CSS_SELECTOR, "[data-testid='metric-delta']")
        self.assertEqual(value.text.strip(), "124")
        self.assertIn("+8 this month", delta.text)

        # --- EmptyState ---
        counter = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='empty-state-clicks']")
        self.assertIn("Action clicked: 0", counter.text)

        button = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='empty-state-action']"))
        )
        self.assertEqual(button.text.strip(), "Add Employee")
        button.click()

        # click er por counter 0 theke 1 hobe
        self.wait.until(EC.text_to_be_present_in_element(
            (By.CSS_SELECTOR, "[data-testid='empty-state-clicks']"), "Action clicked: 1"
        ))


if __name__ == "__main__":
    unittest.main()