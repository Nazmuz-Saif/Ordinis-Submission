import datetime
import io
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from analytics import services
from analytics.models import CompanyHealthSnapshot
from attendance.leave_models import LeaveRequest, LeaveType
from attendance.models import Attendance
from core.test_utils import add_employee, give_role, login_as, register_company, rows
from organization.models import Department, Employee
from tasks.models import Task
from tenants.models import Company

OVERVIEW = '/api/v1/analytics/overview/'
SNAPSHOTS = '/api/v1/analytics/snapshots/'
TODAY = datetime.date(2026, 10, 19)          # a Monday; every test fixes "today" so nothing depends on the real date
D = datetime.date


def at(day):
    return {'date': day, 'check_in': timezone.now()}


class Base(TestCase):
    def setUp(self):
        patcher = mock.patch('analytics.services.local_today', return_value=(TODAY, None))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.company = Company.objects.get(subdomain='acme')
        add_employee(self.ceo, 'emp@acme.com', 'E-001')
        self.boss = Employee.objects.get(user__email='ceo@acme.com')
        self.emp = Employee.objects.get(user__email='emp@acme.com')    # head count is 2

    def present(self, employee, *days):
        for day in days:
            Attendance.objects.create(company=self.company, employee=employee, **at(day))

    def leave(self, employee, first, last, status=LeaveRequest.STATUS_APPROVED):
        kind, _ = LeaveType.objects.get_or_create(company=self.company, name='Annual', defaults={'days_allowed_per_year': 20})
        return LeaveRequest.objects.create(
            company=self.company, employee=employee, leave_type=kind, start_date=first, end_date=last,
            days=(last - first).days + 1, reason='test', status=status,
        )

    def task(self, employee, status=Task.STATUS_NOT_STARTED, deadline=None, title='T'):
        return Task.objects.create(company=self.company, title=title, assigned_to=employee, status=status, deadline=deadline)

    def month(self, key, data=None):
        data = data or services.overview(self.company)
        return next(m for m in data['attendance_by_month'] if m['month'] == key)


