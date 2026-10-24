"""ST-146: price rules, the quote, manual payment submission, and approval or rejection by the platform team."""
import datetime
from decimal import Decimal
from unittest import mock

from django.test import TestCase

from accounts.models import User
from audit_log.models import AuditLog
from billing import services
from billing.models import Invoice, PaymentSubmission, Subscription
from billing.test_subscription import at, end_on, sub_of
from core.test_utils import add_employee, give_role, login_as, register_company, rows
from notifications.models import Notification
from platform_admin.models import PlatformActionLog

D = datetime.date
QUOTE = '/api/v1/billing/quote/'
PAYMENTS = '/api/v1/billing/payments/'
ADMIN = '/api/v1/platform-admin/admin/payments/'
TODAY = D(2026, 11, 10)


def body(**over):
    data = {'plan': 'Basic', 'months': 3, 'method': 'bkash', 'payer_name': 'Rahim Uddin',
            'payer_number': '01712345678', 'transaction_id': 'TX1234ABCD'}
    data.update(over)
    return data


def code(res):
    return (res.data.get('error') or {}).get('code') if isinstance(res.data, dict) else None


def make_admin():
    User.objects.create_user(email='root@x.com', password='StrongPass123', is_platform_admin=True)
    return login_as('root@x.com')


def wait_for_payment(subdomain):
    Subscription.objects.filter(company__subdomain=subdomain).update(status=Subscription.STATUS_PENDING_PAYMENT)


def waiting_company(subdomain, email, people=()):
    """A company that registered but has not paid yet (restricted, pending_payment). `people` are added first,
    because a restricted company cannot add anybody."""
    ceo = register_company(subdomain.upper(), subdomain, email)
    for person_email, person_code in people:
        add_employee(ceo, person_email, person_code)
    wait_for_payment(subdomain)
    return login_as(email)


class PriceRuleTests(TestCase):
    def setUp(self):
        self.ceo = register_company('Q Co', 'q-co', 'ceo@q.com')

    def quote(self, plan='Basic', months=1):
        return self.ceo.get(QUOTE, {'plan': plan, 'months': months})

    def wait(self):
        wait_for_payment('q-co')

    def test_price_is_monthly_price_times_months_with_two_free_months_per_full_year(self):
        self.wait()
        cases = {1: ('1500.00', '0.00'), 3: ('4500.00', '0.00'), 6: ('9000.00', '0.00'),
                 11: ('16500.00', '0.00'), 12: ('15000.00', '3000.00'),
                 13: ('16500.00', '3000.00'), 24: ('30000.00', '6000.00'), 36: ('45000.00', '9000.00')}
        for months, (amount, discount) in cases.items():
            data = self.quote(months=months).data['data']
            self.assertEqual((str(data['amount']), str(data['discount'])), (amount, discount), months)
            self.assertEqual(data['gross'] - data['discount'], data['amount'])

    def test_twelve_months_cost_the_price_of_ten(self):
        self.wait()
        data = self.quote('Professional', 12).data['data']
        self.assertEqual(data['amount'], Decimal('5000.00') * 10)
        self.assertEqual(data['free_months'], 2)

    def test_the_quote_has_the_period_the_kind_and_the_plan(self):
        self.wait()
        with at(TODAY):
            data = self.quote('Professional', 3).data['data']
        self.assertEqual(data['kind'], 'new')
        self.assertEqual((data['period_start'], data['period_end']), (TODAY, D(2027, 2, 9)))
        self.assertEqual((data['plan']['name'], data['currency'], data['months']), ('Professional', 'BDT', 3))

    def test_months_outside_1_to_36_or_not_a_whole_number_are_refused(self):
        self.wait()
        for months, expected in [(40, 'MONTHS_OUT_OF_RANGE'), (37, 'MONTHS_OUT_OF_RANGE'), (0, 'MONTHS_OUT_OF_RANGE'),
                                 (-3, 'MONTHS_OUT_OF_RANGE'), ('abc', 'MONTHS_INVALID'), ('2.5', 'MONTHS_INVALID'), ('', 'MONTHS_INVALID')]:
            res = self.quote(months=months)
            self.assertEqual((res.status_code, code(res)), (400, expected), months)
        for months in (1, 36):
            self.assertEqual(self.quote(months=months).status_code, 200)

    def test_an_unknown_plan_is_refused_and_a_plan_may_be_given_by_id(self):
        self.wait()
        self.assertEqual(code(self.quote('Platinum', 3)), 'PLAN_NOT_FOUND')
        plan_id = self.ceo.get('/api/v1/billing/plans/').data[0]['id']
        self.assertEqual(self.quote(plan_id, 3).status_code, 200)

    def test_the_quote_saves_nothing(self):
        self.wait()
        self.quote('Professional', 12)
        self.assertEqual(PaymentSubmission.objects.count(), 0)
        self.assertEqual(Invoice.objects.count(), 0)

    def test_a_plan_too_small_for_the_team_is_refused(self):
        services.change_plan(sub_of('q-co').company, 'Professional')
        for n in range(10):
            add_employee(self.ceo, f'e{n}@q.com', f'Q-{n}')           # 11 people with the CEO
        self.wait()
        res = self.quote('Basic', 3)
        self.assertEqual((res.status_code, code(res)), (400, 'PLAN_TOO_SMALL'))
        self.assertEqual(self.quote('Professional', 3).status_code, 200)

    def test_a_running_plan_cannot_be_switched_by_a_renewal(self):
        res = self.quote('Professional', 3)
        self.assertEqual((res.status_code, code(res)), (400, 'PLAN_CHANGE_NOT_VIA_RENEWAL'))
        self.assertEqual(self.quote('Basic', 3).status_code, 200)

    def test_a_renewal_of_a_running_plan_starts_the_day_after_the_end(self):
        with at(TODAY):
            end_on('q-co', D(2026, 11, 20))
            data = self.quote('Basic', 1).data['data']
        self.assertEqual((data['kind'], data['period_start'], data['period_end']), ('renewal', D(2026, 11, 21), D(2026, 12, 20)))

    def test_an_expired_company_starts_today_and_may_choose_another_plan(self):
        with at(TODAY):
            end_on('q-co', D(2026, 10, 1), status=Subscription.STATUS_EXPIRED)
            data = self.quote('Professional', 1).data['data']
        self.assertEqual((data['kind'], data['period_start']), ('renewal', TODAY))

    def test_a_plain_employee_without_view_billing_cannot_quote(self):
        add_employee(self.ceo, 'plain@q.com', 'Q-2')
        self.assertEqual(login_as('plain@q.com').get(QUOTE, {'plan': 'Basic', 'months': 1}).status_code, 403)


