"""ST-142: change password, temporary passwords and the PASSWORD_CHANGE_REQUIRED gate."""
from django.test import TestCase
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from accounts.passwords import make_temporary_password
from core.api_matrix import discover_routes
from core.test_utils import add_employee, login_as, register_company, rows

CHANGE = '/api/v1/auth/change-password/'
GOOD_NEW = 'Brand-New-Pass-7391'


def login_tokens(email, password='StrongPass123'):
    res = APIClient().post('/api/v1/auth/login/', {'email': email, 'password': password}, format='json')
    assert res.status_code == 200, res.content
    return res.data['access'], res.data['refresh']


def client_with(access):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
    return c


def refresh(token):
    return APIClient().post('/api/v1/auth/refresh/', {'refresh': token}, format='json')


class ChangePasswordTests(APITestCase):
    def setUp(self):
        self.ceo = register_company('Pw Co', 'pw-co', 'ceo@pw.com')

    def change(self, client=None, **body):
        data = {'current_password': 'StrongPass123', 'new_password': GOOD_NEW, 'confirm_password': GOOD_NEW, **body}
        return (client or self.ceo).post(CHANGE, data, format='json')

    def test_a_wrong_current_password_is_refused_and_nothing_changes(self):
        res = self.change(current_password='nope')
        self.assertEqual(res.status_code, 400)
        self.assertIn('current_password', res.data['error']['field_errors'])
        self.assertTrue(User.objects.get(email='ceo@pw.com').check_password('StrongPass123'))

    def test_the_password_rules_apply(self):
        for bad in ('short1', '12345678', 'password', 'ceo@pw.com'):
            res = self.change(new_password=bad, confirm_password=bad)
            self.assertEqual(res.status_code, 400, bad)
            self.assertIn('new_password', res.data['error']['field_errors'], bad)
        self.assertTrue(User.objects.get(email='ceo@pw.com').check_password('StrongPass123'))

    def test_the_new_password_must_differ_and_must_be_confirmed(self):
        res = self.change(new_password='StrongPass123', confirm_password='StrongPass123')
        self.assertIn('new_password', res.data['error']['field_errors'])
        res = self.change(confirm_password='Different-Pass-1234')
        self.assertIn('confirm_password', res.data['error']['field_errors'])

    def test_missing_fields_are_refused(self):
        self.assertEqual(self.ceo.post(CHANGE, {}, format='json').status_code, 400)
        self.assertEqual(self.ceo.post(CHANGE, {'current_password': 'StrongPass123'}, format='json').status_code, 400)

    def test_success_changes_the_login_password(self):
        res = self.change()
        self.assertEqual(res.status_code, 200, res.content)
        res = APIClient().post('/api/v1/auth/login/', {'email': 'ceo@pw.com', 'password': 'StrongPass123'}, format='json')
        self.assertEqual(res.status_code, 401)
        self.assertEqual(APIClient().post('/api/v1/auth/login/', {'email': 'ceo@pw.com', 'password': GOOD_NEW}, format='json').status_code, 200)

    def test_other_sessions_are_ended_and_the_current_one_stays(self):
        access_a, refresh_a = login_tokens('ceo@pw.com')
        _, refresh_b = login_tokens('ceo@pw.com')
        _, refresh_c = login_tokens('ceo@pw.com')
        res = self.change(client=client_with(access_a), refresh=refresh_a)
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(refresh(refresh_a).status_code, 200)     # this session stays
        self.assertEqual(refresh(refresh_b).status_code, 401)
        self.assertEqual(refresh(refresh_c).status_code, 401)

    def test_without_the_current_refresh_token_every_session_ends(self):
        _, refresh_a = login_tokens('ceo@pw.com')
        self.assertEqual(self.change().status_code, 200)
        self.assertEqual(refresh(refresh_a).status_code, 401)

    def test_a_refresh_token_of_someone_else_does_not_keep_a_session(self):
        other = register_company('Other Co', 'other-co', 'ceo@other.com')
        _, mine = login_tokens('ceo@pw.com')
        _, theirs = login_tokens('ceo@other.com')
        self.change(refresh=theirs)
        self.assertEqual(refresh(mine).status_code, 401)
        self.assertEqual(refresh(theirs).status_code, 200)        # nothing happened to the other person

    def test_another_persons_sessions_are_untouched(self):
        add_employee(self.ceo, 'e@pw.com', 'E1', password='StrongPass123')
        _, emp_refresh = login_tokens('e@pw.com')
        self.change()
        self.assertEqual(refresh(emp_refresh).status_code, 200)

    def test_login_is_required(self):
        self.assertEqual(APIClient().post(CHANGE, {'current_password': 'a', 'new_password': 'b'}, format='json').status_code, 401)

    def test_the_platform_admin_can_change_their_password(self):
        User.objects.create_user(email='pa@o.test', password='StrongPass123', is_platform_admin=True)
        pa = login_as('pa@o.test')
        self.assertEqual(self.change(client=pa).status_code, 200)


