"""
ST-129 Selenium Tests (TC-71, TC-72, TC-73): Leave Approval Chain, Final Approval & Rejection
File: test_st129_selenium.py

Test Cases:
  TC-71: [Selenium] Apply for leave as an Employee when the company has a leave Approval Chain —
         expect the request Pending and visible in the approver's Pending Approvals page and Action Inbox
  TC-72: [Selenium] As the approver approve the last step —
         expect the leave Approved, a Notification for the applicant, and the days used in the leave balance
  TC-73: [Selenium] As the approver reject a leave request with a comment —
         expect it Rejected, the days back in the balance, and the comment shown to the applicant

Assignee:
  Md. Tahsin Rahman Khan
"""
import os
import sys
import time
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _path in (BASE_DIR, os.path.join(BASE_DIR, 'apps')):
    if _path not in sys.path:
        sys.path.insert(0, _path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
import django
django.setup()

from selenium_helpers import (  # noqa: E402
    FRONTEND_URL,
    clear_session,
    login_as_demo,
    make_driver,
)

from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402
from selenium.webdriver.support.ui import Select  # noqa: E402


class ST129LeaveApprovalSeleniumTest(unittest.TestCase):
    def _login_as(self, role):
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
        self.driver, self.wait = make_driver()
        login_as_demo(self.driver, self.wait, role)

    def setUp(self):
        from attendance.leave_models import LeaveRequest
        LeaveRequest.objects.filter(reason__startswith='ST129').delete()
        self.driver, self.wait = make_driver()

    def tearDown(self):
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
        from attendance.leave_models import LeaveRequest
        LeaveRequest.objects.filter(reason__startswith='ST129').delete()

    def _apply_leave(self, start_date, end_date, reason, leave_type_name='Casual Leave'):
        self.driver.get(f'{FRONTEND_URL}/attendance/leave')
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='leave-form']")))

        selector = "[data-testid='leave-type']"
        self.wait.until(
            lambda d: any(
                opt.get_attribute('value') and (leave_type_name.lower() in opt.text.lower())
                for opt in Select(d.find_element(By.CSS_SELECTOR, selector)).options
            )
        )
        select_el = self.driver.find_element(By.CSS_SELECTOR, selector)
        select = Select(select_el)
        target = next(o for o in select.options if leave_type_name.lower() in o.text.lower())
        target_value = target.get_attribute('value')

        self.driver.execute_script(
            """
            const s = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
            s.call(arguments[0], arguments[1]);
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """,
            select_el,
            target_value,
        )
        select.select_by_value(target_value)

        start_el = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='leave-start']")
        end_el = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='leave-end']")
        self.driver.execute_script(
            """
            const set = (el, val) => {
                el.removeAttribute('min');
                const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                s.call(el, val);
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
            };
            set(arguments[0], arguments[1]);
            set(arguments[2], arguments[3]);
            """,
            start_el,
            start_date.isoformat(),
            end_el,
            end_date.isoformat(),
        )

        reason_el = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='leave-reason']")
        self.driver.execute_script(
            """
            const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            s.call(arguments[0], arguments[1]);
            arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
            arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
            """,
            reason_el,
            reason,
        )

        time.sleep(0.5)

        form = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='leave-form']")
        self.driver.execute_script(
            """
            arguments[0].dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
            """,
            form,
        )

        # Wait for the confirmation message
        try:
            self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='leave-message']")))
        except Exception:
            errs = [e.text for e in self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='leave-error'], [role='alert']")]
            print(f"FAILED TO SUBMIT. Error elements: {errs}")
            print(f"PAGE BODY TEXT:\n{self.driver.find_element(By.TAG_NAME, 'body').text}")
            raise

    def _get_balance_remaining(self, leave_type_name='Casual Leave'):
        self.driver.get(f'{FRONTEND_URL}/attendance/leave')
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='leave-balance-card']")))
        cards = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='leave-balance-card']")
        for card in cards:
            if leave_type_name.lower() in card.text.lower():
                rem_el = card.find_element(By.CSS_SELECTOR, "[data-testid='balance-remaining']")
                return int(rem_el.text.strip())
        return None

    def test_tc71_leave_approval_chain_pending_in_approver_views(self):
        """TC-71: Apply for leave as an Employee when company has leave Approval Chain -> Pending in Pending Approvals & Action Inbox"""
        ts = int(time.time())
        reason = f'ST129 TC71 Family Event {ts}'
        start = date.today() + timedelta(days=60)
        end = date.today() + timedelta(days=61)

        # 1. Apply as Employee
        self._login_as('Employee')
        self._apply_leave(start, end, reason, leave_type_name='Casual Leave')

        # Verify Pending status on employee's leave table
        self.wait.until(
            EC.presence_of_element_located((
                By.XPATH,
                f"//table[@data-testid='leave-table']//tr[contains(., '{reason}')]",
            ))
        )
        row = self.driver.find_element(
            By.XPATH, f"//table[@data-testid='leave-table']//tr[contains(., '{reason}')]"
        )
        self.assertIn('Pending', row.text)
        self.assertTrue(
            'waiting for Manager' in row.text or 'Step 1' in row.text,
            f'Expected waiting for Manager in row: {row.text}',
        )

        # 2. Log in as Approver (Manager)
        self._login_as('Manager')

        # Check Pending Approvals page
        self.driver.get(f'{FRONTEND_URL}/approvals/pending')
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='approval-item']")))
        items = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='approval-item']")
        matching = [item for item in items if reason in item.text]
        self.assertTrue(
            len(matching) > 0,
            f"Expected request with reason '{reason}' in Pending Approvals list",
        )
        self.assertIn('pending', matching[0].text.lower())

        # Check Action Inbox
        self.driver.get(f'{FRONTEND_URL}/inbox')
        approval_inbox_item = self.wait.until(
            EC.visibility_of_element_located((
                By.XPATH,
                "//*[contains(text(), 'Approval needed') or contains(text(), 'Approvals waiting')]",
            ))
        )
        self.assertTrue(approval_inbox_item.is_displayed())

    def test_tc72_approver_approves_last_step(self):
        """TC-72: Approver approves last step -> Leave Approved, Notification sent, days deducted from balance"""
        ts = int(time.time())
        reason = f'ST129 TC72 Trip {ts}'
        start = date.today() + timedelta(days=25)
        end = date.today() + timedelta(days=25)  # 1 day in current year 2026

        # 1. Check initial balance as Employee and apply
        self._login_as('Employee')
        initial_remaining = self._get_balance_remaining('Casual Leave')
        self.assertIsNotNone(initial_remaining, 'Could not read initial Casual Leave balance')

        self._apply_leave(start, end, reason, leave_type_name='Casual Leave')

        # 2. Step 1 Approver (Manager) approves
        self._login_as('Manager')
        self.driver.get(f'{FRONTEND_URL}/approvals/pending')
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='approval-item']")))

        item = self.wait.until(
            EC.presence_of_element_located((
                By.XPATH,
                f"//div[@data-testid='approval-item'][contains(., '{reason}')]",
            ))
        )
        approve_btn = item.find_element(By.XPATH, ".//button[contains(., 'Approve')]")
        approve_btn.click()

        dialog_submit = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//form//button[@type='submit'][contains(., 'Approve')]"))
        )
        dialog_submit.click()
        time.sleep(1.5)

        # 3. Step 2 (Last Step) Approver (HR) approves
        self._login_as('HR')
        self.driver.get(f'{FRONTEND_URL}/approvals/pending')
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='approval-item']")))

        item = self.wait.until(
            EC.presence_of_element_located((
                By.XPATH,
                f"//div[@data-testid='approval-item'][contains(., '{reason}')]",
            ))
        )
        approve_btn = item.find_element(By.XPATH, ".//button[contains(., 'Approve')]")
        approve_btn.click()

        dialog_submit = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//form//button[@type='submit'][contains(., 'Approve')]"))
        )
        dialog_submit.click()
        time.sleep(1.5)

        # 4. Verify Employee sees Approved, reduced balance, and notification
        self._login_as('Employee')

        self.driver.get(f'{FRONTEND_URL}/attendance/leave')
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='leave-table']")))

        row = self.wait.until(
            EC.presence_of_element_located((
                By.XPATH,
                f"//table[@data-testid='leave-table']//tr[contains(., '{reason}')]",
            ))
        )
        self.assertIn('Approved', row.text)

        new_remaining = self._get_balance_remaining('Casual Leave')
        self.assertEqual(new_remaining, initial_remaining - 1, 'Leave days should be deducted from balance')

        # Inbox check for notification
        self.driver.get(f'{FRONTEND_URL}/inbox')
        self.wait.until(
            EC.presence_of_element_located((
                By.XPATH,
                "//li[@data-testid='inbox-item'][.//*[contains(text(), 'Leave Approval: approved') or contains(text(), 'approved')]]"
            ))
        )
        inbox_content = self.driver.find_element(By.TAG_NAME, 'main').text.lower()
        self.assertTrue(
            'approved' in inbox_content or 'leave' in inbox_content,
            f'Expected notification about approved leave in inbox: {inbox_content}',
        )

    def test_tc73_approver_rejects_with_comment(self):
        """TC-73: Approver rejects leave request with comment -> Rejected, days restored to balance, comment shown to applicant"""
        ts = int(time.time())
        reason = f'ST129 TC73 Medical {ts}'
        rejection_comment = f'Peak project release week, please reschedule ({ts})'
        start = date.today() + timedelta(days=35)
        end = date.today() + timedelta(days=35)  # 1 day in current year 2026

        # 1. Note initial balance and apply as Employee
        self._login_as('Employee')
        initial_remaining = self._get_balance_remaining('Casual Leave')
        self._apply_leave(start, end, reason, leave_type_name='Casual Leave')

        # 2. Manager rejects with comment
        self._login_as('Manager')
        self.driver.get(f'{FRONTEND_URL}/approvals/pending')
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='approval-item']")))

        item = self.wait.until(
            EC.presence_of_element_located((
                By.XPATH,
                f"//div[@data-testid='approval-item'][contains(., '{reason}')]",
            ))
        )
        reject_btn = item.find_element(By.XPATH, ".//button[contains(., 'Reject')]")
        reject_btn.click()

        # Fill rejection comment
        comment_area = self.wait.until(EC.visibility_of_element_located((By.XPATH, "//form//textarea")))
        comment_area.clear()
        comment_area.send_keys(rejection_comment)

        reject_submit = self.driver.find_element(By.XPATH, "//form//button[@type='submit'][contains(., 'Reject')]")
        reject_submit.click()
        time.sleep(1.5)

        # 3. Employee checks status Rejected, days restored, and comment visible
        self._login_as('Employee')
        self.driver.get(f'{FRONTEND_URL}/attendance/leave')
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='leave-table']")))

        row = self.wait.until(
            EC.presence_of_element_located((
                By.XPATH,
                f"//table[@data-testid='leave-table']//tr[contains(., '{reason}')]",
            ))
        )
        self.assertIn('Rejected', row.text)
        self.assertIn(rejection_comment, row.text, 'Rejection comment should be displayed in approval progress')

        current_remaining = self._get_balance_remaining('Casual Leave')
        self.assertEqual(current_remaining, initial_remaining, 'Days should be returned to balance after rejection')


if __name__ == '__main__':
    unittest.main(verbosity=2)
