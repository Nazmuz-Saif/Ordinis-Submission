import datetime
from unittest import mock

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from attendance import services
from attendance.leave_models import LeaveRequest, LeaveType
from attendance.models import Attendance
from core.test_utils import add_employee, login_as, register_company
from organization.models import Employee
from tenants.models import Company

URL = '/api/v1/attendance/attendance/calendar/'
D = datetime.date
TODAY = D(2026, 10, 19)       # a Monday; every test fixes "today" so nothing depends on the real date


class Base(TestCase):
    def setUp(self):
        patcher = mock.patch('attendance.services.local_today', return_value=(TODAY, None))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.company = Company.objects.get(subdomain='acme')
        add_employee(self.ceo, 'emp@acme.com', 'E-001')
        add_employee(self.ceo, 'other@acme.com', 'E-002')
        self.boss = Employee.objects.get(user__email='ceo@acme.com')
        self.me = Employee.objects.get(user__email='emp@acme.com')
        self.other = Employee.objects.get(user__email='other@acme.com')
        self.client_me = login_as('emp@acme.com')

    def present(self, employee, *days):
        for day in days:
            Attendance.objects.create(company=employee.company, employee=employee, date=day, check_in=timezone.now())

    def leave(self, first, last, status=LeaveRequest.STATUS_APPROVED, employee=None):
        kind, _ = LeaveType.objects.get_or_create(company=self.company, name='Annual', defaults={'days_allowed_per_year': 20})
        return LeaveRequest.objects.create(
            company=self.company, employee=employee or self.me, leave_type=kind, start_date=first, end_date=last,
            days=(last - first).days + 1, reason='t', status=status,
        )

    def month(self, month=None, employee=None):
        return services.month_calendar(employee or self.me, month)

    def status(self, data, day):
        return next(d['status'] for d in data['days'] if d['date'] == day)


class StatusTests(Base):
    def setUp(self):
        super().setUp()
        # The company worked Mon 5, Tue 6, Wed 7 October (the others checked in); Thursday 8 and Friday 9 nobody did.
        self.present(self.other, D(2026, 10, 5), D(2026, 10, 6), D(2026, 10, 7))

    def test_present_on_leave_and_absent(self):
        self.present(self.me, D(2026, 10, 5))
        self.leave(D(2026, 10, 6), D(2026, 10, 6))
        data = self.month('2026-10')
        self.assertEqual(self.status(data, '2026-10-05'), 'present')
        self.assertEqual(self.status(data, '2026-10-06'), 'on_leave')
        self.assertEqual(self.status(data, '2026-10-07'), 'absent')
        self.assertEqual(data['summary'], {'present': 1, 'absent': 1, 'on_leave': 1, 'attendance_rate': 50.0})

    def test_a_day_nobody_worked_has_no_status_even_on_approved_leave(self):
        self.leave(D(2026, 10, 8), D(2026, 10, 9))
        data = self.month('2026-10')
        self.assertIsNone(self.status(data, '2026-10-08'))
        self.assertIsNone(self.status(data, '2026-10-10'))          # a Saturday
        self.assertEqual(data['summary']['on_leave'], 0)

    def test_future_days_have_no_status_even_with_approved_leave(self):
        self.leave(D(2026, 10, 21), D(2026, 10, 22))
        data = self.month('2026-10')
        self.assertIsNone(self.status(data, '2026-10-21'))
        self.assertIsNone(self.status(data, '2026-10-31'))
        self.assertEqual(data['summary']['on_leave'], 0)

    def test_pending_rejected_and_cancelled_leave_is_not_on_leave(self):
        for status in ('pending', 'rejected', 'cancelled'):
            self.leave(D(2026, 10, 6), D(2026, 10, 6), status=status)
        self.assertEqual(self.status(self.month('2026-10'), '2026-10-06'), 'absent')

    def test_a_check_in_on_a_leave_day_counts_as_present(self):
        self.present(self.me, D(2026, 10, 6))
        self.leave(D(2026, 10, 6), D(2026, 10, 6))
        data = self.month('2026-10')
        self.assertEqual(self.status(data, '2026-10-06'), 'present')
        self.assertEqual(data['summary']['on_leave'], 0)

    def test_leave_days_are_not_expected_so_they_do_not_lower_the_rate(self):
        self.present(self.me, D(2026, 10, 5), D(2026, 10, 7))
        self.leave(D(2026, 10, 6), D(2026, 10, 6))
        self.assertEqual(self.month('2026-10')['summary']['attendance_rate'], 100.0)

    def test_the_rate_is_present_over_present_plus_absent(self):
        self.present(self.me, D(2026, 10, 5), D(2026, 10, 6))
        self.assertEqual(self.month('2026-10')['summary'], {'present': 2, 'absent': 1, 'on_leave': 0, 'attendance_rate': 66.7})

    def test_leave_over_several_days_covers_each_working_day(self):
        self.leave(D(2026, 10, 5), D(2026, 10, 7))
        self.assertEqual(self.month('2026-10')['summary'], {'present': 0, 'absent': 0, 'on_leave': 3, 'attendance_rate': 0.0})

    def test_leave_that_starts_in_the_previous_month_reaches_into_this_one(self):
        self.leave(D(2026, 9, 28), D(2026, 10, 5))
        self.assertEqual(self.status(self.month('2026-10'), '2026-10-05'), 'on_leave')


