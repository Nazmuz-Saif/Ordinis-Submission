"""ST-153: the Platform Admin dashboard summary."""
import datetime
from decimal import Decimal

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from billing import services as billing_services
from billing.models import Invoice, PaymentSubmission, Subscription
from accounts.models import User
from billing.test_payments import body, make_admin
from core.test_utils import register_company
from platform_admin.models import SupportAccessRequest, SupportTicket
from platform_admin.test_panel import ADMIN, PanelBase
from tenants.models import Company

SUMMARY = ADMIN + 'summary/'


def put_state(company_id, status=Subscription.STATUS_ACTIVE, days=100):
    end = timezone.localdate() + datetime.timedelta(days=days)
    Subscription.objects.filter(company_id=company_id).update(
        status=status, current_period_end=end, current_period_start=end - datetime.timedelta(days=30),
    )


def paid_invoice(company_id, amount, paid_on, number):
    sub = Subscription.objects.get(company_id=company_id)
    start = paid_on - datetime.timedelta(days=int(number[1:]))
    return Invoice.objects.create(
        company_id=company_id, subscription=sub, number=number, plan_name='Basic', period_start=start, period_end=start,
        amount=amount, status=Invoice.STATUS_PAID, issued_on=paid_on, due_on=paid_on, paid_on=paid_on, kind=Invoice.KIND_PAYMENT,
    )


