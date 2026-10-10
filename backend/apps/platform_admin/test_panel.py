from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

from core.test_utils import add_employee, give_role, login_as, register_company, rows
from payroll.models import SalaryStructure
from platform_admin.models import PlatformActionLog, SupportAccessRequest, SupportTicket
from platform_admin.tests import BaseCase

ADMIN = '/api/v1/platform-admin/admin/'
COMPANIES = ADMIN + 'companies/'
TICKETS = ADMIN + 'tickets/'
CO_TICKETS = '/api/v1/platform-admin/company/tickets/'
LOGIN = '/api/v1/auth/login/'


def try_login(email, password='StrongPass123'):
    return APIClient().post(LOGIN, {'email': email, 'password': password}, format='json')


class PanelBase(BaseCase):
    def setUp(self):
        super().setUp()
        self.acme_id = str(self.cid)
        self.beta_id = str(self.beta.company_id)
        self.emp = add_employee(self.ceo, 'emp@acme.com', 'A-2')
        self.emp_c = login_as('emp@acme.com')

    def company(self, company_id):
        return {c['id']: c for c in rows(self.admin.get(COMPANIES))}[company_id]


class AdminOnlyTests(PanelBase):
    ENDPOINTS = [COMPANIES, TICKETS, ADMIN + 'access-requests/', ADMIN + 'actions/']

    def test_ceo_and_employees_are_blocked_everywhere(self):
        for client in (self.ceo, self.emp_c):
            for url in self.ENDPOINTS:
                self.assertEqual(client.get(url).status_code, 403, url)
            self.assertEqual(client.post(f'{COMPANIES}{self.beta_id}/suspend/').status_code, 403)
            self.assertEqual(client.post(f'{COMPANIES}{self.beta_id}/activate/').status_code, 403)
        self.assertTrue(self.company(self.beta_id)['is_active'])

    def test_anonymous_is_blocked(self):
        for url in self.ENDPOINTS:
            self.assertIn(APIClient().get(url).status_code, (401, 403), url)

    def test_platform_admin_is_allowed(self):
        for url in self.ENDPOINTS:
            self.assertEqual(self.admin.get(url).status_code, 200, url)


class CompanyListTests(PanelBase):
    def test_lists_every_company_with_counts_of_our_own_objects(self):
        self.ask()                                                    # one pending request on Acme
        self.emp_c.post(CO_TICKETS, {'subject': 'Cannot login'}, format='json')
        listed = rows(self.admin.get(COMPANIES))
        self.assertEqual([c['name'] for c in listed], ['Acme', 'Beta'])
        acme, beta = self.company(self.acme_id), self.company(self.beta_id)
        self.assertEqual((acme['open_tickets'], acme['pending_requests']), (1, 1))
        self.assertEqual((beta['open_tickets'], beta['pending_requests']), (0, 0))
        self.assertTrue(acme['is_active'])

    def test_the_panel_shows_no_employee_task_or_salary_data(self):
        SalaryStructure.objects.create(company_id=self.cid, employee_id=self.ceo.employee_id, base_salary=424242)
        body = ''.join(
            self.admin.get(url).content.decode()
            for url in (COMPANIES, TICKETS, ADMIN + 'access-requests/', ADMIN + 'actions/')
        )
        for secret in ('ceo@acme.com', 'emp@acme.com', 'ceo@beta.com', 'A-2', 'Acme task', 'Acme Engineering', '424242', 'salary'):
            self.assertNotIn(secret, body)
        self.assertEqual(
            set(self.admin.get(COMPANIES).data['data'][0]),
            {'id', 'name', 'subdomain', 'industry', 'is_active', 'created_at', 'open_tickets', 'pending_requests'},
        )

    def test_the_list_is_read_only(self):
        self.assertEqual(self.admin.post(COMPANIES, {'name': 'x'}, format='json').status_code, 405)
        self.assertIn(self.admin.delete(f'{COMPANIES}{self.acme_id}/').status_code, (404, 405))  # no such route
        self.assertEqual(len(rows(self.admin.get(COMPANIES))), 2)                                  # nothing was deleted


