import datetime
import os
import sys
import unittest

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(TESTS_DIR)

sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, TESTS_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django

django.setup()

from selenium_helpers import (
    DEMO_USERS,
    FRONTEND_URL,
    clear_session,
    login_as_demo,
    make_driver,
)
from attendance.leave_models import LeaveRequest, LeaveType
from attendance.models import Attendance
from attendance.services import local_today
from organization.models import Employee


def card_value(driver, testid):
    return driver.find_element(
        By.CSS_SELECTOR,
        f"[data-testid='{testid}'] [data-testid='metric-value']",
    ).text.strip()


def statuses(driver):
    cells = driver.find_elements(
        By.CSS_SELECTOR, "[data-testid^='calendar-day-']"
    )
    return [cell.get_attribute("data-status") for cell in cells], cells


class ST137CalendarSeleniumTest(unittest.TestCase):
    def setUp(self):
        self.driver, self.wait = make_driver()
        self.undo = []

    def tearDown(self):
        try:
            for fn in reversed(self.undo):
                try:
                    fn()
                except Exception as exc:
                    print(f"Cleanup warning: {exc}")
        finally:
            try:
                clear_session(self.driver)
            finally:
                self.driver.quit()

    def open_calendar(self):
        login_as_demo(self.driver, self.wait, "Employee")
        self.driver.get(f"{FRONTEND_URL}/attendance")
        self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[data-testid='calendar-grid']")
            )
        )

    def test_tc88_dots_and_cards_match_the_month(self):
        self.open_calendar()
        found, cells = statuses(self.driver)

        self.assertGreaterEqual(len(cells), 28)
        self.assertTrue(
            self.driver.find_element(
                By.CSS_SELECTOR, "[data-testid='calendar-month-label']"
            ).text.strip()
        )

        self.assertEqual(
            card_value(self.driver, "calendar-card-present"),
            str(found.count("present")),
        )
        self.assertEqual(
            card_value(self.driver, "calendar-card-absent"),
            str(found.count("absent")),
        )
        self.assertEqual(
            card_value(self.driver, "calendar-card-on-leave"),
            str(found.count("on_leave")),
        )
        self.assertIn("%", card_value(self.driver, "calendar-card-rate"))

        self.assertFalse(
            self.driver.find_element(
                By.CSS_SELECTOR, "[data-testid='calendar-next']"
            ).is_enabled()
        )

    def test_tc89_previous_month_shows_a_day_of_approved_leave(self):
        employee = Employee.objects.get(
            user__email=DEMO_USERS["Employee"]
        )

        today, _zone = local_today(employee.company)
        first_of_this_month = today.replace(day=1)
        last_month_end = first_of_this_month - datetime.timedelta(days=1)

        month_key = (
            f"{last_month_end.year}-{last_month_end.month:02d}"
        )

        working = list(
            Attendance.objects.filter(
                company=employee.company,
                date__year=last_month_end.year,
                date__month=last_month_end.month,
            )
            .exclude(employee=employee)
            .values_list("date", flat=True)
            .order_by("date")
            .distinct()
        )

        if not working:
            self.skipTest(
                "The demo company has no attendance in the previous month."
            )

        day = working[0]
        own = Attendance.objects.filter(
            employee=employee, date=day
        ).first()

        if own:
            saved = (
                own.company,
                own.employee,
                own.date,
                own.check_in,
                own.check_out,
            )
            own.delete()

            self.undo.append(
                lambda saved=saved: Attendance.objects.create(
                    company=saved[0],
                    employee=saved[1],
                    date=saved[2],
                    check_in=saved[3],
                    check_out=saved[4],
                )
            )

        leave_type, _ = LeaveType.objects.get_or_create(
            company=employee.company,
            name="Annual",
            defaults={"days_allowed_per_year": 20},
        )

        leave = LeaveRequest.objects.create(
            company=employee.company,
            employee=employee,
            leave_type=leave_type,
            start_date=day,
            end_date=day,
            days=1,
            reason="ST-137 selenium",
            status=LeaveRequest.STATUS_APPROVED,
        )
        self.undo.append(leave.delete)

        self.open_calendar()

        month_label = self.driver.find_element(
            By.CSS_SELECTOR, "[data-testid='calendar-month-label']"
        )
        before = month_label.text.strip()

        previous_button = self.driver.find_element(
            By.CSS_SELECTOR, "[data-testid='calendar-prev']"
        )
        self.wait.until(lambda d: previous_button.is_enabled())
        previous_button.click()

        try:
            self.wait.until(
                lambda d: d.find_element(
                    By.CSS_SELECTOR,
                    "[data-testid='calendar-month-label']",
                ).text.strip() != before
            )
        except TimeoutException:
            after = self.driver.find_element(
                By.CSS_SELECTOR,
                "[data-testid='calendar-month-label']",
            ).text.strip()

            self.fail(
                f"Calendar month did not change after clicking Previous. "
                f"Before: {before!r}, After: {after!r}"
            )

        cell = self.wait.until(
            EC.visibility_of_element_located(
                (
                    By.CSS_SELECTOR,
                    f"[data-testid='calendar-day-{day.isoformat()}']",
                )
            )
        )

        self.assertEqual(
            cell.get_attribute("data-status"),
            "on_leave",
            month_key,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)