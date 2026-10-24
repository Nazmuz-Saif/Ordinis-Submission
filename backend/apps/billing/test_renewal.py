"""ST-149: the renewal invoice issued 7 days before the end, paying it, and the invoice detail."""
import datetime
from decimal import Decimal

from django.test import TestCase

from billing import services
from billing.models import Invoice, PaymentSubmission, Subscription
from billing.test_payments import ADMIN, PAYMENTS, body, code, make_admin
from billing.test_subscription import at, end_on, sub_of
from core.test_utils import add_employee, login_as, register_company, rows
from notifications.models import Notification
from tenants.models import Company

D = datetime.date
SUBSCRIPTION = '/api/v1/billing/subscription/'
INVOICES = '/api/v1/billing/invoices/'
TODAY = D(2026, 11, 10)


def run_job(today):
    with at(today):
        return services.process_subscriptions()


def renewal(subdomain):
    return Invoice.objects.filter(company__subdomain=subdomain, kind=Invoice.KIND_RENEWAL)


class RenewalInvoiceJobTests(TestCase):
    def setUp(self):
        self.ceo = register_company('R Co', 'r-co', 'ceo@r.com')
        end_on('r-co', D(2026, 11, 20))         # TODAY is 10 days before the end

    def test_nothing_is_issued_8_days_before_the_end_and_one_invoice_at_7(self):
        self.assertEqual(run_job(D(2026, 11, 12))['invoiced'], 0)            # 8 days left
        self.assertEqual(renewal('r-co').count(), 0)
        self.assertEqual(run_job(D(2026, 11, 13))['invoiced'], 1)            # 7 days left
        invoice = renewal('r-co').get()
        self.assertEqual((invoice.status, invoice.kind, invoice.due_on, invoice.issued_on), ('open', 'renewal', D(2026, 11, 20), D(2026, 11, 13)))
        self.assertEqual((invoice.period_start, invoice.period_end), (D(2026, 11, 21), D(2027, 11, 20)))   # same 12 months as before
        self.assertEqual((invoice.plan_name, invoice.months, invoice.amount), ('Basic', 12, Decimal('15000.00')))
        self.assertRegex(invoice.number, r'^INV-2026-\d{5}$')

    def test_the_job_run_twice_or_on_later_days_issues_it_once(self):
        for day in (D(2026, 11, 13), D(2026, 11, 13), D(2026, 11, 19), D(2026, 11, 20), D(2026, 11, 22)):
            run_job(day)
        self.assertEqual(renewal('r-co').count(), 1)

    def test_it_is_issued_at_1_day_and_at_0_days_left_when_earlier_days_were_missed(self):
        self.assertEqual(run_job(D(2026, 11, 19))['invoiced'], 1)             # 1 day left
        self.assertEqual(renewal('r-co').count(), 1)
        end_on('r-co', D(2026, 11, 20))
        Invoice.objects.all().delete()
        self.assertEqual(run_job(D(2026, 11, 20))['invoiced'], 1)             # the last day
        self.assertEqual(renewal('r-co').get().due_on, D(2026, 11, 20))

    def test_it_is_still_issued_inside_the_grace_period_but_not_after_expiry(self):
        self.assertEqual(run_job(D(2026, 11, 22))['invoiced'], 1)             # 2 days past the end
        Invoice.objects.all().delete()
        self.assertEqual(run_job(D(2026, 11, 24))['invoiced'], 0)             # past the grace period: it expires instead
        self.assertEqual(sub_of('r-co').status, Subscription.STATUS_EXPIRED)

    def test_the_amount_is_the_plans_price_for_the_last_paid_length(self):
        sub = sub_of('r-co')
        sub.billing_months = 3
        sub.save()
        run_job(D(2026, 11, 14))
        invoice = renewal('r-co').get()
        self.assertEqual((invoice.months, invoice.amount, invoice.period_end), (3, Decimal('4500.00'), D(2027, 2, 20)))

    def test_nothing_is_issued_while_a_payment_is_waiting(self):
        self.ceo.post(PAYMENTS, body(months=1), format='json')
        self.assertEqual(run_job(D(2026, 11, 14))['invoiced'], 0)
        self.assertEqual(renewal('r-co').count(), 0)

    def test_a_suspended_company_still_gets_its_invoice_but_no_reminder(self):
        Company.objects.filter(subdomain='r-co').update(is_active=False)
        result = run_job(D(2026, 11, 14))
        self.assertEqual((result['invoiced'], result['reminded']), (1, 0))

    def test_the_reminder_names_the_invoice(self):
        run_job(D(2026, 11, 13))
        message = Notification.objects.filter(kind=Notification.KIND_BILLING_REMINDER).first().message
        self.assertIn(renewal('r-co').get().number, message)

    def test_a_company_waiting_for_the_first_payment_gets_no_renewal_invoice(self):
        Subscription.objects.filter(company__subdomain='r-co').update(status=Subscription.STATUS_PENDING_PAYMENT)
        self.assertEqual(run_job(D(2026, 11, 14))['checked'], 0)
        self.assertEqual(renewal('r-co').count(), 0)


class RenewalPaymentTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.ceo = register_company('P Co', 'p-co', 'ceo@p.com')
        add_employee(self.ceo, 'plain@p.com', 'P-2')
        end_on('p-co', D(2026, 11, 20))
        sub = sub_of('p-co')
        sub.billing_months = 3
        sub.reminders_sent = [7]
        sub.save()
        run_job(D(2026, 11, 14))                               # 6 days left: the invoice is issued
        self.invoice = renewal('p-co').get()

    def pay(self, client=None, **over):
        data = {'invoice': str(self.invoice.id), 'method': 'bkash', 'payer_name': 'Rahim', 'payer_number': '01712345678', 'transaction_id': 'RENEW00001'}
        data.update(over)
        return (client or self.ceo).post(PAYMENTS, data, format='json')

    def approve(self, pid, today=D(2026, 11, 14)):
        with at(today):
            return self.admin.post(f'{ADMIN}{pid}/approve/', {}, format='json')

    def test_the_billing_page_data_offers_the_invoice_and_then_the_pending_payment(self):
        data = self.ceo.get(SUBSCRIPTION).data['data']
        self.assertEqual(data['renewal_invoice']['number'], self.invoice.number)
        self.assertEqual((data['renewal_invoice']['status'], data['renewal_invoice']['months']), ('open', 3))
        self.assertIsNone(data['pending_payment'])
        self.assertEqual(self.pay().status_code, 201)
        data = self.ceo.get(SUBSCRIPTION).data['data']
        self.assertEqual((data['pending_payment']['status'], data['pending_payment']['invoice']), ('pending', self.invoice.id))
        self.assertEqual(str(data['pending_payment']['amount']), '4500.00')

    def test_paying_the_invoice_uses_its_plan_months_and_amount(self):
        res = self.pay()
        self.assertEqual(res.status_code, 201, res.content)
        payment = PaymentSubmission.objects.get()
        self.assertEqual((payment.invoice_id, payment.kind, payment.months, payment.amount, payment.plan.name),
                         (self.invoice.id, 'renewal', 3, Decimal('4500.00'), 'Basic'))

    def test_the_amount_the_person_saw_must_match_and_months_must_match_the_invoice(self):
        self.assertEqual(code(self.pay(amount='1.00')), 'PAYMENT_AMOUNT_MISMATCH')
        self.assertEqual(code(self.pay(months=12)), 'INVOICE_MONTHS_MISMATCH')
        self.assertEqual(code(self.pay(plan='Professional')), 'PLAN_CHANGE_NOT_VIA_RENEWAL')
        self.assertEqual(PaymentSubmission.objects.count(), 0)
        self.assertEqual(self.pay(amount='4500.00', months=3, plan='Basic').status_code, 201)

    def test_another_companys_or_a_bad_or_a_paid_invoice_is_refused(self):
        other = register_company('O Co', 'o-co', 'ceo@o.com')
        end_on('o-co', D(2026, 11, 20))
        run_job(D(2026, 11, 14))
        theirs = renewal('o-co').get()
        for bad in (str(theirs.id), 'not-an-id', '00000000-0000-0000-0000-000000000000'):
            res = self.pay(invoice=bad)
            self.assertEqual((res.status_code, code(res)), (400, 'INVOICE_NOT_PAYABLE'), bad)
        self.assertEqual(self.pay(other, invoice=str(self.invoice.id)).status_code, 400)       # and not the other way round
        Invoice.objects.filter(pk=self.invoice.pk).update(status='paid')
        self.assertEqual(code(self.pay()), 'INVOICE_NOT_PAYABLE')
        self.assertEqual(PaymentSubmission.objects.count(), 0)

    def test_only_manage_billing_can_pay(self):
        self.assertEqual(self.pay(login_as('plain@p.com')).status_code, 403)

    def test_approval_marks_the_same_invoice_paid_and_moves_the_end_date_without_losing_days(self):
        pid = self.pay().data['id']
        self.assertEqual(self.approve(pid).status_code, 200)
        invoice = Invoice.objects.get(pk=self.invoice.pk)
        self.assertEqual((invoice.status, invoice.paid_on, invoice.payment_method, invoice.transaction_id), ('paid', D(2026, 11, 14), 'bkash', 'RENEW00001'))
        self.assertEqual((invoice.period_start, invoice.period_end, invoice.amount), (D(2026, 11, 21), D(2027, 2, 20), Decimal('4500.00')))
        self.assertEqual(Invoice.objects.filter(company__subdomain='p-co', kind=Invoice.KIND_RENEWAL).count(), 1)   # no second invoice
        self.assertEqual(Invoice.objects.filter(kind=Invoice.KIND_PAYMENT).count(), 0)
        sub = sub_of('p-co')
        self.assertEqual((sub.current_period_end, sub.status, sub.reminders_sent), (D(2027, 2, 20), 'active', []))
        payment = PaymentSubmission.objects.get()
        self.assertEqual((payment.status, payment.invoice_id, payment.period_end), ('approved', self.invoice.id, D(2027, 2, 20)))
        data = self.ceo.get(SUBSCRIPTION).data['data']
        self.assertIsNone(data['renewal_invoice'])
        self.assertIsNone(data['pending_payment'])

    def test_approving_twice_changes_nothing_and_the_job_does_not_issue_another_invoice(self):
        pid = self.pay().data['id']
        self.approve(pid)
        before = (Invoice.objects.count(), sub_of('p-co').current_period_end)
        self.approve(pid, today=D(2026, 12, 1))
        self.assertEqual(before, (Invoice.objects.count(), sub_of('p-co').current_period_end))
        for day in (D(2026, 11, 15), D(2027, 2, 14), D(2027, 2, 20)):          # the next end date is far away until 7 days before it
            run_job(day)
        self.assertEqual(renewal('p-co').count(), 2 if run_job(D(2027, 2, 20))['checked'] else 1)

    def test_a_rejected_payment_leaves_the_invoice_open_and_it_can_be_paid_again(self):
        pid = self.pay().data['id']
        self.admin.post(f'{ADMIN}{pid}/reject/', {'note': 'Transaction not found.'}, format='json')
        self.assertEqual(Invoice.objects.get(pk=self.invoice.pk).status, 'open')
        data = self.ceo.get(SUBSCRIPTION).data['data']
        self.assertEqual(str(data['renewal_invoice']['id']), str(self.invoice.id))
        self.assertIsNone(data['pending_payment'])
        res = self.pay(transaction_id='RENEW00002')
        self.assertEqual(res.status_code, 201, res.content)
        self.approve(res.data['id'])
        self.assertEqual(Invoice.objects.get(pk=self.invoice.pk).transaction_id, 'RENEW00002')
        self.assertEqual(PaymentSubmission.objects.filter(invoice=self.invoice).count(), 2)

    def test_the_same_invoice_cannot_be_paid_twice_at_once(self):
        self.assertEqual(self.pay().status_code, 201)
        self.assertEqual(code(self.pay(transaction_id='RENEW00003')), 'PAYMENT_ALREADY_PENDING')

    def test_an_expired_company_paying_its_invoice_restarts_from_today_and_the_invoice_gets_the_real_period(self):
        end_on('p-co', D(2026, 10, 1), status=Subscription.STATUS_EXPIRED)
        pid = self.pay().data['id']
        self.approve(pid, today=D(2026, 11, 14))
        sub = sub_of('p-co')
        self.assertEqual((sub.current_period_start, sub.current_period_end), (D(2026, 11, 14), D(2027, 2, 13)))
        invoice = Invoice.objects.get(pk=self.invoice.pk)
        self.assertEqual((invoice.status, invoice.period_start, invoice.period_end), ('paid', D(2026, 11, 14), D(2027, 2, 13)))
        self.assertEqual(login_as('ceo@p.com').get('/api/v1/organization/departments/').status_code, 200)

    def test_an_early_renewal_voids_the_renewal_invoice_it_covers(self):
        # paid early without the invoice: 3 months from the old end
        with at(D(2026, 11, 14)):
            res = self.ceo.post(PAYMENTS, body(plan='Basic', months=12, transaction_id='EARLY000001'), format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.approve(res.data['id'])
        self.assertEqual(Invoice.objects.get(pk=self.invoice.pk).status, 'void')
        self.assertEqual(Invoice.objects.filter(kind=Invoice.KIND_PAYMENT).count(), 1)
        self.assertIsNone(self.ceo.get(SUBSCRIPTION).data['data']['renewal_invoice'])

    def test_an_invoice_that_is_no_longer_open_blocks_the_approval(self):
        pid = self.pay().data['id']
        Invoice.objects.filter(pk=self.invoice.pk).update(status='void')
        res = self.approve(pid)
        self.assertEqual((res.status_code, code(res)), (400, 'INVOICE_NOT_OPEN'))
        self.assertEqual(PaymentSubmission.objects.get().status, 'pending')


class InvoiceDetailTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.ceo = register_company('I Co', 'i-co', 'ceo@i.com')
        add_employee(self.ceo, 'plain@i.com', 'I-2')
        end_on('i-co', D(2026, 11, 20))
        run_job(D(2026, 11, 14))
        self.invoice = renewal('i-co').get()
        pid = self.ceo.post(PAYMENTS, {'invoice': str(self.invoice.id), 'method': 'nagad', 'payer_name': 'Karim', 'payer_number': '01812345678', 'transaction_id': 'DETAIL00001'}, format='json').data['id']
        with at(D(2026, 11, 14)):
            self.admin.post(f'{ADMIN}{pid}/approve/', {}, format='json')

    def test_the_detail_has_everything_the_page_shows(self):
        data = self.ceo.get(f'{INVOICES}{self.invoice.id}/').data
        expected = {'number': self.invoice.number, 'company_name': 'I Co', 'plan_name': 'Basic', 'months': 12, 'currency': 'BDT',
                    'status': 'paid', 'status_label': 'Paid', 'payment_method': 'nagad', 'payment_method_label': 'Nagad',
                    'transaction_id': 'DETAIL00001', 'kind': 'renewal'}
        for key, value in expected.items():
            self.assertEqual(data[key], value, key)
        for key in ('period_start', 'period_end', 'amount', 'issued_on', 'due_on', 'paid_on'):
            self.assertTrue(data[key], key)
        self.assertEqual(data['issued_on'], '2026-11-14')
        self.assertEqual(data['paid_on'], '2026-11-14')

    def test_an_open_invoice_has_no_payment_method_yet(self):
        Invoice.objects.filter(pk=self.invoice.pk).update(status='open', paid_on=None, payment_method='', transaction_id='')
        data = self.ceo.get(f'{INVOICES}{self.invoice.id}/').data
        self.assertEqual((data['status'], data['paid_on'], data['payment_method_label']), ('open', None, ''))

    def test_another_companys_invoice_is_a_404_and_the_list_shows_only_your_own(self):
        other = register_company('X Co', 'x-co', 'ceo@x.com')
        self.assertEqual(other.get(f'{INVOICES}{self.invoice.id}/').status_code, 404)
        self.assertEqual(self.ceo.get(f'{INVOICES}00000000-0000-0000-0000-000000000000/').status_code, 404)
        self.assertEqual([i['number'] for i in rows(other.get(INVOICES))], [])
        self.assertIn(self.invoice.number, [i['number'] for i in rows(self.ceo.get(INVOICES))])

    def test_only_view_billing_can_read_it(self):
        self.assertEqual(login_as('plain@i.com').get(f'{INVOICES}{self.invoice.id}/').status_code, 403)
        self.assertEqual(login_as('plain@i.com').get(SUBSCRIPTION).status_code, 403)

    def test_invoices_written_before_this_story_get_a_kind_and_months(self):
        monthly = services.generate_invoice(sub_of('i-co'), 2026, 3)[0]
        self.assertEqual((monthly.kind, monthly.months), ('monthly', 1))
        paid = Invoice.objects.filter(kind=Invoice.KIND_PAYMENT)
        self.assertEqual(paid.count(), 0)          # this payment settled the renewal invoice, so no extra invoice was written