class SuspendActivateTests(PanelBase):
    def test_suspended_company_users_cannot_log_in(self):
        self.assertEqual(try_login('ceo@beta.com').status_code, 200)
        res = self.admin.post(f'{COMPANIES}{self.beta_id}/suspend/')
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data['is_active'])
        denied = try_login('ceo@beta.com')
        self.assertNotEqual(denied.status_code, 200)
        self.assertIn('suspended', denied.content.decode())
        self.assertNotIn('access', denied.data)

    def test_a_token_issued_before_the_suspension_stops_working(self):
        self.admin.post(f'{COMPANIES}{self.beta_id}/suspend/')
        self.assertEqual(self.beta.get('/api/v1/organization/departments/').status_code, 403)
        self.assertEqual(self.beta.get('/api/v1/dashboard/summary/').status_code, 403)

    def test_other_companies_are_not_affected(self):
        self.admin.post(f'{COMPANIES}{self.beta_id}/suspend/')
        self.assertEqual(try_login('ceo@acme.com').status_code, 200)
        self.assertEqual(self.ceo.get('/api/v1/organization/departments/').status_code, 200)

    def test_activating_lets_everyone_back_in(self):
        self.admin.post(f'{COMPANIES}{self.beta_id}/suspend/')
        res = self.admin.post(f'{COMPANIES}{self.beta_id}/activate/')
        self.assertTrue(res.data['is_active'])
        self.assertEqual(try_login('ceo@beta.com').status_code, 200)
        self.assertEqual(self.beta.get('/api/v1/organization/departments/').status_code, 200)

    def test_data_is_kept_while_suspended(self):
        self.admin.post(f'{COMPANIES}{self.acme_id}/suspend/')
        self.admin.post(f'{COMPANIES}{self.acme_id}/activate/')
        self.assertEqual(len(rows(self.ceo.get('/api/v1/organization/departments/'))), 1)

    def test_repeating_the_same_action_changes_nothing_and_logs_once(self):
        for _ in range(3):
            self.assertEqual(self.admin.post(f'{COMPANIES}{self.beta_id}/suspend/').status_code, 200)
        self.assertEqual(PlatformActionLog.objects.filter(action='suspend').count(), 1)
        self.assertEqual(self.admin.post(f'{COMPANIES}{self.acme_id}/activate/').status_code, 200)
        self.assertEqual(PlatformActionLog.objects.filter(action='activate').count(), 0)

    def test_every_change_is_logged_with_who_and_which_company(self):
        self.admin.post(f'{COMPANIES}{self.beta_id}/suspend/')
        self.admin.post(f'{COMPANIES}{self.beta_id}/activate/')
        log = rows(self.admin.get(ADMIN + 'actions/'))
        self.assertEqual([e['action'] for e in log], ['activate', 'suspend'])
        self.assertEqual({e['company_name'] for e in log}, {'Beta'})
        self.assertEqual({e['actor_email'] for e in log}, {'root@ordinis.com'})

    def test_unknown_company_is_404(self):
        res = self.admin.post(f'{COMPANIES}00000000-0000-0000-0000-000000000000/suspend/')
        self.assertEqual(res.status_code, 404)

    def test_the_action_log_cannot_be_written(self):
        self.assertEqual(self.admin.post(ADMIN + 'actions/', {}, format='json').status_code, 405)