class SubmitPaymentTests(TestCase):
    def setUp(self):
        self.ceo = waiting_company('s-co', 'ceo@s.com', people=[('view@s.com', 'S-2'), ('plain@s.com', 'S-3'), ('pay@s.com', 'S-4')])

    def submit(self, client=None, **over):
        return (client or self.ceo).post(PAYMENTS, body(**over), format='json')

    def test_a_submission_is_saved_pending_with_the_servers_amount(self):
        res = self.submit()
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual((res.data['status'], res.data['kind'], str(res.data['amount'])), ('pending', 'new', '4500.00'))
        payment = PaymentSubmission.objects.get()
        self.assertEqual((payment.method, payment.months, payment.plan.name, payment.transaction_id), ('bkash', 3, 'Basic', 'TX1234ABCD'))
        self.assertEqual(payment.submitted_by.user.email, 'ceo@s.com')
        self.assertEqual(res.data['submitted_by_email'], 'ceo@s.com')

    def test_a_tampered_amount_is_refused_and_nothing_is_saved(self):
        for amount in ('1', '4499.99', '99999'):
            res = self.submit(amount=amount)
            self.assertEqual((res.status_code, code(res)), (400, 'PAYMENT_AMOUNT_MISMATCH'), amount)
        self.assertEqual(PaymentSubmission.objects.count(), 0)
        self.assertEqual(self.submit(amount='4500.00').status_code, 201)       # the amount the person saw is fine

    def test_the_client_cannot_set_status_kind_company_or_reviewer(self):
        other = register_company('Other', 'other', 'ceo@other.com')
        res = self.submit(status='approved', kind='upgrade', company=other.company_id, review_note='x',
                          reviewed_by='root', period_end='2099-01-01')
        self.assertEqual(res.status_code, 201, res.content)
        payment = PaymentSubmission.objects.get()
        self.assertEqual((payment.status, payment.kind, str(payment.company_id), payment.review_note), ('pending', 'new', self.ceo_company_id(), ''))
        self.assertIsNone(payment.period_end)
        self.assertIsNone(payment.invoice)

    def employee_id(self, code_):
        from organization.models import Employee
        return Employee.objects.get(company__subdomain='s-co', employee_code=code_).id

    def ceo_company_id(self):
        return str(Subscription.objects.get(company__subdomain='s-co').company_id)

    def test_a_transaction_id_can_be_used_once_per_method(self):
        self.assertEqual(self.submit().status_code, 201)
        other = waiting_company('t-co', 'ceo@t.com')
        res = self.submit(other)                                      # another company, same method and id
        self.assertEqual((res.status_code, code(res)), (400, 'PAYMENT_TRANSACTION_USED'))
        self.assertIn('transaction_id', res.data['error']['field_errors'])
        res = self.submit(other, transaction_id=' tx1234 abcd ')      # the same id typed differently
        self.assertEqual(code(res), 'PAYMENT_TRANSACTION_USED')
        self.assertEqual(self.submit(other, method='nagad').status_code, 201)   # another method may reuse the id

    def test_one_pending_submission_per_company(self):
        self.assertEqual(self.submit().status_code, 201)
        res = self.submit(transaction_id='SECOND12345')
        self.assertEqual((res.status_code, code(res)), (400, 'PAYMENT_ALREADY_PENDING'))
        self.assertEqual(PaymentSubmission.objects.count(), 1)

    def test_a_rejected_submission_frees_the_slot_and_the_transaction_id(self):
        admin = make_admin()
        pid = self.submit().data['id']
        admin.post(f'{ADMIN}{pid}/reject/', {'note': 'Amount is short.'}, format='json')
        res = self.submit()                                           # same data again after the rejection
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(PaymentSubmission.objects.count(), 2)

    def test_bad_input_is_refused_with_a_code_and_a_field(self):
        cases = [({'method': 'paypal'}, 'PAYMENT_METHOD_INVALID', 'method'), ({'transaction_id': 'ab'}, 'TRANSACTION_ID_INVALID', 'transaction_id'),
                 ({'transaction_id': 'bad id!'}, 'TRANSACTION_ID_INVALID', 'transaction_id'), ({'payer_name': ' '}, 'PAYER_NAME_INVALID', 'payer_name'),
                 ({'payer_number': 'abc'}, 'PAYER_NUMBER_INVALID', 'payer_number'), ({'months': 40}, 'MONTHS_OUT_OF_RANGE', None),
                 ({'plan': 'Nope'}, 'PLAN_NOT_FOUND', None)]
        for over, expected, field in cases:
            res = self.submit(**over)
            self.assertEqual((res.status_code, code(res)), (400, expected), over)
            if field:
                self.assertIn(field, res.data['error']['field_errors'])
        self.assertEqual(PaymentSubmission.objects.count(), 0)
        self.assertEqual(self.ceo.post(PAYMENTS, {}, format='json').status_code, 400)

    def test_only_manage_billing_can_submit_and_read(self):
        company_id = Subscription.objects.get(company__subdomain='s-co').company_id
        give_role(company_id, self.employee_id('S-2'), ['view_billing'], 'Viewer')
        for email in ('view@s.com', 'plain@s.com'):
            client = login_as(email)
            self.assertEqual(client.post(PAYMENTS, body(), format='json').status_code, 403, email)
            self.assertEqual(client.get(PAYMENTS).status_code, 403, email)
        give_role(company_id, self.employee_id('S-4'), ['manage_billing'], 'Payer')
        self.assertEqual(login_as('pay@s.com').post(PAYMENTS, body(), format='json').status_code, 201)

    def test_a_company_sees_only_its_own_payments(self):
        self.submit()
        other = waiting_company('u-co', 'ceo@u.com')
        self.submit(other, transaction_id='OTHERPAY123')
        mine = rows(self.ceo.get(PAYMENTS))
        self.assertEqual([p['transaction_id'] for p in mine], ['TX1234ABCD'])
        other_id = PaymentSubmission.objects.get(transaction_id='OTHERPAY123').id
        self.assertEqual(self.ceo.get(f'{PAYMENTS}{other_id}/').status_code, 404)

    def test_a_restricted_company_can_quote_submit_and_list_but_nothing_else(self):
        self.assertEqual(self.ceo.get(QUOTE, {'plan': 'Basic', 'months': 1}).status_code, 200)
        self.assertEqual(self.submit().status_code, 201)
        self.assertEqual(self.ceo.get(PAYMENTS).status_code, 200)
        self.assertEqual(code(self.ceo.get('/api/v1/organization/departments/')), 'SUBSCRIPTION_RESTRICTED')


class ApprovalTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.ceo = waiting_company('a-co', 'ceo@a.com', people=[('bill@a.com', 'A-2')])

    def pay(self, client=None, **over):
        res = (client or self.ceo).post(PAYMENTS, body(**over), format='json')
        assert res.status_code == 201, res.content
        return res.data['id']

    def approve(self, pid, today=TODAY):
        with at(today):
            return self.admin.post(f'{ADMIN}{pid}/approve/', {}, format='json')

    def test_approving_a_first_payment_starts_the_plan_and_writes_the_paid_invoice(self):
        pid = self.pay(plan='Professional', months=3, transaction_id='FIRSTPAY01')
        res = self.approve(pid)
        self.assertEqual(res.status_code, 200, res.content)
        sub = sub_of('a-co')
        self.assertEqual((sub.status, sub.plan.name, sub.current_period_start, sub.current_period_end, sub.billing_months),
                         ('active', 'Professional', TODAY, D(2027, 2, 9), 3))
        self.assertEqual(sub.started_on, TODAY)
        invoice = Invoice.objects.get()
        self.assertEqual((invoice.number, invoice.status, invoice.amount, invoice.plan_name), ('INV-2026-00001', 'paid', Decimal('15000.00'), 'Professional'))
        self.assertEqual((invoice.period_start, invoice.period_end, invoice.paid_on, invoice.issued_on), (TODAY, D(2027, 2, 9), TODAY, TODAY))
        self.assertEqual((invoice.payment_method, invoice.transaction_id), ('bkash', 'FIRSTPAY01'))
        payment = PaymentSubmission.objects.get()
        self.assertEqual((payment.status, payment.invoice_id, payment.period_end), ('approved', invoice.id, D(2027, 2, 9)))
        self.assertEqual(payment.reviewed_by.email, 'root@x.com')
        self.assertIsNotNone(payment.reviewed_at)
        data = res.data['data']
        self.assertEqual((data['status'], data['invoice_number'], data['reviewed_by_name']), ('approved', 'INV-2026-00001', 'root@x.com'))

    def test_a_company_that_was_restricted_works_again_after_approval(self):
        self.assertEqual(code(self.ceo.get('/api/v1/organization/departments/')), 'SUBSCRIPTION_RESTRICTED')
        with at(TODAY):
            self.approve(self.pay())
            self.assertEqual(login_as('ceo@a.com').get('/api/v1/organization/departments/').status_code, 200)

    def test_approving_twice_changes_nothing(self):
        pid = self.pay()
        self.approve(pid)
        sub = sub_of('a-co')
        before = (sub.current_period_end, sub.updated_at, Invoice.objects.count(), Notification.objects.count(),
                  PlatformActionLog.objects.count(), AuditLog.objects.count())
        res = self.approve(pid, today=D(2026, 12, 20))               # even weeks later
        self.assertEqual(res.status_code, 200)
        self.assertIn('already approved', res.data['message'])
        sub = sub_of('a-co')
        self.assertEqual(before, (sub.current_period_end, sub.updated_at, Invoice.objects.count(), Notification.objects.count(),
                                  PlatformActionLog.objects.count(), AuditLog.objects.count()))
        _, changed = services.approve_payment(PaymentSubmission.objects.get(), User.objects.get(email='root@x.com'))
        self.assertFalse(changed)

    def test_a_renewal_extends_from_the_old_end_date_so_no_days_are_lost(self):
        self.approve(self.pay(months=1, transaction_id='FIRSTPAY01'))
        with at(TODAY):
            end_on('a-co', D(2026, 11, 20))
            sub = sub_of('a-co')
            sub.reminders_sent = [7]
            sub.save()
        start_before = sub_of('a-co').current_period_start
        pid = self.pay(login_as('ceo@a.com'), months=3, transaction_id='RENEWAL0001')
        self.assertEqual(PaymentSubmission.objects.get(pk=pid).kind, 'renewal')
        self.approve(pid)
        sub = sub_of('a-co')
        self.assertEqual(sub.current_period_end, D(2027, 2, 20))        # 21 Nov + 3 months - 1 day
        self.assertEqual(sub.current_period_start, start_before)         # the running period keeps its start
        self.assertEqual(sub.reminders_sent, [])
        invoice = Invoice.objects.get(transaction_id='RENEWAL0001')
        self.assertEqual((invoice.period_start, invoice.period_end), (D(2026, 11, 21), D(2027, 2, 20)))
        self.assertEqual(invoice.number, 'INV-2026-00002')

    def test_a_renewal_inside_the_grace_period_still_starts_after_the_old_end(self):
        self.approve(self.pay(months=1, transaction_id='FIRSTPAY01'))
        with at(TODAY):
            end_on('a-co', D(2026, 11, 8))                               # ended 2 days ago, grace still running
        pid = self.pay(login_as('ceo@a.com'), months=1, transaction_id='GRACEPAY001')
        self.approve(pid)
        self.assertEqual(sub_of('a-co').current_period_end, D(2026, 12, 8))   # 9 Nov + 1 month - 1 day

    def test_an_expired_company_restarts_from_today_with_the_plan_it_chose(self):
        self.approve(self.pay(months=1, transaction_id='FIRSTPAY01'))
        with at(TODAY):
            end_on('a-co', D(2026, 10, 1), status=Subscription.STATUS_EXPIRED)
        pid = self.pay(login_as('ceo@a.com'), plan='Professional', months=2, transaction_id='BACKAGAIN01')
        res = self.approve(pid)
        self.assertEqual(res.status_code, 200, res.content)
        sub = sub_of('a-co')
        self.assertEqual((sub.status, sub.plan.name, sub.current_period_start, sub.current_period_end), ('active', 'Professional', TODAY, D(2027, 1, 9)))

    def test_one_month_twelve_months_and_thirty_six_months_end_on_the_right_day(self):
        for n, (months, end) in enumerate([(1, D(2026, 12, 9)), (12, D(2027, 11, 9)), (36, D(2029, 11, 9))]):
            ceo = waiting_company(f'm{n}-co', f'ceo@m{n}.com')
            pid = self.pay(ceo, months=months, transaction_id=f'MONTHS{n}XYZ')
            self.approve(pid)
            self.assertEqual(sub_of(f'm{n}-co').current_period_end, end, months)
        self.assertEqual(Invoice.objects.get(transaction_id='MONTHS1XYZ').amount, Decimal('15000.00'))   # 12 months = 10 months' price

    def test_invoice_numbers_run_on_across_companies(self):
        for n in range(3):
            ceo = waiting_company(f'n{n}-co', f'ceo@n{n}.com')
            self.approve(self.pay(ceo, transaction_id=f'NUMBER{n}ABC'))
        self.assertEqual(sorted(Invoice.objects.values_list('number', flat=True)), ['INV-2026-00001', 'INV-2026-00002', 'INV-2026-00003'])

    def test_the_company_is_told_and_the_decision_is_logged_twice(self):
        pid = self.pay(transaction_id='NOTIFY00001')
        self.approve(pid)
        titles = Notification.objects.filter(kind=Notification.KIND_PAYMENT_APPROVED)
        self.assertEqual(set(titles.values_list('recipient__user__email', flat=True)), {'ceo@a.com'})
        self.assertIn('INV-2026-00001', titles.first().message)
        log = PlatformActionLog.objects.get(action='approve_payment')
        self.assertEqual((log.company.subdomain, log.actor.email), ('a-co', 'root@x.com'))
        self.assertIn('NOTIFY00001', log.note)
        rows_ = AuditLog.objects.filter(company__subdomain='a-co', model_name='PaymentSubmission', action='update')
        self.assertTrue(rows_.exists())
        self.assertIn('status', rows_.first().changed_fields)
        self.assertEqual(rows_.first().actor_email, 'root@x.com')

    def test_a_billing_holder_is_notified_too(self):
        give_role(Subscription.objects.get(company__subdomain='a-co').company_id, self.ceo_employee('A-2'), ['view_billing'], 'Billing')
        self.approve(self.pay(transaction_id='NOTIFY00002'))
        got = set(Notification.objects.filter(kind=Notification.KIND_PAYMENT_APPROVED).values_list('recipient__user__email', flat=True))
        self.assertEqual(got, {'ceo@a.com', 'bill@a.com'})

    def ceo_employee(self, code_):
        from organization.models import Employee
        return Employee.objects.get(company__subdomain='a-co', employee_code=code_).id

    def test_a_company_can_never_approve_or_reject_its_own_payment(self):
        pid = self.pay()
        for action in ('approve', 'reject'):
            res = self.ceo.post(f'{ADMIN}{pid}/{action}/', {'note': 'ok'}, format='json')
            self.assertEqual(res.status_code, 403, action)
            self.assertEqual(self.ceo.post(f'{PAYMENTS}{pid}/{action}/', {'note': 'ok'}, format='json').status_code, 404, action)
        self.assertEqual(self.ceo.get(ADMIN).status_code, 403)
        self.assertEqual(PaymentSubmission.objects.get().status, 'pending')
        self.assertEqual(sub_of('a-co').status, Subscription.STATUS_PENDING_PAYMENT)

    def test_rejecting_needs_a_note_and_tells_the_company(self):
        pid = self.pay()
        res = self.admin.post(f'{ADMIN}{pid}/reject/', {}, format='json')
        self.assertEqual((res.status_code, code(res)), (400, 'REJECTION_NOTE_REQUIRED'))
        self.assertEqual(PaymentSubmission.objects.get().status, 'pending')
        res = self.admin.post(f'{ADMIN}{pid}/reject/', {'note': 'We could not find this transaction.'}, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        payment = PaymentSubmission.objects.get()
        self.assertEqual((payment.status, payment.review_note, payment.reviewed_by.email), ('rejected', 'We could not find this transaction.', 'root@x.com'))
        self.assertEqual(sub_of('a-co').status, Subscription.STATUS_PENDING_PAYMENT)      # nothing started
        self.assertEqual(Invoice.objects.count(), 0)
        note = Notification.objects.get(kind=Notification.KIND_PAYMENT_REJECTED)
        self.assertIn('We could not find this transaction.', note.message)
        self.assertEqual(PlatformActionLog.objects.get(action='reject_payment').company.subdomain, 'a-co')
        seen = rows(self.ceo.get(PAYMENTS))[0]
        self.assertEqual((seen['status'], seen['review_note']), ('rejected', 'We could not find this transaction.'))
        self.assertNotIn('reviewed_by_name', seen)                # a company sees the decision, not who made it

    def test_rejecting_twice_changes_nothing_and_a_decided_payment_cannot_be_flipped(self):
        pid = self.pay()
        self.admin.post(f'{ADMIN}{pid}/reject/', {'note': 'No match.'}, format='json')
        count = Notification.objects.count()
        self.assertEqual(self.admin.post(f'{ADMIN}{pid}/reject/', {'note': 'Again'}, format='json').status_code, 200)
        self.assertEqual(Notification.objects.count(), count)
        self.assertEqual(PaymentSubmission.objects.get().review_note, 'No match.')
        res = self.admin.post(f'{ADMIN}{pid}/approve/', {}, format='json')
        self.assertEqual((res.status_code, code(res)), (400, 'PAYMENT_ALREADY_REJECTED'))
        pid2 = self.pay(transaction_id='SECONDPAY01')
        self.approve(pid2)
        res = self.admin.post(f'{ADMIN}{pid2}/reject/', {'note': 'Too late'}, format='json')
        self.assertEqual((res.status_code, code(res)), (400, 'PAYMENT_ALREADY_APPROVED'))

    def test_the_admin_list_filters_and_shows_the_company(self):
        self.pay(transaction_id='LISTPAY0001')
        other = waiting_company('b-co', 'ceo@b.com')
        self.pay(other, transaction_id='LISTPAY0002', method='nagad')
        everything = rows(self.admin.get(ADMIN))
        self.assertEqual(len(everything), 2)
        self.assertEqual({p['company_name'] for p in everything}, {'A-CO', 'B-CO'})
        self.assertEqual(len(rows(self.admin.get(ADMIN, {'status': 'pending'}))), 2)
        self.assertEqual(len(rows(self.admin.get(ADMIN, {'status': 'approved'}))), 0)
        self.assertEqual(len(rows(self.admin.get(ADMIN, {'method': 'nagad'}))), 1)
        self.assertEqual(len(rows(self.admin.get(ADMIN, {'q': 'listpay0001'}))), 1)
        self.assertEqual(len(rows(self.admin.get(ADMIN, {'q': 'b-co'}))), 1)
        one = everything[0]
        self.assertEqual(self.admin.get(f"{ADMIN}{one['id']}/").status_code, 200)

    def test_approval_is_atomic_when_the_invoice_cannot_be_written(self):
        pid = self.pay()
        with mock.patch.object(services, '_create_paid_invoice', side_effect=services.BillingError('boom', code='X')):
            res = self.approve(pid)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(PaymentSubmission.objects.get().status, 'pending')
        self.assertEqual(sub_of('a-co').status, Subscription.STATUS_PENDING_PAYMENT)
        self.assertEqual(Notification.objects.count(), 0)