class AttendanceRateTests(Base):
    def test_the_rate_is_present_days_over_expected_days_of_the_working_days(self):
        self.present(self.boss, D(2026, 10, 5), D(2026, 10, 6))
        self.present(self.emp, D(2026, 10, 5))
        october = self.month('2026-10')
        self.assertEqual(october['working_days'], 2)
        self.assertEqual(october['rate'], 75.0)       # 3 present of 2 people x 2 days

    def test_a_day_nobody_checked_in_is_not_a_working_day(self):
        self.present(self.boss, D(2026, 10, 5))
        self.present(self.emp, D(2026, 10, 5))        # Oct 6 has no row at all (a weekend or holiday)
        self.assertEqual(self.month('2026-10')['working_days'], 1)
        self.assertEqual(self.month('2026-10')['rate'], 100.0)

    def test_approved_leave_without_a_check_in_is_not_expected(self):
        self.present(self.boss, D(2026, 10, 5), D(2026, 10, 6))
        self.present(self.emp, D(2026, 10, 5))
        self.leave(self.emp, D(2026, 10, 6), D(2026, 10, 6))
        self.assertEqual(self.month('2026-10')['rate'], 100.0)    # 3 present of 4 - 1 on leave

    def test_pending_rejected_and_cancelled_leave_changes_nothing(self):
        self.present(self.boss, D(2026, 10, 5), D(2026, 10, 6))
        self.present(self.emp, D(2026, 10, 5))
        for status in ('pending', 'rejected', 'cancelled'):
            self.leave(self.emp, D(2026, 10, 6), D(2026, 10, 6), status=status)
        self.assertEqual(self.month('2026-10')['rate'], 75.0)

    def test_leave_on_a_day_the_person_still_checked_in_is_not_taken_off_twice(self):
        self.present(self.boss, D(2026, 10, 5))
        self.present(self.emp, D(2026, 10, 5))
        self.leave(self.emp, D(2026, 10, 5), D(2026, 10, 5))
        self.assertEqual(self.month('2026-10')['rate'], 100.0)    # never above 100

    def test_two_overlapping_leaves_of_one_person_count_once(self):
        self.present(self.boss, D(2026, 10, 5), D(2026, 10, 6))
        self.leave(self.emp, D(2026, 10, 5), D(2026, 10, 6))
        self.leave(self.emp, D(2026, 10, 6), D(2026, 10, 7))
        self.assertEqual(self.month('2026-10')['rate'], 100.0)    # 2 present of 4 - 2 on leave

    def test_a_month_without_data_is_zero_not_an_error(self):
        self.present(self.boss, D(2026, 10, 5))
        september = self.month('2026-09')
        self.assertEqual((september['rate'], september['working_days']), (0.0, 0))

    def test_the_last_six_months_come_oldest_first_with_labels(self):
        months = services.overview(self.company)['attendance_by_month']
        self.assertEqual([m['month'] for m in months], ['2026-05', '2026-06', '2026-07', '2026-08', '2026-09', '2026-10'])
        self.assertEqual((months[0]['short'], months[-1]['label']), ('May', 'October 2026'))

    def test_the_months_cross_a_year_boundary(self):
        with mock.patch('analytics.services.local_today', return_value=(D(2027, 2, 3), None)):
            months = services.overview(self.company)['attendance_by_month']
        self.assertEqual([m['month'] for m in months][:3], ['2026-09', '2026-10', '2026-11'])
        self.assertEqual(months[-1]['month'], '2027-02')

    def test_the_change_against_last_month_needs_data_in_both_months(self):
        self.present(self.boss, D(2026, 10, 5))
        self.assertIsNone(services.overview(self.company)['metrics']['attendance_rate_change'])
        self.present(self.boss, D(2026, 9, 7))
        self.present(self.emp, D(2026, 9, 7))                       # September 100.0, October 50.0
        self.assertEqual(services.overview(self.company)['metrics']['attendance_rate_change'], -50.0)

    def test_a_check_in_after_today_is_not_counted(self):
        self.present(self.boss, D(2026, 10, 20))
        self.assertEqual(self.month('2026-10')['working_days'], 0)


class TaskNumberTests(Base):
    def setUp(self):
        super().setUp()
        eng = Department.objects.create(company=self.company, name='Engineering')
        self.emp.department = eng
        self.emp.save()                                           # the CEO has no department

    def test_the_task_numbers(self):
        self.task(self.emp, Task.STATUS_COMPLETED, deadline=D(2026, 10, 1))      # done late: not overdue
        self.task(self.emp, Task.STATUS_IN_PROGRESS, deadline=D(2026, 10, 10))   # overdue
        self.task(self.emp, Task.STATUS_NOT_STARTED, deadline=D(2026, 10, 30))
        self.task(self.boss, Task.STATUS_REJECTED)
        metrics = services.overview(self.company)['metrics']
        self.assertEqual(metrics['task_completion_rate'], 25.0)
        self.assertEqual(metrics['overdue_tasks'], 1)
        self.assertEqual(metrics['average_workload'], 1.5)         # 3 open tasks over 2 employees

    def test_a_task_due_today_is_not_overdue(self):
        self.task(self.emp, deadline=TODAY)
        self.assertEqual(services.overview(self.company)['metrics']['overdue_tasks'], 0)

    def test_completed_and_pending_by_department(self):
        self.task(self.emp, Task.STATUS_COMPLETED)
        self.task(self.emp, Task.STATUS_COMPLETED)
        self.task(self.emp, Task.STATUS_SUBMITTED)
        self.task(self.boss, Task.STATUS_IN_PROGRESS)
        chart = services.overview(self.company)['tasks_by_department']
        self.assertEqual(chart, [
            {'name': 'Engineering', 'completed': 2, 'pending': 1},
            {'name': 'No department', 'completed': 0, 'pending': 1},
        ])

    def test_no_tasks_and_no_attendance_is_all_zero_and_flagged_empty(self):
        Task.objects.all().delete()
        data = services.overview(self.company)
        self.assertEqual(data['metrics'], {
            'attendance_rate': 0.0, 'attendance_rate_change': None, 'task_completion_rate': 0.0,
            'overdue_tasks': 0, 'average_workload': 0.0,
        })
        self.assertEqual(data['tasks_by_department'], [])
        self.assertFalse(data['has_data'])

    def test_data_flips_the_empty_flag(self):
        self.task(self.emp)
        self.assertTrue(services.overview(self.company)['has_data'])