class TicketTests(PanelBase):
    def test_an_employee_raises_a_ticket_for_their_own_company(self):
        res = self.emp_c.post(CO_TICKETS, {'subject': 'Report is empty', 'description': 'Open Tasks, nothing shows'}, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['status'], 'open')
        self.assertEqual(res.data['company_name'], 'Acme')
        self.assertEqual(res.data['created_by_email'], 'emp@acme.com')

    def test_a_subject_is_required(self):
        for body in ({}, {'subject': ''}, {'subject': '   '}):
            self.assertEqual(self.emp_c.post(CO_TICKETS, body, format='json').status_code, 400, body)
        self.assertEqual(SupportTicket.objects.count(), 0)

    def test_company_status_and_author_cannot_be_chosen_by_the_client(self):
        res = self.emp_c.post(CO_TICKETS, {
            'subject': 'x', 'company': self.beta_id, 'status': 'resolved', 'created_by_email': 'ceo@beta.com'}, format='json')
        ticket = SupportTicket.objects.get()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(str(ticket.company_id), self.acme_id)
        self.assertEqual(ticket.status, 'open')

    def test_employees_see_only_their_own_tickets_the_ceo_sees_the_company(self):
        self.emp_c.post(CO_TICKETS, {'subject': 'mine'}, format='json')
        add_employee(self.ceo, 'other@acme.com', 'A-3')
        other_c = login_as('other@acme.com')
        other_c.post(CO_TICKETS, {'subject': 'theirs'}, format='json')
        self.assertEqual([t['subject'] for t in rows(self.emp_c.get(CO_TICKETS))], ['mine'])
        self.assertEqual({t['subject'] for t in rows(self.ceo.get(CO_TICKETS))}, {'mine', 'theirs'})
        self.assertEqual(rows(self.beta.get(CO_TICKETS)), [])

    def test_another_companys_ticket_is_a_404(self):
        tid = self.emp_c.post(CO_TICKETS, {'subject': 'mine'}, format='json').data['id']
        self.assertEqual(self.beta.get(f'{CO_TICKETS}{tid}/').status_code, 404)
        self.assertEqual(self.emp_c.get(f'{CO_TICKETS}{tid}/').status_code, 200)

    def test_a_suspended_company_cannot_raise_tickets(self):
        self.admin.post(f'{COMPANIES}{self.acme_id}/suspend/')
        self.assertEqual(self.emp_c.post(CO_TICKETS, {'subject': 'x'}, format='json').status_code, 403)

    def test_admin_sees_tickets_of_all_companies_and_can_filter(self):
        self.emp_c.post(CO_TICKETS, {'subject': 'acme problem'}, format='json')
        self.beta.post(CO_TICKETS, {'subject': 'beta problem'}, format='json')
        listed = rows(self.admin.get(TICKETS))
        self.assertEqual({t['company_name'] for t in listed}, {'Acme', 'Beta'})
        tid = [t['id'] for t in listed if t['subject'] == 'beta problem'][0]
        self.admin.post(f'{TICKETS}{tid}/resolve/')
        self.assertEqual([t['subject'] for t in rows(self.admin.get(TICKETS + '?status=open'))], ['acme problem'])
        self.assertEqual([t['subject'] for t in rows(self.admin.get(TICKETS + '?status=resolved'))], ['beta problem'])

    def test_resolve_and_reopen(self):
        tid = self.emp_c.post(CO_TICKETS, {'subject': 'x'}, format='json').data['id']
        done = self.admin.post(f'{TICKETS}{tid}/resolve/')
        self.assertEqual(done.data['status'], 'resolved')
        self.assertIsNotNone(done.data['resolved_at'])
        self.admin.post(f'{TICKETS}{tid}/resolve/')                                  # again: nothing new
        self.assertEqual(PlatformActionLog.objects.filter(action='resolve_ticket').count(), 1)
        back = self.admin.post(f'{TICKETS}{tid}/reopen/')
        self.assertEqual(back.data['status'], 'open')
        self.assertIsNone(back.data['resolved_at'])

    def test_a_company_cannot_resolve_its_own_ticket(self):
        tid = self.emp_c.post(CO_TICKETS, {'subject': 'x'}, format='json').data['id']
        self.assertEqual(self.ceo.post(f'{TICKETS}{tid}/resolve/').status_code, 403)
        self.assertEqual(SupportTicket.objects.get(id=tid).status, 'open')


class AdminRequestListTests(PanelBase):
    def test_admin_sees_every_request_on_the_platform(self):
        from platform_admin.tests import make_admin
        other = make_admin('other@ordinis.com')
        self.ask()
        self.ask(admin=other, company=self.beta_id)
        listed = rows(self.admin.get(ADMIN + 'access-requests/'))
        self.assertEqual({(r['company_name'], r['requested_by_email']) for r in listed},
                         {('Acme', 'root@ordinis.com'), ('Beta', 'other@ordinis.com')})

    def test_expired_status_shows_in_the_panel(self):
        rid = self.approved(hours=1)
        SupportAccessRequest.objects.filter(id=rid).update(expires_at=timezone.now() - timedelta(minutes=1))
        self.assertEqual(rows(self.admin.get(ADMIN + 'access-requests/'))[0]['status'], 'expired')

    def test_it_is_read_only(self):
        self.assertEqual(self.admin.post(ADMIN + 'access-requests/', {}, format='json').status_code, 405)
