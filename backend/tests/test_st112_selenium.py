import os
import time
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

LOGIN_URL = f"{FRONTEND_URL}/login"
CHAINS_URL = f"{FRONTEND_URL}/approvals/chains"

CEO_EMAIL = os.environ.get("TEST_EMAIL", "ceo@acme.com")
CEO_PASSWORD = os.environ.get("TEST_PASSWORD", "TestPass123")

COMPANY_B_EMAIL = os.environ.get("COMPANY_B_EMAIL", "")
COMPANY_B_PASSWORD = os.environ.get("COMPANY_B_PASSWORD", "")


class ST112ApprovalChainSeleniumTest(unittest.TestCase):

    def setUp(self):
        options = webdriver.ChromeOptions()
        self.driver = webdriver.Chrome(options=options)
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 15)

    def tearDown(self):
        self.driver.quit()

    def login(self, email, password):
        self.driver.get(LOGIN_URL)

        self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//input[@type='email']")
            )
        )

        self.driver.find_element(
            By.XPATH, "//input[@type='email']"
        ).send_keys(email)

        self.driver.find_element(
            By.XPATH, "//input[@type='password']"
        ).send_keys(password)

        self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[normalize-space()='Login']")
            )
        ).click()

        self.wait.until(
            lambda driver: "/login" not in driver.current_url
        )

    def open_chains_page(self):
        self.driver.get(CHAINS_URL)

        self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//h1[normalize-space()='Approval Chains']")
            )
        )

    def create_chain(self, chain_name):
        name_input = self.wait.until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    "//input[@placeholder='Chain name (e.g. Leave Approval)']"
                )
            )
        )

        name_input.clear()
        name_input.send_keys(chain_name)

        self.driver.find_element(
            By.XPATH,
            "//button[normalize-space()='New Chain']"
        ).click()

        self.wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    f"//*[normalize-space()='{chain_name}']"
                )
            )
        )

    def get_chain_card(self, chain_name):
        return self.wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    f"//*[normalize-space()='{chain_name}']"
                    "/ancestor::div[contains(@class,'bg-white')][1]"
                )
            )
        )

    def select_first_role(self, card):
        role_select = card.find_element(By.TAG_NAME, "select")

        role_option = role_select.find_elements(
            By.XPATH,
            ".//option[@value and normalize-space(.)!='Approver role...']"
        )[0]

        role_select.click()
        role_option.click()

    def add_step(self, chain_name):
        card = self.get_chain_card(chain_name)

        self.select_first_role(card)

        card.find_element(
            By.XPATH,
            ".//button[normalize-space()='Add Step']"
        ).click()

    def get_step_orders(self, chain_name):
        card = self.get_chain_card(chain_name)

        return [
            element.text.strip()
            for element in card.find_elements(
                By.XPATH,
                ".//ol//li/span[1]"
            )
        ]

    def get_chain_and_role_ids(self, chain_name):
        script = """
        const done = arguments[arguments.length - 1];
        const chainName = arguments[0];
        const token = localStorage.getItem('access_token');

        fetch('http://127.0.0.1:8000/api/v1/approvals/chains/', {
            headers: {
                'Authorization': 'Bearer ' + token
            }
        })
        .then(response => response.json())
        .then(chains => {
            const chain = chains.find(c => c.name === chainName);

            const selects = [...document.querySelectorAll('select')];

            const roleSelect = selects.find(select =>
                [...select.options].some(
                    option =>
                        option.value &&
                        option.textContent.trim() !== 'Approver role...'
                )
            );

            const roleOption = roleSelect
                ? [...roleSelect.options].find(option => option.value)
                : null;

            done({
                chainId: chain ? chain.id : null,
                roleId: roleOption ? roleOption.value : null
            });
        })
        .catch(error => {
            done({
                chainId: null,
                roleId: null,
                error: error.toString()
            });
        });
        """

        return self.driver.execute_async_script(
            script,
            chain_name
        )

    def test_tc24_create_approval_chain_with_three_ordered_steps(self):
        """
        ST-112 TC-24:
        Create an Approval Chain with three ordered steps.
        """

        self.login(CEO_EMAIL, CEO_PASSWORD)
        self.open_chains_page()

        chain_name = f"ST112 Selenium Chain {int(time.time())}"

        self.create_chain(chain_name)

        self.add_step(chain_name)

        self.wait.until(
            lambda driver: len(
                self.get_step_orders(chain_name)
            ) == 1
        )

        self.add_step(chain_name)

        self.wait.until(
            lambda driver: len(
                self.get_step_orders(chain_name)
            ) == 2
        )

        self.add_step(chain_name)

        self.wait.until(
            lambda driver: len(
                self.get_step_orders(chain_name)
            ) == 3
        )

        orders = self.get_step_orders(chain_name)

        self.assertEqual(
            orders,
            ["1", "2", "3"],
            f"Expected [1, 2, 3], but got {orders}"
        )

        print(
            "\nST-112 TC-24 PASS: "
            "Three approval steps were saved in order."
        )

    def test_tc25_no_role_validation(self):
        """
        ST-112 TC-25:
        Add a step without selecting a Role.
        Expect validation error.
        """

        self.login(CEO_EMAIL, CEO_PASSWORD)
        self.open_chains_page()

        chain_name = f"ST112 No Role Chain {int(time.time())}"

        self.create_chain(chain_name)

        card = self.get_chain_card(chain_name)

        card.find_element(
            By.XPATH,
            ".//button[normalize-space()='Add Step']"
        ).click()

        error = self.wait.until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    "//*[contains(normalize-space(), "
                    "'Please choose a role for the new step.')]"
                )
            )
        )

        self.assertIn(
            "Please choose a role for the new step.",
            error.text
        )

        print(
            "\nST-112 TC-25 PASS: "
            "Adding a step without a Role was rejected."
        )

    def test_tc26_company_b_cannot_open_company_a_chain(self):
        """
        ST-112 TC-26:
        Company B opens Company A's approval chain by ID.
        Expect HTTP 404.
        """

        if not COMPANY_B_EMAIL or not COMPANY_B_PASSWORD:
            self.skipTest(
                "COMPANY_B_EMAIL and COMPANY_B_PASSWORD "
                "are not configured."
            )

        self.login(CEO_EMAIL, CEO_PASSWORD)
        self.open_chains_page()

        chain_name = f"ST112 Company A Chain {int(time.time())}"

        self.create_chain(chain_name)

        data = self.get_chain_and_role_ids(chain_name)

        self.assertIsNotNone(data["chainId"])

        company_a_chain_id = data["chainId"]

        self.driver.execute_script(
            """
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            """
        )

        self.login(
            COMPANY_B_EMAIL,
            COMPANY_B_PASSWORD
        )

        result = self.driver.execute_async_script(
            """
            const done = arguments[arguments.length - 1];
            const chainId = arguments[0];
            const token = localStorage.getItem('access_token');

            fetch(
                'http://127.0.0.1:8000/api/v1/approvals/chains/'
                + chainId + '/',
                {
                    headers: {
                        'Authorization': 'Bearer ' + token
                    }
                }
            )
            .then(async response => ({
                status: response.status,
                body: await response.text()
            }))
            .then(done)
            .catch(error => {
                done({
                    status: 0,
                    body: error.toString()
                });
            });
            """,
            company_a_chain_id
        )

        self.assertEqual(
            result["status"],
            404,
            f"Expected HTTP 404, got {result}"
        )

        print(
            "\nST-112 TC-26 PASS: "
            "Company B received HTTP 404 for Company A's chain."
        )


if __name__ == "__main__":
    unittest.main()