class ApiTests(Base):
    def test_the_ceo_gets_the_overview_in_the_standard_envelope(self):
        self.task(self.emp, Task.STATUS_COMPLETED)
        res = self.ceo.get(OVERVIEW)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body['success'])
        self.assertEqual(body['data']['metrics']['task_completion_rate'], 100.0)
        self.assertEqual(len(body['data']['attendance_by_month']), 6)

    def test_an_employee_without_the_permission_gets_403_and_no_numbers(self):
        employee = login_as('emp@acme.com')
        for url in (OVERVIEW, SNAPSHOTS):
            res = employee.get(url)
            self.assertEqual(res.status_code, 403, url)
            self.assertNotIn('metrics', res.content.decode())

    def test_exactly_the_view_analytics_permission_is_enough(self):
        give_role(self.company.id, self.emp.id, ['view_analytics'])
        self.assertEqual(login_as('emp@acme.com').get(OVERVIEW).status_code, 200)

    def test_a_new_companys_ceo_holds_the_permission(self):
        self.assertTrue(self.boss.has_permission('view_analytics'))

    def test_the_endpoints_are_read_only(self):
        for url in (OVERVIEW, SNAPSHOTS):
            for method in ('post', 'put', 'patch', 'delete'):
                self.assertEqual(getattr(self.ceo, method)(url, {}, format='json').status_code, 405, f'{method} {url}')

    def test_another_company_never_sees_these_numbers(self):
        self.task(self.emp, Task.STATUS_COMPLETED)
        self.present(self.boss, D(2026, 10, 5))
        services.take_snapshot(self.company, TODAY)
        other = register_company('Beta', 'beta', 'ceo@beta.com')
        data = other.get(OVERVIEW).json()['data']
        self.assertEqual(data['tasks_by_department'], [])
        self.assertEqual(data['metrics']['task_completion_rate'], 0.0)
        self.assertFalse(data['has_data'])
        self.assertEqual(rows(other.get(SNAPSHOTS)), [])

    def test_a_company_without_data_answers_200_not_an_error(self):
        other = register_company('Beta', 'beta', 'ceo@beta.com')
        self.assertEqual(other.get(OVERVIEW).status_code, 200)

    def test_the_number_of_queries_does_not_grow_with_the_data(self):
        self.task(self.emp)
        self.present(self.boss, D(2026, 10, 5))
        self.leave(self.emp, D(2026, 10, 6), D(2026, 10, 6))
        with CaptureQueriesContext(connection) as small:
            self.ceo.get(OVERVIEW)
        for n in range(25):
            self.task(self.emp, title=f'x{n}')
            self.present(self.emp, D(2026, 9, 1) + datetime.timedelta(days=n))
        self.leave(self.boss, D(2026, 9, 8), D(2026, 9, 9))
        with CaptureQueriesContext(connection) as big:
            self.ceo.get(OVERVIEW)
        self.assertEqual(len(small), len(big))


