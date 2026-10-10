from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from core.test_utils import add_employee, give_role, login_as, register_company, rows
from organization.models import Department
from payroll.models import SalaryStructure
from platform_admin.models import ImpersonationLog, SupportAccessRequest
from tasks.models import Task

REQUESTS = '/api/v1/platform-admin/requests/'
CO_REQUESTS = '/api/v1/platform-admin/company/access-requests/'
CO_LOG = '/api/v1/platform-admin/company/access-log/'


def support(company_id, resource):
    return f'/api/v1/platform-admin/support/{company_id}/{resource}/'


def make_admin(email='root@ordinis.com'):
    call_command('create_platform_admin', email=email, password='StrongPass123', stdout=StringIO())
    return login_as(email)


class BaseCase(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.cid = self.ceo.company_id
        self.beta = register_company('Beta', 'beta', 'ceo@beta.com')
        Department.objects.create(company_id=self.cid, name='Acme Engineering')
        Department.objects.create(company_id=self.beta.company_id, name='Beta Secret Dept')
        Task.objects.create(company_id=self.cid, title='Acme task', assigned_to_id=self.ceo.employee_id)

    def ask(self, reason='Bug #123: dashboard is empty', admin=None, company=None):
        return (admin or self.admin).post(REQUESTS, {'company': str(company or self.cid), 'reason': reason}, format='json')

    def approved(self, hours=None):
        rid = self.ask().data['id']
        body = {'duration_hours': hours} if hours else {}
        res = self.ceo.post(f'{CO_REQUESTS}{rid}/approve/', body, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        return rid


class PlatformAdminAccountTests(BaseCase):
    def test_command_creates_a_company_less_platform_admin(self):
        user = User.objects.get(email='root@ordinis.com')
        self.assertTrue(user.is_platform_admin)
        self.assertIsNone(user.company)
        self.assertFalse(hasattr(user, 'employee'))

    def test_command_refuses_duplicate_and_short_password(self):
        with self.assertRaises(CommandError):
            call_command('create_platform_admin', email='root@ordinis.com', password='StrongPass123', stdout=StringIO())
        with self.assertRaises(CommandError):
            call_command('create_platform_admin', email='x@ordinis.com', password='short', stdout=StringIO())

    def test_me_tells_the_frontend_who_is_a_platform_admin(self):
        self.assertTrue(self.admin.get('/api/v1/auth/me/').data['data']['is_platform_admin'])
        self.assertFalse(self.ceo.get('/api/v1/auth/me/').data['data']['is_platform_admin'])

    def test_nobody_can_make_themselves_a_platform_admin_when_registering(self):
        res = APIClient().post('/api/v1/auth/register/', {
            'company_name': 'Evil', 'subdomain': 'evil', 'ceo_email': 'evil@x.com',
            'ceo_password': 'StrongPass123', 'is_platform_admin': True}, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertFalse(User.objects.get(email='evil@x.com').is_platform_admin)

    def test_platform_admin_cannot_use_any_company_endpoint(self):
        for url in ('/api/v1/organization/departments/', '/api/v1/organization/employees/',
                    '/api/v1/tasks/tasks/', '/api/v1/payroll/salary-structures/', '/api/v1/dashboard/summary/'):
            self.assertIn(self.admin.get(url).status_code, (401, 403), url)

    def test_ceo_and_employees_cannot_use_platform_admin_endpoints(self):
        emp = add_employee(self.ceo, 'e@acme.com', 'A-2')
        emp_c = login_as('e@acme.com')
        for client in (self.ceo, emp_c):
            self.assertEqual(client.get(REQUESTS).status_code, 403)
            self.assertEqual(client.post(REQUESTS, {'company': str(self.cid), 'reason': 'x'}, format='json').status_code, 403)
            self.assertEqual(client.get(support(self.cid, 'employees')).status_code, 403)


class RequestFlowTests(BaseCase):
    def test_platform_admin_sends_a_request_and_it_starts_pending(self):
        res = self.ask()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['status'], 'pending')
        self.assertEqual(res.data['company_name'], 'Acme')
        self.assertIsNone(res.data['expires_at'])

    def test_a_reason_is_required(self):
        for reason in ('', '   '):
            res = self.ask(reason=reason)
            self.assertEqual(res.status_code, 400)
            self.assertEqual(res.data['error']['code'], 'SUPPORT_REASON_REQUIRED')

    def test_unknown_company_is_rejected(self):
        res = self.admin.post(REQUESTS, {'company': '00000000-0000-0000-0000-000000000000', 'reason': 'x'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_only_one_open_request_per_company(self):
        self.ask()
        res = self.ask()
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data['error']['code'], 'SUPPORT_REQUEST_ALREADY_OPEN')

    def test_a_new_request_is_allowed_after_a_denial(self):
        rid = self.ask().data['id']
        self.ceo.post(f'{CO_REQUESTS}{rid}/deny/')
        self.assertEqual(self.ask().status_code, 201)

    def test_ceo_sees_the_request_and_the_other_company_does_not(self):
        rid = self.ask().data['id']
        listed = rows(self.ceo.get(CO_REQUESTS))
        self.assertEqual([r['id'] for r in listed], [rid])
        self.assertEqual(listed[0]['requested_by_email'], 'root@ordinis.com')
        self.assertEqual(rows(self.beta.get(CO_REQUESTS)), [])
        self.assertEqual(self.beta.get(f'{CO_REQUESTS}{rid}/').status_code, 404)
        self.assertEqual(self.beta.post(f'{CO_REQUESTS}{rid}/approve/').status_code, 404)

    def test_an_employee_without_the_permission_cannot_see_or_decide(self):
        rid = self.ask().data['id']
        add_employee(self.ceo, 'e@acme.com', 'A-2')
        emp_c = login_as('e@acme.com')
        self.assertEqual(emp_c.get(CO_REQUESTS).status_code, 403)
        self.assertEqual(emp_c.post(f'{CO_REQUESTS}{rid}/approve/').status_code, 403)
        self.assertEqual(emp_c.get(CO_LOG).status_code, 403)
        self.assertEqual(SupportAccessRequest.objects.get(id=rid).status, 'pending')

    def test_an_employee_given_the_permission_can_decide(self):
        rid = self.ask().data['id']
        emp = add_employee(self.ceo, 'e@acme.com', 'A-2')
        give_role(self.cid, emp['id'], ['approve_support_access'])
        self.assertEqual(login_as('e@acme.com').post(f'{CO_REQUESTS}{rid}/deny/').status_code, 200)

    def test_approve_sets_a_default_24_hour_limit(self):
        rid = self.ask().data['id']
        res = self.ceo.post(f'{CO_REQUESTS}{rid}/approve/', {}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['status'], 'approved')
        left = SupportAccessRequest.objects.get(id=rid).expires_at - timezone.now()
        self.assertTrue(timedelta(hours=23, minutes=59) < left <= timedelta(hours=24))

    def test_approve_accepts_1_to_72_hours_only(self):
        rid = self.ask().data['id']
        for bad in (0, 73, -1, 'abc'):
            res = self.ceo.post(f'{CO_REQUESTS}{rid}/approve/', {'duration_hours': bad}, format='json')
            self.assertEqual(res.status_code, 400, bad)
            self.assertEqual(res.data['error']['code'], 'SUPPORT_BAD_HOURS')
        self.assertEqual(SupportAccessRequest.objects.get(id=rid).status, 'pending')
        ok = self.ceo.post(f'{CO_REQUESTS}{rid}/approve/', {'duration_hours': 2}, format='json')
        self.assertEqual(ok.status_code, 200)
        left = SupportAccessRequest.objects.get(id=rid).expires_at - timezone.now()
        self.assertTrue(timedelta(hours=1, minutes=59) < left <= timedelta(hours=2))

    def test_a_decided_request_cannot_be_decided_again(self):
        rid = self.ask().data['id']
        self.ceo.post(f'{CO_REQUESTS}{rid}/deny/')
        for action in ('approve', 'deny'):
            res = self.ceo.post(f'{CO_REQUESTS}{rid}/{action}/')
            self.assertEqual(res.status_code, 400)
            self.assertEqual(res.data['error']['code'], 'SUPPORT_NOT_PENDING')
        self.assertEqual(SupportAccessRequest.objects.get(id=rid).status, 'denied')

    def test_decision_records_who_and_when(self):
        rid = self.ask().data['id']
        res = self.ceo.post(f'{CO_REQUESTS}{rid}/approve/')
        self.assertEqual(res.data['decided_by_name'], 'ceo@acme.com')
        self.assertIsNotNone(res.data['decided_at'])

    def test_platform_admin_sees_only_their_own_requests(self):
        self.ask()
        other = make_admin('other@ordinis.com')
        self.assertEqual(len(rows(self.admin.get(REQUESTS))), 1)
        self.assertEqual(rows(other.get(REQUESTS)), [])


class GatedAccessTests(BaseCase):
    RESOURCES = ('departments', 'employees', 'tasks')

    def test_no_request_means_no_data(self):
        for r in self.RESOURCES:
            res = self.admin.get(support(self.cid, r))
            self.assertEqual(res.status_code, 403, r)
            self.assertEqual(res.data['error']['code'], 'SUPPORT_ACCESS_REQUIRED')
        self.assertEqual(ImpersonationLog.objects.count(), 0)

    def test_pending_and_denied_requests_give_no_data(self):
        rid = self.ask().data['id']
        self.assertEqual(self.admin.get(support(self.cid, 'employees')).status_code, 403)
        self.ceo.post(f'{CO_REQUESTS}{rid}/deny/')
        self.assertEqual(self.admin.get(support(self.cid, 'employees')).status_code, 403)

    def test_approved_request_opens_read_access_to_that_company_only(self):
        self.approved()
        res = self.admin.get(support(self.cid, 'departments'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual([d['name'] for d in rows(res)], ['Acme Engineering'])
        self.assertEqual(res.data['pagination']['count'], 1)
        self.assertEqual(len(rows(self.admin.get(support(self.cid, 'employees')))), 1)
        self.assertEqual([t['title'] for t in rows(self.admin.get(support(self.cid, 'tasks')))], ['Acme task'])
        # the grant for Acme says nothing about Beta
        res = self.admin.get(support(self.beta.company_id, 'departments'))
        self.assertEqual(res.status_code, 403)
        self.assertNotIn('Beta Secret Dept', res.content.decode())

    def test_access_is_read_only(self):
        self.approved()
        url = support(self.cid, 'departments')
        for call in (self.admin.post, self.admin.put, self.admin.patch, self.admin.delete):
            self.assertEqual(call(url, {'name': 'x'}, format='json').status_code, 405)

    def test_salary_and_payroll_are_never_offered(self):
        SalaryStructure.objects.create(company_id=self.cid, employee_id=self.ceo.employee_id, base_salary=987654)
        self.approved()
        for r in ('salary-structures', 'payslips', 'payroll', 'unknown'):
            self.assertEqual(self.admin.get(support(self.cid, r)).status_code, 404, r)
        for r in self.RESOURCES:
            self.assertNotIn('987654', self.admin.get(support(self.cid, r)).content.decode())

    def test_access_ends_by_itself_when_the_time_is_up(self):
        rid = self.approved(hours=1)
        self.assertEqual(self.admin.get(support(self.cid, 'employees')).status_code, 200)
        SupportAccessRequest.objects.filter(id=rid).update(expires_at=timezone.now() - timedelta(seconds=1))
        res = self.admin.get(support(self.cid, 'employees'))
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.data['error']['code'], 'SUPPORT_ACCESS_REQUIRED')
        self.assertEqual(rows(self.ceo.get(CO_REQUESTS))[0]['status'], 'expired')

    def test_ceo_can_end_access_early(self):
        rid = self.approved()
        self.assertEqual(self.admin.get(support(self.cid, 'employees')).status_code, 200)
        res = self.ceo.post(f'{CO_REQUESTS}{rid}/revoke/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['status'], 'revoked')
        self.assertEqual(self.admin.get(support(self.cid, 'employees')).status_code, 403)

    def test_only_running_access_can_be_revoked(self):
        rid = self.ask().data['id']
        res = self.ceo.post(f'{CO_REQUESTS}{rid}/revoke/')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data['error']['code'], 'SUPPORT_NOT_ACTIVE')

    def test_a_grant_belongs_to_the_admin_who_asked(self):
        self.approved()
        other = make_admin('other@ordinis.com')
        self.assertEqual(other.get(support(self.cid, 'employees')).status_code, 403)

    def test_after_expiry_the_admin_can_ask_again(self):
        rid = self.approved(hours=1)
        SupportAccessRequest.objects.filter(id=rid).update(expires_at=timezone.now() - timedelta(minutes=1))
        self.assertEqual(self.ask().status_code, 201)


class AccessLogTests(BaseCase):
    def test_every_read_is_logged_and_the_company_can_read_the_log(self):
        self.approved()
        self.admin.get(support(self.cid, 'employees'))
        self.admin.get(support(self.cid, 'tasks'))
        self.admin.get(support(self.cid, 'departments'))
        self.assertEqual(ImpersonationLog.objects.count(), 3)
        log = rows(self.ceo.get(CO_LOG))
        self.assertEqual(len(log), 3)
        self.assertEqual({e['actor_email'] for e in log}, {'root@ordinis.com'})
        self.assertEqual({e['method'] for e in log}, {'GET'})
        self.assertTrue(any('employees' in e['endpoint'] for e in log))
        self.assertTrue(all('rows' in e['detail'] for e in log))

    def test_blocked_attempts_write_no_log_and_show_no_data(self):
        self.admin.get(support(self.cid, 'employees'))
        self.assertEqual(rows(self.ceo.get(CO_LOG)), [])

    def test_company_only_sees_its_own_log(self):
        self.approved()
        self.admin.get(support(self.cid, 'employees'))
        self.assertEqual(rows(self.beta.get(CO_LOG)), [])

    def test_the_log_cannot_be_written_or_deleted_through_the_api(self):
        self.approved()
        self.admin.get(support(self.cid, 'employees'))
        entry = rows(self.ceo.get(CO_LOG))[0]['id']
        self.assertEqual(self.ceo.post(CO_LOG, {}, format='json').status_code, 405)
        self.assertEqual(self.ceo.delete(f'{CO_LOG}{entry}/').status_code, 405)
        self.assertEqual(self.ceo.patch(f'{CO_LOG}{entry}/', {'detail': 'x'}, format='json').status_code, 405)
        self.assertEqual(self.admin.delete(f'{CO_LOG}{entry}/').status_code, 403)

    def test_log_stays_after_access_expires(self):
        rid = self.approved()
        self.admin.get(support(self.cid, 'employees'))
        SupportAccessRequest.objects.filter(id=rid).update(expires_at=timezone.now() - timedelta(minutes=1))
        self.assertEqual(len(rows(self.ceo.get(CO_LOG))), 1)
