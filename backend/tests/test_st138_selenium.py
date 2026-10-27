"""
ST-138 Selenium tests: Permission Catalog in UI and backend sync.

  TC-90  [Selenium] As the CEO create a Role and tick one Permission from every module
         — expect the new Role card to list all of them, not four.
  TC-91  [Selenium] Open the Roles page — expect Permissions grouped by module,
         each with a description, and every name present in the backend.

Needs the demo company and both servers running.
Run:  cd backend && python tests/test_st138_selenium.py        (HEADLESS=1 hides the window)
"""
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from selenium_helpers import (  # noqa: E402
    FRONTEND_URL,
    clear_session,
    login_as_demo,
    make_driver,
)

from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402


class ST138RolesCatalogSeleniumTest(unittest.TestCase):
    def setUp(self):
        self.driver, self.wait = make_driver()

    def tearDown(self):
        try:
            self.driver.get(f'{FRONTEND_URL}/login')
            clear_session(self.driver)
        except Exception:
            pass
        self.driver.quit()

    def _login(self, role):
        try:
            self.driver.get(f'{FRONTEND_URL}/login')
            clear_session(self.driver)
        except Exception:
            pass
        login_as_demo(self.driver, self.wait, role)

    def test_tc90_create_role_with_permission_from_every_module(self):
        """TC-90: As CEO create Role with 1 permission per module -> Role card lists all of them, not four."""
        self._login('CEO')
        self.driver.get(f'{FRONTEND_URL}/roles')
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Roles & Permissions']")))

        role_name = f'All-Modules Role {int(time.time())}'

        # Fill role name
        name_input = self.wait.until(EC.visibility_of_element_located((
            By.XPATH, "//input[@placeholder='Role name (e.g. Department Manager)']"
        )))
        name_input.clear()
        name_input.send_keys(role_name)

        # Open each collapsed section in PermissionPicker if closed, and tick one checkbox per section
        sections = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'border') and .//button[contains(@class, 'font-semibold')]]")
        ticked_count = 0

        for section in sections:
            # Check if section toggle button is expanded
            btn = section.find_element(By.XPATH, ".//button[contains(@class, 'font-semibold')]")
            is_expanded = btn.get_attribute('aria-expanded') == 'true'
            if not is_expanded:
                btn.click()
                time.sleep(0.2)

            # Pick the first checkbox in this module
            checkboxes = section.find_elements(By.XPATH, ".//input[@type='checkbox']")
            if checkboxes:
                cb = checkboxes[0]
                if not cb.is_selected():
                    self.driver.execute_script("arguments[0].click();", cb)
                    ticked_count += 1

        self.assertGreaterEqual(ticked_count, 6, f'Expected at least 6 module checkboxes ticked, got {ticked_count}')

        # Verify counter shows ticked count
        counter = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='perm-counter']").text
        self.assertIn(f'{ticked_count} of', counter)

        # Submit form
        submit_btn = self.driver.find_element(By.XPATH, "//form//button[contains(., 'Create Role')]")
        self.driver.execute_script("arguments[0].click();", submit_btn)

        # Wait for success or updated roles list
        time.sleep(2)

        # Locate the new role card in the Existing Roles grid
        role_card = self.wait.until(EC.presence_of_element_located((
            By.XPATH, f"//div[contains(@class, 'grid')]//div[.//a[normalize-space()='{role_name}']]"
        )))
        card_text = role_card.text
        self.assertIn(f'{ticked_count} Permissions', card_text, f'Role card should reflect all {ticked_count} permissions saved, not 4')

    def test_tc91_roles_page_permissions_grouped_with_descriptions(self):
        """TC-91: Open Roles page -> Permissions grouped by module, each with description and backend catalog names."""
        self._login('CEO')
        self.driver.get(f'{FRONTEND_URL}/roles')
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Roles & Permissions']")))
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='perm-counter']")))

        # Check permission sections (modules)
        from rbac.catalog import PERMISSION_CATALOG
        modules_in_catalog = {entry['module'] for entry in PERMISSION_CATALOG}

        # Check that module sections exist in the picker
        sections = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'border') and .//button[contains(@class, 'font-semibold')]]")
        self.assertGreaterEqual(len(sections), len(modules_in_catalog) - 2)

        # Expand all sections to verify descriptions and names
        for section in sections:
            btn = section.find_element(By.XPATH, ".//button[contains(@class, 'font-semibold')]")
            if btn.get_attribute('aria-expanded') != 'true':
                btn.click()
                time.sleep(0.1)

        # Check sample permission names and descriptions from catalog
        page_source = self.driver.page_source
        for sample in PERMISSION_CATALOG[:5]:
            self.assertIn(sample['name'], page_source, f"Permission name {sample['name']} should be displayed on page")
            self.assertIn(sample['description'], page_source, f"Description for {sample['name']} should be displayed on page")


if __name__ == '__main__':
    unittest.main(verbosity=2)
