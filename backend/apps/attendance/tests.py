from datetime import datetime, timezone as dt_tz
from unittest.mock import patch

from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from core.test_utils import add_employee, login_as, register_company
from tenants.models import CompanySettings
from .models import Attendance

BASE = '/api/v1/attendance/attendance/'


def at(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=dt_tz.utc)


def clock(moment):
    """Pretend that 'now' is `moment` (UTC)."""
    return patch('attendance.services._now', return_value=moment)


class AttendanceTests(APITestCase):

    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')   # time zone: Asia/Dhaka (UTC+6)
        self.emp = add_employee(self.ceo, 'emp@acme.com', 'E-1')
        self.emp_c = login_as('emp@acme.com')

    # --- check in ---------------------------------------------------------
    def test_check_in_records_time_in_company_zone(self):
        with clock(at(2026, 10, 5, 3, 30)):           # 09:30 in Dhaka
            res = self.emp_c.post(BASE + 'check_in/')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.data['check_in_time'], '09:30')
        self.assertEqual(res.data['date'], '2026-10-05')
        self.assertEqual(res.data['status'], 'checked_in')
        self.assertIsNone(res.data['check_out_time'])

    def test_second_check_in_same_day_is_rejected(self):
        with clock(at(2026, 10, 5, 3, 30)):
            self.emp_c.post(BASE + 'check_in/')
        with clock(at(2026, 10, 5, 8, 0)):
            res = self.emp_c.post(BASE + 'check_in/')
        self.assertEqual(res.status_code, 400)
        self.assertIn('already checked in', str(res.content))
        self.assertEqual(Attendance.objects.count(), 1)

    def test_database_allows_one_row_per_employee_per_day(self):
        with clock(at(2026, 10, 5, 3, 30)):
            self.emp_c.post(BASE + 'check_in/')
        row = Attendance.objects.get()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Attendance.objects.create(company=row.company, employee=row.employee, date=row.date, check_in=row.check_in)

    # --- check out --------------------------------------------------------
    def test_check_out_before_check_in_is_rejected(self):
        with clock(at(2026, 10, 5, 3, 30)):
            res = self.emp_c.post(BASE + 'check_out/')
        self.assertEqual(res.status_code, 400)
        self.assertIn('Check in first', str(res.content))
        self.assertEqual(Attendance.objects.count(), 0)

    def test_check_in_then_check_out(self):
        with clock(at(2026, 10, 5, 3, 30)):
            self.emp_c.post(BASE + 'check_in/')
        with clock(at(2026, 10, 5, 11, 15)):           # 17:15 in Dhaka
            res = self.emp_c.post(BASE + 'check_out/')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual((res.data['check_in_time'], res.data['check_out_time']), ('09:30', '17:15'))
        self.assertEqual(res.data['status'], 'checked_out')

    def test_second_check_out_is_rejected(self):
        with clock(at(2026, 10, 5, 3, 30)):
            self.emp_c.post(BASE + 'check_in/')
        with clock(at(2026, 10, 5, 11, 0)):
            self.emp_c.post(BASE + 'check_out/')
            res = self.emp_c.post(BASE + 'check_out/')
        self.assertEqual(res.status_code, 400)
        self.assertIn('already checked out', str(res.content))

    def test_yesterdays_check_in_does_not_allow_check_out_today(self):
        with clock(at(2026, 10, 5, 3, 30)):
            self.emp_c.post(BASE + 'check_in/')
        with clock(at(2026, 10, 6, 3, 30)):            # next day, never checked in
            res = self.emp_c.post(BASE + 'check_out/')
        self.assertEqual(res.status_code, 400)

    # --- the company's own time zone -------------------------------------
    def test_day_changes_at_the_companys_midnight_not_utc(self):
        with clock(at(2026, 10, 5, 17, 0)):            # 23:00 Oct 5 in Dhaka
            self.emp_c.post(BASE + 'check_in/')
        with clock(at(2026, 10, 5, 19, 0)):            # 01:00 Oct 6 in Dhaka: a new day, still Oct 5 in UTC
            res = self.emp_c.post(BASE + 'check_in/')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.data['date'], '2026-10-06')
        self.assertEqual(Attendance.objects.count(), 2)

    def test_another_company_zone_gives_another_day(self):
        beta = register_company('Beta', 'beta', 'ceo@beta.com')
        CompanySettings.objects.filter(company_id=beta.company_id).update(timezone='America/New_York')
        moment = at(2026, 10, 5, 2, 0)                 # Dhaka: Oct 5 08:00  |  New York: Oct 4 22:00
        with clock(moment):
            dhaka = self.emp_c.post(BASE + 'check_in/')
            new_york = beta.post(BASE + 'check_in/')
        self.assertEqual(dhaka.data['date'], '2026-10-05')
        self.assertEqual(new_york.data['date'], '2026-10-04')
        self.assertEqual((dhaka.data['check_in_time'], new_york.data['check_in_time']), ('08:00', '22:00'))

    def test_broken_timezone_setting_falls_back(self):
        CompanySettings.objects.filter(company_id=self.ceo.company_id).update(timezone='Not/AZone')
        with clock(at(2026, 10, 5, 3, 30)):
            self.assertEqual(self.emp_c.post(BASE + 'check_in/').status_code, 200)

    # --- today / list / privacy ------------------------------------------
    def test_today_endpoint(self):
        with clock(at(2026, 10, 5, 3, 30)):
            empty = self.emp_c.get(BASE + 'today/')
            self.emp_c.post(BASE + 'check_in/')
            full = self.emp_c.get(BASE + 'today/')
        self.assertEqual((empty.data['date'], empty.data['record']), ('2026-10-05', None))
        self.assertEqual(full.data['record']['check_in_time'], '09:30')

    def test_list_shows_only_my_records(self):
        other = add_employee(self.ceo, 'other@acme.com', 'E-2')
        with clock(at(2026, 10, 5, 3, 30)):
            self.emp_c.post(BASE + 'check_in/')
            login_as('other@acme.com').post(BASE + 'check_in/')
        mine = self.emp_c.get(BASE).data
        self.assertEqual(len(mine), 1)
        self.assertEqual(Attendance.objects.count(), 2)
        # the CEO also sees only his own (none)
        self.assertEqual(self.ceo.get(BASE).data, [])

    def test_other_company_cannot_open_my_record(self):
        with clock(at(2026, 10, 5, 3, 30)):
            rid = self.emp_c.post(BASE + 'check_in/').data['id']
        beta = register_company('Beta', 'beta', 'ceo@beta.com')
        self.assertEqual(beta.get(f'{BASE}{rid}/').status_code, 404)

    def test_records_cannot_be_written_directly(self):
        self.assertEqual(self.emp_c.post(BASE, {'date': '2026-10-05'}, format='json').status_code, 405)
