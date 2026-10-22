"""ST-144: Team Attendance: who may open whose month, and what the month shows."""
import datetime
from unittest import mock

from django.utils import timezone
from rest_framework.test import APITestCase

from attendance.models import Attendance
from billing.services import change_plan
from core.test_utils import add_employee, give_role, login_as, register_company
from rbac.catalog import CATALOG_CODENAMES
from rbac.models import Permission, Role
from tenants.models import Company

TEAM = '/api/v1/attendance/attendance/team/'
PEOPLE = '/api/v1/attendance/attendance/team/people/'
NOW = datetime.datetime(2026, 10, 22, 12, 0, tzinfo=datetime.timezone.utc)   # a Thursday, 18:00 in Dhaka


def at(day, hour, minute=0):
    # company zone is Asia/Dhaka (UTC+6)
    return datetime.datetime(2026, 10, day, hour, minute, tzinfo=datetime.timezone(datetime.timedelta(hours=6)))


class TeamBase(APITestCase):
    def setUp(self):
        patcher = mock.patch('attendance.services._now', return_value=NOW)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.ceo = register_company('Team Co', 'team-co', 'ceo@team.com', full_name='Chief Exec')
        change_plan(Company.objects.get(subdomain='team-co'), 'Enterprise')
        self.cid = self.ceo.company_id
        self.head = add_employee(self.ceo, 'head@team.com', 'H1', full_name='Hasan Head', reports_to=str(self.ceo.employee_id))
        self.dev = add_employee(self.ceo, 'dev@team.com', 'D1', full_name='Dina Dev', reports_to=self.head['id'])
        self.junior = add_employee(self.ceo, 'jr@team.com', 'D2', full_name='Jamil Junior', reports_to=self.dev['id'])
        self.other = add_employee(self.ceo, 'other@team.com', 'O1', full_name='Olin Other', reports_to=str(self.ceo.employee_id))
        self.c = {k: login_as(f'{k}@team.com') for k in ('head', 'dev', 'jr', 'other')}

    def record(self, emp, day, cin=(9, 0), cout=(17, 30)):
        return Attendance.objects.create(
            company_id=self.cid, employee_id=emp['id'], date=datetime.date(2026, 10, day),
            check_in=at(day, *cin), check_out=at(day, *cout) if cout else None)

    def team(self, client, emp, month=None):
        params = {'employee': emp['id'], **({'month': month} if month else {})}
        return client.get(TEAM, params)

    def names(self, client):
        return sorted(p['full_name'] for p in client.get(PEOPLE).data['results'])


class ScopeTests(TeamBase):
    def test_the_permission_is_in_the_catalog_and_the_ceo_role_holds_it(self):
        self.assertIn('view_team_attendance', CATALOG_CODENAMES)
        role = Role.objects.get(company_id=self.cid, is_system_default=True)
        self.assertTrue(role.permissions.filter(codename='view_team_attendance').exists())
        self.assertTrue(Permission.objects.get(codename='view_team_attendance').description)

    def test_the_ceo_sees_the_whole_company(self):
        res = self.ceo.get(PEOPLE)
        self.assertTrue(res.data['whole_company'])
        self.assertEqual(len(res.data['results']), 5)

    def test_a_manager_sees_only_the_people_below_at_any_depth(self):
        self.assertEqual(self.names(self.c['head']), ['Dina Dev', 'Jamil Junior'])
        self.assertFalse(self.c['head'].get(PEOPLE).data['whole_company'])

    def test_an_employee_with_no_team_sees_nobody(self):
        self.assertEqual(self.c['jr'].get(PEOPLE).data['results'], [])
        self.assertEqual(self.team(self.c['jr'], self.junior).status_code, 404)    # not even themself here

    def test_the_permission_widens_a_manager_to_the_whole_company(self):
        give_role(self.cid, self.head['id'], ['view_team_attendance'], 'Attendance viewer')
        res = self.c['head'].get(PEOPLE)
        self.assertTrue(res.data['whole_company'])
        self.assertEqual(len(res.data['results']), 5)
        self.assertEqual(self.team(self.c['head'], self.other).status_code, 200)

    def test_a_person_outside_the_scope_is_a_404_not_a_403(self):
        self.assertEqual(self.team(self.c['head'], self.other).status_code, 404)    # not below the head
        self.assertEqual(self.team(self.c['dev'], self.head).status_code, 404)      # upwards is not allowed
        self.assertEqual(self.team(self.c['dev'], self.dev).status_code, 404)

    def test_another_company_is_a_404(self):
        outsider = register_company('Out Co', 'out-co', 'ceo@out.com')
        res = outsider.get(TEAM, {'employee': self.dev['id']})
        self.assertEqual(res.status_code, 404)
        self.assertEqual(self.team(self.ceo, {'id': str(outsider.employee_id)}).status_code, 404)

    def test_a_bad_or_missing_employee_id(self):
        self.assertEqual(self.ceo.get(TEAM, {'employee': 'not-a-uuid'}).status_code, 404)
        self.assertEqual(self.ceo.get(TEAM, {'employee': '00000000-0000-4000-8000-000000000001'}).status_code, 404)
        self.assertEqual(self.ceo.get(TEAM).status_code, 400)

    def test_login_is_required(self):
        from rest_framework.test import APIClient
        self.assertEqual(APIClient().get(TEAM, {'employee': self.dev['id']}).status_code, 401)
        self.assertEqual(APIClient().get(PEOPLE).status_code, 401)

    def test_me_tells_the_menu_whether_the_person_has_a_team(self):
        self.assertTrue(self.c['head'].get('/api/v1/auth/me/').data['data']['has_team'])
        self.assertFalse(self.c['jr'].get('/api/v1/auth/me/').data['data']['has_team'])


