"""
ST-137 Selenium tests: the monthly attendance calendar (Attendance page).

  TC-88  Open the calendar: a colored dot per day and the Present, Absent, On Leave and rate cards match the month.
  TC-89  Go to the previous month and look at a day of approved leave: the month changes and the day shows On Leave.

Needs the demo company (python manage.py seed_demo_data) and both servers running.
TC-89 prepares one working day of the previous month for the demo Employee (no check-in, Approved leave) and puts
everything back afterwards.
Run:  cd backend && python tests/test_st137_selenium.py        (HEADLESS=1 hides the window)
"""
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
import django  # noqa: E402
django.setup()

from selenium_helpers import DEMO_USERS, FRONTEND_URL, clear_session, login_as_demo, make_driver  # noqa: E402

from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402

from attendance.leave_models import LeaveRequest, LeaveType  # noqa: E402
from attendance.models import Attendance  # noqa: E402
from attendance.services import local_today  # noqa: E402
from organization.models import Employee  # noqa: E402


def card_value(driver, testid):
    return driver.find_element(By.CSS_SELECTOR, f"[data-testid='{testid}'] [data-testid='metric-value']").text.strip()


def statuses(driver):
    cells = driver.find_elements(By.CSS_SELECTOR, "[data-testid^='calendar-day-']")
    return [c.get_attribute('data-status') for c in cells], cells


class ST137CalendarSeleniumTest(unittest.TestCase):
    def setUp(self):
        self.driver, self.wait = make_driver()
        self.undo = []

    def tearDown(self):
        for fn in reversed(self.undo):
            fn()
        clear_session(self.driver)
        self.driver.quit()

    def open_calendar(self):
        login_as_demo(self.driver, self.wait, 'Employee')
        self.driver.get(f'{FRONTEND_URL}/attendance')
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='calendar-grid']")))

    def test_tc88_dots_and_cards_match_the_month(self):
        self.open_calendar()
        found, cells = statuses(self.driver)
        self.assertGreaterEqual(len(cells), 28)
        self.assertTrue(self.driver.find_element(By.CSS_SELECTOR, "[data-testid='calendar-month-label']").text.strip())
        self.assertEqual(card_value(self.driver, 'calendar-card-present'), str(found.count('present')))
        self.assertEqual(card_value(self.driver, 'calendar-card-absent'), str(found.count('absent')))
        self.assertEqual(card_value(self.driver, 'calendar-card-on-leave'), str(found.count('on_leave')))
        self.assertIn('%', card_value(self.driver, 'calendar-card-rate'))
        self.assertFalse(self.driver.find_element(By.CSS_SELECTOR, "[data-testid='calendar-next']").is_enabled())   # this month is the last

    def test_tc89_previous_month_shows_a_day_of_approved_leave(self):
        employee = Employee.objects.get(user__email=DEMO_USERS['Employee'])
        today, _zone = local_today(employee.company)
        first_of_this_month = today.replace(day=1)
        last_month_end = first_of_this_month - datetime.timedelta(days=1)
        month_key = f'{last_month_end.year}-{last_month_end.month:02d}'
        working = (
            Attendance.objects.filter(company=employee.company, date__year=last_month_end.year, date__month=last_month_end.month)
            .exclude(employee=employee).values_list('date', flat=True).order_by('date').distinct()
        )
        if not working:
            self.skipTest('The demo company has no attendance in the previous month.')
        day = working[0]
        own = Attendance.objects.filter(employee=employee, date=day).first()
        if own:
            saved = (own.company, own.employee, own.date, own.check_in, own.check_out)
            own.delete()
            self.undo.append(lambda: Attendance.objects.create(company=saved[0], employee=saved[1], date=saved[2], check_in=saved[3], check_out=saved[4]))
        kind, _ = LeaveType.objects.get_or_create(company=employee.company, name='Annual', defaults={'days_allowed_per_year': 20})
        leave = LeaveRequest.objects.create(
            company=employee.company, employee=employee, leave_type=kind, start_date=day, end_date=day, days=1,
            reason='ST-137 selenium', status=LeaveRequest.STATUS_APPROVED,
        )
        self.undo.append(leave.delete)

        self.open_calendar()
        before = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='calendar-month-label']").text
        self.driver.find_element(By.CSS_SELECTOR, "[data-testid='calendar-prev']").click()
        self.wait.until(lambda d: d.find_element(By.CSS_SELECTOR, "[data-testid='calendar-month-label']").text != before)
        cell = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, f"[data-testid='calendar-day-{day.isoformat()}']")))
        self.assertEqual(cell.get_attribute('data-status'), 'on_leave', month_key)


if __name__ == '__main__':
    unittest.main(verbosity=2)
