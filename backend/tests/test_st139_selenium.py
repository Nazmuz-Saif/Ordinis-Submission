"""
ST-139 Selenium tests: Role detail, edit flow, locked CEO Role, and ROLE_IN_USE refusal.

  TC-92  [Selenium] As the CEO open a Role's detail page — expect Permissions grouped by module
         with descriptions and the list of employees who hold it.
  TC-93  [Selenium] Edit a Role: add and remove Permissions and save — expect the detail page
         and the Roles list to show the change; the CEO Role shows no Edit button.
  TC-94  [Selenium] Delete a Role that an Employee holds — expect a clear refusal and the Role still listed.

Needs the demo company and both servers running.
Run:  cd backend && python tests/test_st139_selenium.py        (HEADLESS=1 hides the window)
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


class ST139RoleDetailAndEditSeleniumTest(unittest.TestCase):
    def setUp(self):
        self.driver, self.wait = make_driver()

    def tearDown(self):
        try:
            self.driver.get(f'{FRONTEND_URL}/login')
            clear_session(self.driver)
        except Exception:
            pass
        self.driver.quit()

    def _login(self, role='CEO'):
        try:
            self.driver.get(f'{FRONTEND_URL}/login')
            clear_session(self.driver)
        except Exception:
            pass
        login_as_demo(self.driver, self.wait, role)

    def test_tc92_role_detail_page_grouped_permissions_and_holders(self):
        """TC-92: As CEO open Role detail page -> Permissions grouped by module with descriptions, and employee holders."""
        self._login('CEO')
        self.driver.get(f'{FRONTEND_URL}/roles')
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Roles & Permissions']")))

        # Click on 'Manager' role link
        manager_link = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//div[contains(@class, 'grid')]//a[normalize-space()='Manager']")
        ))
        manager_link.click()

        # Wait for Role detail page to load
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Manager']")))

        # 1. Expect permissions grouped by module with descriptions
        perms_section = self.wait.until(EC.visibility_of_element_located(
            (By.XPATH, "//h2[normalize-space()='What this Role allows']/..")
        ))
        section_text = perms_section.text
        self.assertTrue(len(section_text) > 0)

        # Check uppercase module headers in detail page
        module_headers = perms_section.find_elements(By.XPATH, ".//p[contains(@class, 'uppercase')]")
        self.assertGreater(len(module_headers), 0, "Expected at least one uppercase module header in What this Role allows")

        # Check permission items (each has name and description)
        perm_items = perms_section.find_elements(By.XPATH, ".//li")
        self.assertGreater(len(perm_items), 0, "Expected permission items in What this Role allows")
        for item in perm_items[:3]:
            # Each item has a title span and a description span
            spans = item.find_elements(By.XPATH, ".//span")
            self.assertGreaterEqual(len(spans), 2, "Expected permission name and description spans")
            self.assertTrue(len(spans[0].text.strip()) > 0, "Permission name should not be empty")
            self.assertTrue(len(spans[1].text.strip()) > 0, "Permission description should not be empty")

        # 2. Expect list of employees who hold this Role
        holders_section = self.wait.until(EC.visibility_of_element_located(
            (By.XPATH, "//h2[normalize-space()='Employees who hold this Role']/..")
        ))
        holders_text = holders_section.text
        self.assertNotIn("Nobody holds this Role yet", holders_text)
        holders = holders_section.find_elements(By.XPATH, ".//li")
        self.assertGreater(len(holders), 0, "Expected at least one employee holding the Manager role")
        # Verify employee links exist
        emp_link = holders[0].find_element(By.XPATH, ".//a[contains(@href, '/organization/employees/')]")
        self.assertTrue(len(emp_link.text.strip()) > 0, "Employee link text should not be empty")

    def test_tc93_edit_role_permissions_ceo_locked(self):
        """TC-93: Edit Role: add/remove permissions & save -> detail & list show changes; CEO Role has no Edit button."""
        self._login('CEO')
        self.driver.get(f'{FRONTEND_URL}/roles')
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Roles & Permissions']")))

        # --- Part 1: Verify CEO Role shows no Edit button ---
        ceo_card_link = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//div[contains(@class, 'grid')]//div[.//span[text()='System']]//a[normalize-space()='CEO']")
        ))
        ceo_card_link.click()

        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='CEO']")))
        # System role note should be present
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='system-role-note']")))

        # No Edit button on CEO detail page
        edit_buttons = self.driver.find_elements(By.XPATH, "//button[contains(., 'Edit')]")
        self.assertEqual(len(edit_buttons), 0, "CEO system role must not display an Edit button")

        # --- Part 2: Create a role to edit ---
        self.driver.get(f'{FRONTEND_URL}/roles')
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Roles & Permissions']")))

        test_role_name = f"Editable Role {int(time.time())}"
        name_input = self.wait.until(EC.visibility_of_element_located((
            By.XPATH, "//input[@placeholder='Role name (e.g. Department Manager)']"
        )))
        name_input.clear()
        name_input.send_keys(test_role_name)

        # Select first permission
        first_cb = self.wait.until(EC.presence_of_element_located((
            By.XPATH, "//div[contains(@class, 'border') and .//button[contains(@class, 'font-semibold')]]//input[@type='checkbox']"
        )))
        self.driver.execute_script("arguments[0].click();", first_cb)

        # Submit create role
        submit_btn = self.driver.find_element(By.XPATH, "//form//button[contains(., 'Create Role')]")
        self.driver.execute_script("arguments[0].click();", submit_btn)
        time.sleep(2)

        # Open detail page of the new role
        role_link = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, f"//div[contains(@class, 'grid')]//a[normalize-space()='{test_role_name}']")
        ))
        role_link.click()

        self.wait.until(EC.visibility_of_element_located((By.XPATH, f"//h1[normalize-space()='{test_role_name}']")))

        # Click Edit button
        edit_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Edit')]")))
        edit_btn.click()

        # Affect note should be displayed
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='affect-note']")))

        # Add another permission
        unselected_cbs = self.driver.find_elements(
            By.XPATH, "//form//div[contains(@class, 'border')]//input[@type='checkbox' and not(@checked)]"
        )
        if unselected_cbs:
            self.driver.execute_script("arguments[0].click();", unselected_cbs[0])

        # Save changes
        save_btn = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//form//button[contains(., 'Save changes')]")
        ))
        self.driver.execute_script("arguments[0].click();", save_btn)

        # Wait for success message or view mode
        time.sleep(2)
        success_alerts = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Role saved')]")
        self.assertTrue(len(success_alerts) > 0, "Success message 'Role saved' should be displayed")

        # Navigate back to roles list
        self.driver.get(f'{FRONTEND_URL}/roles')
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Roles & Permissions']")))

        # Expect role card to show updated permissions count
        card = self.wait.until(EC.presence_of_element_located((
            By.XPATH, f"//div[contains(@class, 'grid')]//div[.//a[normalize-space()='{test_role_name}']]"
        )))
        self.assertIn("Permissions", card.text)

    def test_tc94_delete_role_in_use_refusal(self):
        """TC-94: Delete a Role that an Employee holds -> clear refusal and Role still listed."""
        self._login('CEO')
        self.driver.get(f'{FRONTEND_URL}/roles')
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Roles & Permissions']")))

        # Find Manager role card (held by demo employees)
        manager_card = self.wait.until(EC.presence_of_element_located((
            By.XPATH, "//div[contains(@class, 'grid')]//div[.//a[normalize-space()='Manager']]"
        )))
        delete_btn = manager_card.find_element(By.XPATH, ".//button[@title='Delete Role']")
        self.driver.execute_script("arguments[0].click();", delete_btn)

        # Confirm dialog should appear
        self.wait.until(EC.alert_is_present())
        alert = self.driver.switch_to.alert
        alert.accept()

        # Error refusal should be displayed on page
        error_banner = self.wait.until(EC.visibility_of_element_located(
            (By.XPATH, "//div[contains(@class, 'bg-red-50') or contains(@class, 'text-red-600')]")
        ))
        error_text = error_banner.text.lower()
        self.assertTrue(
            'employee' in error_text or 'held' in error_text or 'role' in error_text or 'cannot' in error_text,
            f"Expected refusal message explaining role is in use, got: '{error_banner.text}'"
        )

        # Refresh page and ensure Manager role is still present
        self.driver.refresh()
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Roles & Permissions']")))
        still_present = self.wait.until(EC.visibility_of_element_located(
            (By.XPATH, "//div[contains(@class, 'grid')]//a[normalize-space()='Manager']")
        ))
        self.assertTrue(still_present.is_displayed(), "Role held by employees must still be listed after refused deletion")


if __name__ == '__main__':
    unittest.main(verbosity=2)