class TemporaryPasswordTests(APITestCase):
    def setUp(self):
        self.ceo = register_company('Tmp Co', 'tmp-co', 'ceo@tmp.com')

    def create(self, email='new@tmp.com', code='N1', **extra):
        return self.ceo.post('/api/v1/organization/employees/',
                             {'email': email, 'employee_code': code, 'full_name': 'New Person', **extra}, format='json')

    def test_creating_without_a_password_returns_one_temporary_password(self):
        res = self.create()
        self.assertEqual(res.status_code, 201, res.content)
        temp = res.data['temporary_password']
        self.assertGreaterEqual(len(temp), 12)
        user = User.objects.get(email='new@tmp.com')
        self.assertTrue(user.check_password(temp))
        self.assertTrue(user.must_change_password)

    def test_a_blank_password_counts_as_none(self):
        self.assertIn('temporary_password', self.create(password='  ').data)

    def test_the_temporary_password_is_shown_once_only(self):
        res = self.create()
        emp_id = res.data['id']
        self.assertNotIn('temporary_password', self.ceo.get(f'/api/v1/organization/employees/{emp_id}/').data)
        for row in rows(self.ceo.get('/api/v1/organization/employees/')):
            self.assertNotIn('temporary_password', row)
        patched = self.ceo.patch(f'/api/v1/organization/employees/{emp_id}/', {'full_name': 'Renamed'}, format='json')
        self.assertNotIn('temporary_password', patched.data)

    def test_the_temporary_password_is_not_written_to_the_audit_log(self):
        temp = self.create().data['temporary_password']
        self.assertNotIn(temp, str(rows(self.ceo.get('/api/v1/audit-log/logs/?page_size=100'))))

    def test_every_temporary_password_is_different_and_follows_the_rules(self):
        values = {make_temporary_password() for _ in range(50)}
        self.assertEqual(len(values), 50)
        for v in values:
            self.assertFalse(any(c in v for c in '0O1lI'))
            self.assertTrue(any(c.isdigit() for c in v) and any(c.isupper() for c in v) and any(c.islower() for c in v))

    def test_an_explicit_password_still_works_and_needs_no_change(self):
        res = self.create(password='StrongPass123')
        self.assertEqual(res.status_code, 201)
        self.assertNotIn('temporary_password', res.data)
        self.assertFalse(User.objects.get(email='new@tmp.com').must_change_password)
        self.assertEqual(login_as('new@tmp.com').get('/api/v1/tasks/tasks/').status_code, 200)

    def test_me_and_profile_report_the_flag(self):
        temp = self.create().data['temporary_password']
        me = login_as('new@tmp.com', temp)
        self.assertTrue(me.get('/api/v1/auth/me/').data['data']['must_change_password'])
        self.assertTrue(me.get('/api/v1/auth/profile/').data['data']['must_change_password'])
        self.assertFalse(self.ceo.get('/api/v1/auth/me/').data['data']['must_change_password'])

    def test_until_the_password_is_changed_other_endpoints_answer_403_with_the_code(self):
        temp = self.create().data['temporary_password']
        me = login_as('new@tmp.com', temp)
        for url in ('/api/v1/tasks/tasks/', '/api/v1/dashboard/summary/', '/api/v1/organization/employees/',
                    '/api/v1/notifications/', '/api/v1/attendance/attendance/today/'):
            res = me.get(url)
            self.assertEqual(res.status_code, 403, url)
            self.assertEqual(res.data['error']['code'], 'PASSWORD_CHANGE_REQUIRED', url)
        self.assertEqual(me.post('/api/v1/attendance/attendance/check_in/').status_code, 403)

    def test_me_profile_and_change_password_stay_open(self):
        temp = self.create().data['temporary_password']
        me = login_as('new@tmp.com', temp)
        self.assertEqual(me.get('/api/v1/auth/me/').status_code, 200)
        self.assertEqual(me.get('/api/v1/auth/profile/').status_code, 200)
        self.assertEqual(me.patch('/api/v1/auth/profile/', {'phone': '0170'}, format='json').status_code, 200)
        _, refresh_token = login_tokens('new@tmp.com', temp)
        out = APIClient().post('/api/v1/auth/logout/', {'refresh': refresh_token}, format='json')
        self.assertIn(out.status_code, (200, 204))

    def test_after_the_change_everything_opens(self):
        temp = self.create().data['temporary_password']
        access, refresh_token = login_tokens('new@tmp.com', temp)
        me = client_with(access)
        res = me.post(CHANGE, {'current_password': temp, 'new_password': GOOD_NEW, 'confirm_password': GOOD_NEW, 'refresh': refresh_token}, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertFalse(User.objects.get(email='new@tmp.com').must_change_password)
        self.assertEqual(me.get('/api/v1/tasks/tasks/').status_code, 200)

    def test_a_wrong_current_password_keeps_the_gate_closed(self):
        temp = self.create().data['temporary_password']
        me = login_as('new@tmp.com', temp)
        self.assertEqual(me.post(CHANGE, {'current_password': 'nope', 'new_password': GOOD_NEW}, format='json').status_code, 400)
        self.assertEqual(me.get('/api/v1/tasks/tasks/').status_code, 403)

    def test_the_old_temporary_password_stops_working_after_the_change(self):
        temp = self.create().data['temporary_password']
        login_as('new@tmp.com', temp).post(CHANGE, {'current_password': temp, 'new_password': GOOD_NEW}, format='json')
        res = APIClient().post('/api/v1/auth/login/', {'email': 'new@tmp.com', 'password': temp}, format='json')
        self.assertEqual(res.status_code, 401)

    def test_the_plan_limit_still_refuses_and_creates_no_temporary_account(self):
        for n in range(9):
            self.create(email=f'x{n}@tmp.com', code=f'X{n}')
        before = User.objects.count()
        res = self.create(email='over@tmp.com', code='OVER')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(User.objects.count(), before)


class GateCoversEveryCompanyEndpointTests(TestCase):
    OPEN = ('/api/v1/auth/',)

    def test_every_company_route_is_closed_to_a_temporary_password_login(self):
        ceo = register_company('Gate Co', 'gate-co', 'ceo@gate.com')
        temp = ceo.post('/api/v1/organization/employees/', {'email': 'g@gate.com', 'employee_code': 'G1'}, format='json').data['temporary_password']
        me = login_as('g@gate.com', temp)
        checked, failures = 0, []
        for route in discover_routes():
            names = route.permission_class_names()
            if route.url().startswith(self.OPEN[0]) or 'AllowAny' in names or 'IsPlatformAdmin' in names:
                continue
            for method in route.methods:
                res = me.generic(method, route.url())
                checked += 1
                code = (res.data or {}).get('error', {}).get('code') if hasattr(res, 'data') and isinstance(res.data, dict) else None
                if res.status_code != 403 or code != 'PASSWORD_CHANGE_REQUIRED':
                    failures.append(f'{route.label(method)} -> {res.status_code} {code}')
        self.assertGreater(checked, 80)
        self.assertEqual(failures, [], '\n' + '\n'.join(failures))