class SummaryTests(PanelBase):
    @property
    def admin_user(self):
        return User.objects.get(email='root@ordinis.com')

    def get(self):
        res = self.admin.get(SUMMARY)
        self.assertEqual(res.status_code, 200, res.content)
        return res.data

    def test_an_empty_platform_is_all_zeros(self):
        Company.objects.all().delete()
        data = self.get()
        self.assertEqual(data['companies'], {'total': 0, 'active': 0, 'restricted': 0, 'suspended': 0})
        self.assertEqual((data['revenue']['this_month'], data['revenue']['all_time'], data['due']['amount']), (0, 0, 0))
        self.assertEqual(len(data['revenue_by_month']), 6)
        self.assertTrue(all(m['revenue'] == 0 for m in data['revenue_by_month']))
        self.assertTrue(all(a['count'] == 0 for a in data['attention']))

    def test_companies_are_counted_by_state(self):
        gamma = register_company('Gamma', 'gamma', 'ceo@gamma.com')
        delta = register_company('Delta', 'delta', 'ceo@delta.com')
        put_state(self.acme_id)                                                      # active
        put_state(self.beta_id, Subscription.STATUS_PENDING_PAYMENT)                 # restricted
        put_state(gamma.company_id, Subscription.STATUS_EXPIRED, days=-40)           # restricted
        put_state(delta.company_id)
        Company.objects.filter(pk=delta.company_id).update(is_active=False)          # suspended wins over its plan state
        data = self.get()['companies']
        self.assertEqual(data, {'total': 4, 'active': 1, 'restricted': 2, 'suspended': 1})

    def test_a_company_in_its_grace_days_still_counts_as_active(self):
        put_state(self.acme_id, days=-2)
        put_state(self.beta_id)
        self.assertEqual(self.get()['companies']['active'], 2)

    def test_revenue_and_dues_come_from_the_invoices(self):
        today = timezone.localdate()
        put_state(self.acme_id)
        put_state(self.beta_id)
        Invoice.objects.filter(company_id__in=[self.acme_id, self.beta_id]).delete()
        paid_invoice(self.acme_id, '1500.00', today, 'P1')
        paid_invoice(self.beta_id, '5000.00', today, 'P2')
        old = today.replace(day=1) - datetime.timedelta(days=1)         # the last day of last month
        paid_invoice(self.acme_id, '3000.00', old, 'P3')
        paid_invoice(self.acme_id, '700.00', today.replace(year=today.year - 1), 'P4')             # a year ago: all time only
        sub = Subscription.objects.get(company_id=self.acme_id)
        Invoice.objects.create(company_id=self.acme_id, subscription=sub, number='O1', plan_name='Basic', period_start=today, period_end=today,
                               amount=900, status=Invoice.STATUS_OPEN, issued_on=today, due_on=today, kind=Invoice.KIND_RENEWAL)
        Invoice.objects.create(company_id=self.acme_id, subscription=sub, number='V1', plan_name='Basic', period_start=today - datetime.timedelta(days=9),
                               period_end=today, amount=111, status=Invoice.STATUS_VOID, issued_on=today, due_on=today, kind=Invoice.KIND_RENEWAL)
        data = self.get()
        self.assertEqual(Decimal(str(data['revenue']['this_month'])), Decimal('6500'))
        self.assertEqual(Decimal(str(data['revenue']['all_time'])), Decimal('10200'))
        self.assertEqual((Decimal(str(data['due']['amount'])), data['due']['count']), (Decimal('900'), 1))
        by_month = data['revenue_by_month']
        self.assertEqual(Decimal(str(by_month[-1]['revenue'])), Decimal('6500'))
        self.assertEqual(Decimal(str(by_month[-2]['revenue'])), Decimal('3000'))
        self.assertEqual(by_month[-1]['month'], today.replace(day=1).isoformat())

    def test_subscriptions_ending_matches_the_subscriptions_page(self):
        put_state(self.acme_id, days=3)
        put_state(self.beta_id, days=40)
        data = self.get()
        self.assertEqual(data['subscriptions_ending'], 1)
        self.assertEqual(data['subscriptions_ending'], len(billing_services.admin_subscription_rows('expiring')))

    def test_attention_counts(self):
        SupportTicket.objects.create(company_id=self.cid, subject='a')
        SupportTicket.objects.create(company_id=self.cid, subject='b')
        SupportTicket.objects.create(company_id=self.cid, subject='c', status='resolved')
        SupportAccessRequest.objects.create(company_id=self.cid, requested_by=self.admin_user, reason='r')
        sub = Subscription.objects.get(company_id=self.cid)
        PaymentSubmission.objects.create(company_id=self.cid, plan=sub.plan, months=1, amount=1500, method='bkash', payer_name='P',
                                         payer_number='017', transaction_id='TXSUM00001', kind='renewal', status='pending')
        data = self.get()
        self.assertEqual((data['open_tickets'], data['pending_access_requests'], data['pending_payments']), (2, 1, 1))
        self.assertEqual({a['key']: a['count'] for a in data['attention']}, {
            'pending_payments': 1, 'subscriptions_ending': data['subscriptions_ending'], 'open_tickets': 2, 'pending_access_requests': 1,
        })

    def test_approving_a_payment_lowers_pending_and_raises_revenue(self):
        put_state(self.acme_id, days=20)
        before = self.get()
        res = self.ceo.post('/api/v1/billing/payments/', body(plan='Basic', months=1), format='json')
        self.assertEqual(res.status_code, 201, res.content)
        mid = self.get()
        self.assertEqual(mid['pending_payments'], before['pending_payments'] + 1)
        amount = Decimal(str(PaymentSubmission.objects.get(pk=res.data['id']).amount))
        make_admin().post(f'{ADMIN}payments/{res.data["id"]}/approve/')
        after = self.get()
        self.assertEqual(after['pending_payments'], before['pending_payments'])
        self.assertEqual(Decimal(str(after['revenue']['all_time'])) - Decimal(str(before['revenue']['all_time'])), amount)
        self.assertEqual(Decimal(str(after['revenue']['this_month'])) - Decimal(str(before['revenue']['this_month'])), amount)

    def test_only_a_platform_admin_can_call_it(self):
        self.assertEqual(self.ceo.get(SUMMARY).status_code, 403)
        self.assertEqual(self.emp_c.get(SUMMARY).status_code, 403)
        from rest_framework.test import APIClient
        self.assertEqual(APIClient().get(SUMMARY).status_code, 401)

    def test_query_count_does_not_grow_with_the_number_of_companies(self):
        with CaptureQueriesContext(connection) as few:
            self.get()
        for i in range(5):
            register_company(f'Extra {i}', f'extra-{i}', f'ceo@extra{i}.com')
        with CaptureQueriesContext(connection) as many:
            self.get()
        self.assertEqual(len(few), len(many))

    def test_no_company_names_or_people_in_the_answer(self):
        body_text = str(self.get())
        for text in ('Acme', 'Beta', 'ceo@acme.com', 'emp@acme.com'):
            self.assertNotIn(text, body_text)
