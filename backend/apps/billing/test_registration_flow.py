"""ST-147: a new company starts waiting for its first payment and works only after the platform team approves it."""
from decimal import Decimal

from django.test import TestCase, override_settings

from billing.models import Invoice, PaymentSubmission, Subscription
from billing.test_payments import ADMIN, PAYMENTS, QUOTE, body, code, make_admin
from core.test_utils import add_employee, login_as, register_company, rows

INSTRUCTIONS = '/api/v1/billing/payment-instructions/'


class RegistrationStartsPendingTests(TestCase):
    def test_a_new_company_is_pending_payment_on_the_basic_plan(self):
        register_company('New Co', 'new-co', 'ceo@new.com', activate=False)
        sub = Subscription.objects.get(company__subdomain='new-co')
        self.assertEqual((sub.status, sub.plan.name), (Subscription.STATUS_PENDING_PAYMENT, 'Basic'))

    def test_me_tells_the_frontend_the_company_is_waiting(self):
        ceo = register_company('New Co', 'new-co', 'ceo@new.com', activate=False)
        data = ceo.get('/api/v1/auth/me/').data['data']['subscription']
        self.assertEqual((data['status'], data['restricted']), ('pending_payment', True))

    def test_the_owner_is_signed_in_but_cannot_use_the_company_yet(self):
        ceo = register_company('New Co', 'new-co', 'ceo@new.com', activate=False)
        self.assertEqual(ceo.get('/api/v1/auth/me/').status_code, 200)
        res = ceo.get('/api/v1/organization/departments/')
        self.assertEqual((res.status_code, code(res)), (403, 'SUBSCRIPTION_RESTRICTED'))
        self.assertEqual(login_as('ceo@new.com').get('/api/v1/billing/plans/').status_code, 200)   # logging in again works

    def test_the_helper_activates_by_default_so_other_tests_are_unaffected(self):
        ceo = register_company('Old Co', 'old-co', 'ceo@old.com')
        self.assertEqual(ceo.get('/api/v1/organization/departments/').status_code, 200)

    def test_the_plans_page_data_is_available_before_payment(self):
        ceo = register_company('New Co', 'new-co', 'ceo@new.com', activate=False)
        names = [p['name'] for p in ceo.get('/api/v1/billing/plans/').data]
        self.assertEqual(names, ['Basic', 'Professional', 'Enterprise'])


class PaymentInstructionsTests(TestCase):
    def setUp(self):
        self.ceo = register_company('New Co', 'new-co', 'ceo@new.com', activate=False)

    def test_the_instructions_come_from_the_server_settings(self):
        data = self.ceo.get(INSTRUCTIONS).data['data']
        self.assertEqual([m['method'] for m in data['methods']], ['bkash', 'nagad', 'bank', 'cash'])
        self.assertTrue(all(m['label'] and m['instructions'] for m in data['methods']))
        self.assertTrue(data['note'])

    @override_settings(PAYMENT_INSTRUCTIONS=[{'method': 'bkash', 'label': 'bKash', 'instructions': 'Pay 01911-111111'},
                                             {'method': 'paypal', 'label': 'PayPal', 'instructions': 'no'}],
                       PAYMENT_NOTE='Reference: your company name')
    def test_changing_the_settings_changes_the_answer_and_an_unknown_method_is_dropped(self):
        data = self.ceo.get(INSTRUCTIONS).data['data']
        self.assertEqual(data['methods'], [{'method': 'bkash', 'label': 'bKash', 'instructions': 'Pay 01911-111111'}])
        self.assertEqual(data['note'], 'Reference: your company name')

    def test_only_manage_billing_can_read_them(self):
        ceo = register_company('Other', 'other', 'ceo@other.com')
        add_employee(ceo, 'plain@other.com', 'O-2')
        self.assertEqual(login_as('plain@other.com').get(INSTRUCTIONS).status_code, 403)