class TodayTests(Base):
    def test_today_without_a_check_in_is_not_absent_yet(self):
        self.present(self.other, TODAY)
        data = self.month()
        self.assertIsNone(self.status(data, '2026-10-19'))
        self.assertEqual(data['summary']['absent'], 0)

    def test_today_is_present_once_checked_in(self):
        self.present(self.me, TODAY)
        data = self.month()
        self.assertEqual(self.status(data, '2026-10-19'), 'present')
        self.assertEqual(data['summary']['present'], 1)

    def test_today_on_approved_leave_shows_on_leave(self):
        self.present(self.other, TODAY)
        self.leave(TODAY, TODAY)
        self.assertEqual(self.status(self.month(), '2026-10-19'), 'on_leave')


class MonthTests(Base):
    def test_a_month_with_no_data_is_all_empty_and_zero(self):
        data = self.month('2026-08')
        self.assertTrue(all(d['status'] is None for d in data['days']))
        self.assertEqual(data['summary'], {'present': 0, 'absent': 0, 'on_leave': 0, 'attendance_rate': 0.0})

    def test_the_default_month_is_the_current_month(self):
        data = self.month()
        self.assertEqual((data['month'], data['label']), ('2026-10', 'October 2026'))

    def test_the_grid_facts(self):
        data = self.month('2026-10')
        self.assertEqual(len(data['days']), 31)
        self.assertEqual(data['first_weekday'], 3)                  # 1 October 2026 is a Thursday
        self.assertEqual(len(self.month('2028-02')['days']), 29)    # a leap year

    def test_previous_and_next(self):
        data = self.month('2026-10')
        self.assertEqual((data['previous'], data['next']), ('2026-09', None))     # no next after the current month
        self.assertEqual(self.month('2026-09')['next'], '2026-10')
        self.assertEqual(self.month('2026-01')['previous'], '2025-12')
        self.assertEqual(self.month('2025-12')['next'], '2026-01')
        self.assertIsNone(self.month('2000-01')['previous'])

    def test_a_future_month_is_empty_and_has_no_next(self):
        data = self.month('2027-03')
        self.assertTrue(all(d['status'] is None for d in data['days']))
        self.assertIsNone(data['next'])

    def test_a_bad_month_is_refused(self):
        for text in ('2026-13', '2026-00', 'abc', '2026-1', '1999-12', '2026-10-01'):
            with self.assertRaises(services.AttendanceError, msg=text):
                self.month(text)


class IsolationTests(Base):
    def test_another_employees_check_ins_never_show_as_mine(self):
        self.present(self.other, D(2026, 10, 5), D(2026, 10, 6))
        data = self.month('2026-10')
        self.assertEqual(self.status(data, '2026-10-05'), 'absent')
        self.assertEqual(data['summary']['present'], 0)

    def test_another_employees_leave_never_shows_as_mine(self):
        self.present(self.boss, D(2026, 10, 5))
        self.leave(D(2026, 10, 5), D(2026, 10, 5), employee=self.other)
        self.assertEqual(self.status(self.month('2026-10'), '2026-10-05'), 'absent')

    def test_another_company_never_makes_a_working_day_for_me(self):
        beta = register_company('Beta', 'beta', 'ceo@beta.com')
        beta_ceo = Employee.objects.get(user__email='ceo@beta.com')
        self.present(beta_ceo, D(2026, 10, 5))
        self.assertIsNone(self.status(self.month('2026-10'), '2026-10-05'))


class ApiTests(Base):
    def test_the_calendar_comes_in_the_standard_envelope(self):
        self.present(self.me, D(2026, 10, 5))
        res = self.client_me.get(URL, {'month': '2026-10'})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        data = body.get('data', body)
        self.assertEqual(data['month'], '2026-10')
        self.assertEqual(data['summary']['present'], 1)

    def test_no_month_means_this_month(self):
        res = self.client_me.get(URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json().get('data', res.json())['month'], '2026-10')

    def test_a_bad_month_is_a_400_with_a_clear_message(self):
        res = self.client_me.get(URL, {'month': '2026-13'})
        self.assertEqual(res.status_code, 400)
        self.assertIn('2026-10', res.content.decode())

    def test_you_cannot_ask_for_somebody_elses_calendar(self):
        self.present(self.other, D(2026, 10, 5))
        for param in ('employee', 'employee_id', 'user'):
            res = self.client_me.get(URL, {'month': '2026-10', param: str(self.other.id)})
            data = res.json().get('data', res.json())
            self.assertEqual(data['summary']['present'], 0, param)

    def test_it_needs_a_login(self):
        from rest_framework.test import APIClient
        self.assertEqual(APIClient().get(URL).status_code, 401)

    def test_it_is_read_only(self):
        for method in ('post', 'put', 'patch', 'delete'):
            self.assertEqual(getattr(self.client_me, method)(URL, {}, format='json').status_code, 405, method)

    def test_the_number_of_queries_does_not_grow_with_the_data(self):
        self.present(self.me, D(2026, 10, 5))
        with CaptureQueriesContext(connection) as small:
            self.client_me.get(URL, {'month': '2026-10'})
        for n in range(1, 17):
            self.present(self.me, D(2026, 9, 1) + datetime.timedelta(days=n))
            self.present(self.other, D(2026, 10, 1) + datetime.timedelta(days=n))
        self.leave(D(2026, 10, 12), D(2026, 10, 14))
        self.leave(D(2026, 10, 15), D(2026, 10, 16))
        with CaptureQueriesContext(connection) as big:
            self.client_me.get(URL, {'month': '2026-10'})
        self.assertEqual(len(small), len(big))