class SnapshotTests(Base):
    def test_a_snapshot_stores_the_numbers_of_that_day(self):
        self.present(self.boss, TODAY)
        self.task(self.emp, Task.STATUS_COMPLETED)
        self.task(self.emp, Task.STATUS_NOT_STARTED, deadline=D(2026, 10, 1))
        snapshot, created = services.take_snapshot(self.company, TODAY)
        self.assertTrue(created)
        self.assertEqual(snapshot.headcount, 2)
        self.assertEqual(float(snapshot.attendance_rate), 50.0)
        self.assertEqual(float(snapshot.task_completion_rate), 50.0)
        self.assertEqual((snapshot.open_tasks, snapshot.overdue_tasks), (1, 1))
        self.assertEqual(float(snapshot.health_score), 50.0)

    def test_the_health_score_is_the_average_of_attendance_and_completion(self):
        self.present(self.boss, TODAY)
        self.present(self.emp, TODAY)
        self.task(self.emp, Task.STATUS_COMPLETED)
        self.task(self.emp, Task.STATUS_COMPLETED)
        self.task(self.emp, Task.STATUS_COMPLETED)
        self.task(self.emp, Task.STATUS_NOT_STARTED)
        snapshot, _ = services.take_snapshot(self.company, TODAY)
        self.assertEqual(float(snapshot.health_score), 87.5)       # (100 + 75) / 2

    def test_taking_it_twice_keeps_one_row_per_day_and_refreshes_it(self):
        services.take_snapshot(self.company, TODAY)
        self.present(self.boss, TODAY)
        snapshot, created = services.take_snapshot(self.company, TODAY)
        self.assertFalse(created)
        self.assertEqual(CompanyHealthSnapshot.objects.filter(company=self.company).count(), 1)
        self.assertEqual(float(snapshot.attendance_rate), 50.0)

    def test_leave_is_not_expected_in_a_day_snapshot(self):
        self.present(self.boss, TODAY)
        self.leave(self.emp, TODAY, TODAY)
        snapshot, _ = services.take_snapshot(self.company, TODAY)
        self.assertEqual(float(snapshot.attendance_rate), 100.0)

    def test_the_database_refuses_a_second_row_for_the_same_day(self):
        from django.db import IntegrityError, transaction
        services.take_snapshot(self.company, TODAY)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CompanyHealthSnapshot.objects.create(company=self.company, date=TODAY)

    def test_the_list_shows_only_the_own_company_newest_day_first(self):
        services.take_snapshot(self.company, D(2026, 10, 17))
        services.take_snapshot(self.company, D(2026, 10, 19))
        other = Company.objects.create(name='Beta', subdomain='beta2')
        services.take_snapshot(other, D(2026, 10, 19))
        items = rows(self.ceo.get(SNAPSHOTS))
        self.assertEqual([i['date'] for i in items], ['2026-10-19', '2026-10-17'])

    def test_a_company_with_no_employee_still_gets_a_snapshot(self):
        empty = Company.objects.create(name='Empty', subdomain='empty')
        snapshot, _ = services.take_snapshot(empty, TODAY)
        self.assertEqual(float(snapshot.health_score), 0.0)


class CommandTests(Base):
    def run_command(self, *args):
        out = io.StringIO()
        call_command('take_health_snapshots', *args, stdout=out)
        return out.getvalue()

    def test_it_stores_one_snapshot_for_every_active_company(self):
        Company.objects.create(name='Beta', subdomain='beta')
        text = self.run_command('--date', '2026-10-19')
        self.assertIn('2 new snapshot(s), 0 refreshed', text)
        self.assertIn('0 new snapshot(s), 2 refreshed', self.run_command('--date', '2026-10-19'))

    def test_a_suspended_company_is_skipped(self):
        Company.objects.filter(subdomain='acme').update(is_active=False)
        self.assertIn('0 new snapshot(s)', self.run_command('--date', '2026-10-19'))
        self.assertFalse(CompanyHealthSnapshot.objects.exists())

    def test_one_company_only(self):
        Company.objects.create(name='Beta', subdomain='beta')
        self.run_command('--date', '2026-10-19', '--company', 'beta')
        self.assertEqual(list(CompanyHealthSnapshot.objects.values_list('company__subdomain', flat=True)), ['beta'])

    def test_a_bad_date_or_company_is_a_clear_error(self):
        with self.assertRaises(CommandError):
            self.run_command('--date', '19-10-2026')
        with self.assertRaises(CommandError):
            self.run_command('--company', 'nobody')