class FirstPaymentEndToEndTests(TestCase):
    def test_register_choose_pay_wait_get_approved_and_start(self):
        admin = make_admin()
        ceo = register_company('Flow Co', 'flow-co', 'ceo@flow.com', activate=False)

        quote = ceo.get(QUOTE, {'plan': 'Professional', 'months': 3}).data['data']
        self.assertEqual((quote['kind'], quote['amount']), ('new', Decimal('15000.00')))

        res = ceo.post(PAYMENTS, body(plan='Professional', months=3, amount=str(quote['amount'])), format='json')
        self.assertEqual(res.status_code, 201, res.content)
        waiting = rows(ceo.get(PAYMENTS))[0]
        self.assertEqual((waiting['status'], waiting['plan_name'], waiting['months']), ('pending', 'Professional', 3))
        self.assertEqual(code(ceo.get('/api/v1/organization/departments/')), 'SUBSCRIPTION_RESTRICTED')   # still waiting

        # a second tab or a reload shows the same waiting state, and the company still cannot work
        again = login_as('ceo@flow.com')
        self.assertEqual(rows(again.get(PAYMENTS))[0]['status'], 'pending')
        self.assertEqual(again.get('/api/v1/auth/me/').data['data']['subscription']['status'], 'pending_payment')

        self.assertEqual(admin.post(f"{ADMIN}{waiting['id']}/approve/", {}, format='json').status_code, 200)

        me = login_as('ceo@flow.com').get('/api/v1/auth/me/').data['data']
        self.assertEqual((me['subscription']['status'], me['subscription']['restricted'], me['plan_name']), ('active', False, 'Professional'))
        self.assertEqual(login_as('ceo@flow.com').get('/api/v1/organization/departments/').status_code, 200)
        invoice = Invoice.objects.get(company__subdomain='flow-co')
        self.assertEqual((invoice.amount, invoice.status, invoice.plan_name), (Decimal('15000.00'), 'paid', 'Professional'))
        self.assertEqual(PaymentSubmission.objects.get().status, 'approved')

    def test_a_rejected_first_payment_can_be_submitted_again_and_then_approved(self):
        admin = make_admin()
        ceo = register_company('Flow Co', 'flow-co', 'ceo@flow.com', activate=False)
        pid = ceo.post(PAYMENTS, body(), format='json').data['id']
        admin.post(f'{ADMIN}{pid}/reject/', {'note': 'The transaction id was not found.'}, format='json')
        latest = rows(ceo.get(PAYMENTS))[0]
        self.assertEqual((latest['status'], latest['review_note']), ('rejected', 'The transaction id was not found.'))
        self.assertEqual(Subscription.objects.get().status, Subscription.STATUS_PENDING_PAYMENT)
        res = ceo.post(PAYMENTS, body(transaction_id='CORRECTID99'), format='json')
        self.assertEqual(res.status_code, 201, res.content)
        newest = rows(ceo.get(PAYMENTS))[0]
        self.assertEqual((newest['status'], newest['transaction_id']), ('pending', 'CORRECTID99'))
        self.assertEqual(rows(ceo.get(PAYMENTS))[1]['status'], 'rejected')           # the history is kept, newest first
        admin.post(f"{ADMIN}{newest['id']}/approve/", {}, format='json')
        self.assertEqual(Subscription.objects.get().status, Subscription.STATUS_ACTIVE)

    def test_every_duration_from_one_to_thirty_six_months_can_be_quoted_and_submitted(self):
        for n, months in enumerate((1, 3, 6, 12, 24, 36)):
            ceo = register_company(f'D{n}', f'd{n}-co', f'ceo@d{n}.com', activate=False)
            quote = ceo.get(QUOTE, {'plan': 'Basic', 'months': months}).data['data']
            res = ceo.post(PAYMENTS, body(months=months, transaction_id=f'DURATION{n}X', amount=str(quote['amount'])), format='json')
            self.assertEqual(res.status_code, 201, (months, res.content))
            self.assertEqual(res.data['amount'], str(quote['amount']))