class MonthTests(TeamBase):
    def test_the_month_has_times_hours_and_the_total(self):
        self.record(self.dev, 5)                             # 8.5 h
        self.record(self.dev, 6, cin=(10, 15), cout=(14, 15))  # 4 h
        data = self.team(self.c['head'], self.dev, '2026-10').data
        self.assertEqual((data['days_present'], data['total_hours']), (2, 12.5))
        first = data['records'][0]
        self.assertEqual((first['date'], first['check_in_time'], first['check_out_time'], first['hours']), ('2026-10-05', '09:00', '17:30', 8.5))
        self.assertEqual(data['summary']['present'], 2)
        self.assertEqual(data['employee']['full_name'], 'Dina Dev')

    def test_a_day_with_no_check_out_shows_no_check_out_and_no_hours(self):
        self.record(self.dev, 5)
        self.record(self.dev, 6, cout=None)
        data = self.team(self.c['head'], self.dev, '2026-10').data
        open_day = data['records'][1]
        self.assertIsNone(open_day['check_out'])
        self.assertIsNone(open_day['check_out_time'])
        self.assertIsNone(open_day['hours'])
        self.assertEqual(data['total_hours'], 8.5)           # the open day adds nothing
        self.assertEqual(data['days_present'], 2)

    def test_the_calendar_and_cards_match_my_attendance_logic(self):
        self.record(self.dev, 5)
        self.record(self.other, 5)
        self.record(self.other, 6)                           # the company worked on the 6th; Dina did not
        data = self.team(self.ceo, self.dev, '2026-10').data
        days = {d['date']: d['status'] for d in data['days']}
        self.assertEqual((days['2026-10-05'], days['2026-10-06']), ('present', 'absent'))
        self.assertEqual(data['summary']['absent'], 1)
        self.assertEqual(data['summary']['attendance_rate'], 50.0)

    def test_navigation_and_empty_months(self):
        data = self.team(self.ceo, self.dev, '2026-09').data
        self.assertEqual((data['records'], data['total_hours'], data['days_present']), ([], 0.0, 0))
        self.assertEqual(data['next'], '2026-10')
        self.assertEqual(self.team(self.ceo, self.dev, '2026-10').data['next'], None)   # not beyond this month

    def test_a_bad_month_is_a_400(self):
        self.assertEqual(self.team(self.ceo, self.dev, '10-2026').status_code, 400)
        self.assertEqual(self.team(self.ceo, self.dev, '2026-13').status_code, 400)

    def test_only_the_month_asked_for_is_returned(self):
        self.record(self.dev, 5)
        Attendance.objects.create(company_id=self.cid, employee_id=self.dev['id'], date=datetime.date(2026, 9, 29),
                                  check_in=at(29, 9), check_out=at(29, 17))
        self.assertEqual(self.team(self.ceo, self.dev, '2026-10').data['days_present'], 1)
        self.assertEqual(self.team(self.ceo, self.dev, '2026-09').data['days_present'], 1)


class MyAttendanceUnchangedTests(TeamBase):
    def test_my_attendance_shows_only_my_own_data(self):
        self.record(self.dev, 5)
        self.record(self.other, 5)
        mine = self.c['dev'].get('/api/v1/attendance/attendance/')
        self.assertEqual(len(mine.data['data'] if 'data' in mine.data else mine.data), 1)
        cal = self.c['dev'].get('/api/v1/attendance/attendance/calendar/', {'month': '2026-10'}).data
        self.assertEqual(cal['summary']['present'], 1)
        self.assertNotIn('records', cal)

    def test_the_ceo_s_own_list_is_still_only_the_ceo_s(self):
        self.record(self.dev, 5)
        res = self.ceo.get('/api/v1/attendance/attendance/')
        rows = res.data['data'] if isinstance(res.data, dict) and 'data' in res.data else res.data
        self.assertEqual(len(rows), 0)
