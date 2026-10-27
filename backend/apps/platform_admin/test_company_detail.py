"""ST-152: the Platform Admin's company detail page, and a note on suspend / activate."""
import datetime

from django.utils import timezone

from billing.models import Invoice, PaymentSubmission, Subscription
from accounts.models import User
from core.test_utils import add_employee, login_as
from payroll.models import SalaryStructure
from platform_admin.models import PlatformActionLog, SupportAccessRequest, SupportTicket
from platform_admin.test_panel import COMPANIES, PanelBase


class CompanyDetailTests(PanelBase):
    @property
    def admin_user(self):
        return User.objects.get(email='root@ordinis.com')

    def url(self, company_id=None):
        return f'{COMPANIES}{company_id or self.acme_id}/'

    def detail(self, company_id=None):
        res = self.admin.get(self.url(company_id))
        self.assertEqual(res.status_code, 200, res.content)
        return res.data

    def test_identity_owner_plan_and_size(self):
        data = self.detail()
        self.assertEqual((data['name'], data['subdomain'], data['is_active']), ('Acme', 'acme', True))
        self.assertIsNotNone(data['registered_on'])
        self.assertEqual(data['owner']['email'], 'ceo@acme.com')
        self.assertIn('phone', data['owner'])
        self.assertEqual(data['subscription']['plan']['name'], 'Basic')
        self.assertIn('days_left', data['subscription'])
        self.assertIn('period_end', data['subscription'])
        self.assertEqual(data['size']['employees'], 2)       # the CEO and the one added by PanelBase
        self.assertEqual(data['size']['limit'], 10)

    def test_a_company_with_no_payments_shows_zeros(self):
        data = self.detail(self.beta_id)
        self.assertEqual(data['payments']['total'], 0)
        self.assertEqual(data['payments']['approved_amount'], 0)
        self.assertIsNone(data['payments']['last_approved_at'])
        self.assertEqual(data['tickets'], {'total': 0, 'open': 0})
        self.assertEqual(data['recent_actions'], [])
        self.assertIsNone(data['last_status_action'])

    def test_counts_of_invoices_payments_tickets_and_requests(self):
        company = self.ceo.company_id
        sub = Subscription.objects.get(company_id=company)
        today = timezone.localdate()
        first, second = today - datetime.timedelta(days=400), today - datetime.timedelta(days=300)
        Invoice.objects.create(company_id=company, subscription=sub, number='T-1', plan_name='Basic', period_start=first, period_end=first,
                               amount=1500, status=Invoice.STATUS_PAID, issued_on=today, due_on=today, kind=Invoice.KIND_PAYMENT)
        Invoice.objects.create(company_id=company, subscription=sub, number='T-2', plan_name='Basic', period_start=second, period_end=second,
                               amount=900, status=Invoice.STATUS_OPEN, issued_on=today, due_on=today, kind=Invoice.KIND_MONTHLY)
        PaymentSubmission.objects.create(company_id=company, plan=sub.plan, months=1, amount=1500, method='bkash', payer_name='Secret Payer',
                                         payer_number='01711111111', transaction_id='TXDETAIL1', kind='new', status='approved', reviewed_at=timezone.now())
        PaymentSubmission.objects.create(company_id=company, plan=sub.plan, months=1, amount=1500, method='nagad', payer_name='X',
                                         payer_number='01722222222', transaction_id='TXDETAIL2', kind='renewal', status='pending')
        SupportTicket.objects.create(company_id=company, subject='Help', status='open')
        SupportTicket.objects.create(company_id=company, subject='Done', status='resolved')
        SupportAccessRequest.objects.create(company_id=company, requested_by=self.admin_user, reason='Bug', status='pending')
        data = self.detail()
        self.assertEqual((data['invoices']['total'], data['invoices']['paid'], data['invoices']['open']), (2, 1, 1))
        self.assertEqual((float(data['invoices']['paid_amount']), float(data['invoices']['open_amount'])), (1500.0, 900.0))
        self.assertEqual((data['payments']['total'], data['payments']['approved'], data['payments']['pending']), (2, 1, 1))
        self.assertEqual(data['tickets'], {'total': 2, 'open': 1})
        self.assertEqual((data['access_requests']['pending'], data['access_requests']['active']), (1, 0))
        self.assertNotIn('Secret Payer', str(data))
        self.assertNotIn('01711111111', str(data))

    def test_suspend_with_a_note_shows_status_and_the_action(self):
        res = self.admin.post(f'{self.url()}suspend/', {'note': 'Payment overdue'}, format='json')
        self.assertEqual(res.status_code, 200)
        data = self.detail()
        self.assertFalse(data['is_active'])
        self.assertEqual(data['last_status_action']['action'], 'suspend')
        self.assertEqual(data['last_status_action']['note'], 'Payment overdue')
        self.assertEqual(data['recent_actions'][0]['note'], 'Payment overdue')
        self.admin.post(f'{self.url()}activate/', {'note': 'Paid in full today'}, format='json')
        data = self.detail()
        self.assertTrue(data['is_active'])
        self.assertEqual((data['last_status_action']['action'], data['last_status_action']['note']), ('activate', 'Paid in full today'))

    def test_the_note_is_required_and_capped(self):
        self.assertEqual(self.admin.post(f'{self.url()}suspend/', {'note': 'x' * 255}, format='json').status_code, 200)
        self.assertEqual(self.admin.post(f'{self.url()}activate/', {'note': 'x' * 256}, format='json').status_code, 400)
        self.assertEqual(len(PlatformActionLog.objects.filter(action='suspend').first().note), 255)

    def test_recent_actions_are_the_last_ten_of_this_company_only(self):
        for i in range(12):
            PlatformActionLog.objects.create(actor=self.admin_user, company_id=self.ceo.company_id, company_name='Acme', action='resolve_ticket', note=f'n{i}')
        PlatformActionLog.objects.create(actor=self.admin_user, company_id=self.beta.company_id, company_name='Beta', action='suspend', note='other')
        actions = self.detail()['recent_actions']
        self.assertEqual(len(actions), 10)
        self.assertNotIn('other', [a['note'] for a in actions])
        self.assertEqual(actions[0]['note'], 'n11')

    def test_no_employee_level_data_is_returned(self):
        emp = add_employee(self.ceo, 'secret.person@acme.com', 'A-9', full_name='Zainab Secretperson')
        SalaryStructure.objects.create(company_id=self.ceo.company_id, employee_id=emp['id'], base_salary=987654)
        body = str(self.detail())
        for forbidden in ('Zainab', 'Secretperson', 'secret.person', '987654', 'salary', 'emp@acme.com'):
            self.assertNotIn(forbidden, body, forbidden)
        self.assertEqual(set(self.detail()) & {'employees', 'tasks', 'attendance', 'salaries'}, set())

    def test_the_company_side_cannot_open_it(self):
        for client in (self.ceo, login_as('emp@acme.com')):
            self.assertEqual(client.get(self.url()).status_code, 403)
            self.assertEqual(client.get(self.url(self.beta_id)).status_code, 403)

    def test_an_unknown_company_is_a_404(self):
        self.assertEqual(self.admin.get(self.url('00000000-0000-0000-0000-000000000000')).status_code, 404)

    def test_query_count_does_not_grow_with_the_data(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as before:
            self.detail()
        for i in range(6):
            SupportTicket.objects.create(company_id=self.ceo.company_id, subject=f't{i}')
            PlatformActionLog.objects.create(actor=self.admin_user, company_id=self.ceo.company_id, company_name='Acme', action='resolve_ticket')
        with CaptureQueriesContext(connection) as after:
            self.detail()
        self.assertEqual(len(before), len(after))
