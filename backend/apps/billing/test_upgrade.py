"""ST-151: plan upgrade quote and approval, and a lower plan that starts at the next renewal."""
import datetime
from decimal import Decimal

from django.test import TestCase

from billing import services
from billing.models import Invoice, PaymentSubmission, Subscription
from billing.test_payments import ADMIN, PAYMENTS, body, code, make_admin
from billing.test_subscription import at, end_on, sub_of
from core.test_utils import add_employee, give_role, login_as, register_company
from notifications.models import Notification
from tenants.models import Company

D = datetime.date
TODAY = D(2026, 11, 10)
UP_QUOTE = '/api/v1/billing/upgrade-quote/'
DOWNGRADE = '/api/v1/billing/downgrade/'
SUBSCRIPTION = '/api/v1/billing/subscription/'


def upgrade_body(**over):
    data = body(months='', kind='upgrade')
    data['plan'] = 'Professional'
    data.update(over)
    return data


class UpgradeBase(TestCase):
    def setUp(self):
        self.ceo = register_company('U Co', 'u-co', 'ceo@u.com')
        self.company = Company.objects.get(subdomain='u-co')

    def run_at(self, days_left, status=Subscription.STATUS_ACTIVE):
        end_on('u-co', TODAY + datetime.timedelta(days=days_left), status)
        return at(TODAY)

    def put_on(self, plan):
        services.change_plan(self.company, plan)


class UpgradeQuoteTests(UpgradeBase):
    def quote(self, plan='Professional'):
        return self.ceo.get(UP_QUOTE, {'plan': plan})

    def test_extra_amount_is_the_price_difference_times_days_left_over_30(self):
        for left, amount in ((30, '3500'), (15, '1750'), (10, '1167'), (1, '117')):
            with self.run_at(left):
                data = self.quote().data['data']
            self.assertEqual(str(data['amount']), amount, left)
            self.assertEqual(data['days_left'], left)

    def test_the_end_date_does_not_change(self):
        with self.run_at(20):
            data = self.quote().data['data']
        self.assertEqual(str(data['period_end']), str(TODAY + datetime.timedelta(days=20)))
        self.assertEqual(sub_of('u-co').current_period_end, TODAY + datetime.timedelta(days=20))

    def test_quote_saves_nothing(self):
        with self.run_at(20):
            self.quote()
        self.assertFalse(PaymentSubmission.objects.exists())
        self.assertEqual(sub_of('u-co').plan.name, 'Basic')

    def test_the_last_day_has_nothing_to_charge(self):
        with self.run_at(0):
            res = self.quote()
        self.assertEqual(res.status_code, 400)
        self.assertEqual(code(res), 'UPGRADE_NO_DAYS_LEFT')

    def test_same_or_lower_plan_is_not_an_upgrade(self):
        with self.run_at(20):
            self.assertEqual(code(self.quote('Basic')), 'UPGRADE_NOT_HIGHER')
            self.put_on('Professional')
            self.assertEqual(code(self.quote('Professional')), 'UPGRADE_NOT_HIGHER')
            self.assertEqual(code(self.quote('Basic')), 'UPGRADE_NOT_HIGHER')

    def test_unknown_plan(self):
        with self.run_at(20):
            self.assertEqual(code(self.quote('Nope')), 'PLAN_NOT_FOUND')

    def test_only_a_running_period_can_be_upgraded(self):
        for status, left in ((Subscription.STATUS_EXPIRED, -10), (Subscription.STATUS_PENDING_PAYMENT, 5), ):
            with self.run_at(left, status):
                self.assertEqual(code(self.quote()), 'PLAN_CHANGE_NOT_AVAILABLE', status)
        with self.run_at(-2):      # grace
            self.assertEqual(code(self.quote()), 'PLAN_CHANGE_NOT_AVAILABLE')

    def test_needs_view_billing(self):
        add_employee(self.ceo, 'e@u.com', 'U-2')
        with self.run_at(20):
            self.assertEqual(login_as('e@u.com').get(UP_QUOTE, {'plan': 'Professional'}).status_code, 403)

    def test_works_while_restricted(self):
        # an expired company can still read the quote route (it answers with a billing rule, not the restricted-mode 403)
        with self.run_at(-10, Subscription.STATUS_EXPIRED):
            res = self.quote()
        self.assertNotEqual(code(res), 'SUBSCRIPTION_RESTRICTED')


class UpgradePaymentTests(UpgradeBase):
    def submit(self, **over):
        return self.ceo.post(PAYMENTS, upgrade_body(**over), format='json')

    def test_submit_creates_a_pending_upgrade_with_the_server_amount(self):
        with self.run_at(15):
            res = self.submit(amount='1750.00')
        self.assertEqual(res.status_code, 201, res.data)
        pay = PaymentSubmission.objects.get()
        self.assertEqual((pay.kind, pay.status, pay.plan.name, pay.amount), ('upgrade', 'pending', 'Professional', Decimal('1750')))
        self.assertEqual(sub_of('u-co').plan.name, 'Basic')          # nothing changes before approval

    def test_a_changed_amount_is_refused(self):
        with self.run_at(15):
            res = self.submit(amount='1.00')
        self.assertEqual(code(res), 'PAYMENT_AMOUNT_MISMATCH')

    def test_only_one_pending_payment_at_a_time(self):
        with self.run_at(15):
            self.assertEqual(self.submit().status_code, 201)
            res = self.submit(transaction_id='TX9999ZZZZ')
        self.assertEqual(code(res), 'PAYMENT_ALREADY_PENDING')

    def test_not_for_a_lower_plan_or_on_the_last_day(self):
        with self.run_at(15):
            self.put_on('Professional')
            self.assertEqual(code(self.submit(plan='Basic')), 'UPGRADE_NOT_HIGHER')
        self.put_on('Basic')
        with self.run_at(0):
            self.assertEqual(code(self.submit()), 'UPGRADE_NO_DAYS_LEFT')

    def test_only_the_upgrade_kind_can_be_chosen(self):
        with self.run_at(15):
            res = self.submit(kind='new')
        self.assertEqual(code(res), 'PAYMENT_KIND_INVALID')
        self.assertFalse(PaymentSubmission.objects.exists())

    def test_an_upgrade_cannot_pay_a_renewal_invoice(self):
        with self.run_at(15):
            res = self.submit(invoice='00000000-0000-0000-0000-000000000000')
        self.assertEqual(code(res), 'PAYMENT_KIND_INVALID')

    def test_without_manage_billing_it_is_refused(self):
        add_employee(self.ceo, 'e@u.com', 'U-2')
        give_role(self.company.id, add_employee(self.ceo, 'v@u.com', 'U-3')['id'], ['view_billing'], 'Billing viewer')
        with self.run_at(15):
            self.assertEqual(login_as('v@u.com').post(PAYMENTS, upgrade_body(), format='json').status_code, 403)

    def test_approval_switches_the_plan_and_writes_the_extra_invoice(self):
        with self.run_at(15):
            pay_id = self.submit().data['id']
            res = make_admin().post(f'{ADMIN}{pay_id}/approve/')
            self.assertEqual(res.status_code, 200, res.data)
        sub = sub_of('u-co')
        self.assertEqual(sub.plan.name, 'Professional')
        self.assertEqual(sub.current_period_end, TODAY + datetime.timedelta(days=15))       # end date unchanged
        invoice = Invoice.objects.get(kind=Invoice.KIND_UPGRADE)
        self.assertEqual((invoice.amount, invoice.status, invoice.plan_name), (Decimal('1750'), Invoice.STATUS_PAID, 'Professional'))
        self.assertEqual((invoice.period_start, invoice.period_end), (TODAY, sub.current_period_end))
        pay = PaymentSubmission.objects.get()
        self.assertEqual((pay.status, pay.invoice_id), ('approved', invoice.id))
        self.assertTrue(Notification.objects.filter(recipient__user__email='ceo@u.com', kind=Notification.KIND_PAYMENT_APPROVED).exists())

    def test_the_higher_employee_limit_applies_at_once(self):
        for i in range(2, 11):
            add_employee(self.ceo, f'p{i}@u.com', f'U-{i}')
        with self.run_at(15):
            self.assertTrue(services.usage(self.company)['is_full'])
            pay_id = self.submit().data['id']
            make_admin().post(f'{ADMIN}{pay_id}/approve/')
            fresh = Company.objects.get(subdomain='u-co')
            self.assertEqual(services.usage(fresh)['limit'], 50)
            self.assertFalse(services.usage(fresh)['is_full'])

    def test_approving_twice_changes_nothing(self):
        with self.run_at(15):
            pay_id = self.submit().data['id']
            admin = make_admin()
            admin.post(f'{ADMIN}{pay_id}/approve/')
            admin.post(f'{ADMIN}{pay_id}/approve/')
        self.assertEqual(Invoice.objects.filter(kind=Invoice.KIND_UPGRADE).count(), 1)

    def test_rejection_keeps_the_plan(self):
        with self.run_at(15):
            pay_id = self.submit().data['id']
            res = make_admin().post(f'{ADMIN}{pay_id}/reject/', {'note': 'No such payment'}, format='json')
            self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(sub_of('u-co').plan.name, 'Basic')
        self.assertFalse(Invoice.objects.filter(kind=Invoice.KIND_UPGRADE).exists())

    def test_approval_after_the_period_ended_is_refused(self):
        with self.run_at(15):
            pay_id = self.submit().data['id']
        with at(TODAY + datetime.timedelta(days=40)):
            res = make_admin().post(f'{ADMIN}{pay_id}/approve/')
        self.assertEqual(code(res), 'UPGRADE_PERIOD_ENDED')
        self.assertEqual(sub_of('u-co').plan.name, 'Basic')

    def test_an_open_renewal_invoice_follows_the_new_plan(self):
        with self.run_at(5):
            services.process_subscriptions()
            old = Invoice.objects.get(kind=Invoice.KIND_RENEWAL)
            self.assertEqual(old.plan_name, 'Basic')
            pay_id = self.submit().data['id']
            make_admin().post(f'{ADMIN}{pay_id}/approve/')
        old.refresh_from_db()
        self.assertEqual((old.plan_name, old.status), ('Professional', Invoice.STATUS_OPEN))
        self.assertEqual(old.amount, services.price_for(sub_of('u-co').plan, old.months)['amount'])


class DowngradeTests(UpgradeBase):
    def setUp(self):
        super().setUp()
        self.put_on('Professional')

    def schedule(self, plan='Basic'):
        return self.ceo.post(DOWNGRADE, {'plan': plan}, format='json')

    def test_a_lower_plan_is_scheduled_not_started(self):
        with self.run_at(15):
            res = self.schedule()
            self.assertEqual(res.status_code, 201, res.data)
            data = self.ceo.get(SUBSCRIPTION).data['data']
        sub = sub_of('u-co')
        self.assertEqual((sub.plan.name, sub.next_plan.name, sub.next_plan_from), ('Professional', 'Basic', None))
        self.assertEqual(data['next_plan']['name'], 'Basic')
        self.assertEqual(data['plan']['name'], 'Professional')

    def test_refused_when_the_team_is_larger_than_the_lower_plan(self):
        for i in range(2, 13):
            add_employee(self.ceo, f'p{i}@u.com', f'U-{i}')
        with self.run_at(15):
            res = self.schedule()
        self.assertEqual(res.status_code, 400)
        self.assertEqual(code(res), 'PLAN_TOO_SMALL')
        self.assertIn('allows 10 employees but the company has 12', res.data['error']['message'])
        self.assertIsNone(sub_of('u-co').next_plan)

    def test_a_higher_plan_is_not_a_downgrade(self):
        with self.run_at(15):
            self.assertEqual(code(self.schedule('Enterprise')), 'DOWNGRADE_NOT_LOWER')
            self.assertEqual(code(self.schedule('Professional')), 'DOWNGRADE_NOT_LOWER')

    def test_can_be_cancelled_before_it_is_paid(self):
        with self.run_at(15):
            self.schedule()
            res = self.ceo.post(f'{DOWNGRADE}cancel/')
            self.assertEqual(res.status_code, 200, res.data)
            self.assertIsNone(sub_of('u-co').next_plan)
            self.assertEqual(code(self.ceo.post(f'{DOWNGRADE}cancel/')), 'DOWNGRADE_NOT_SCHEDULED')

    def test_the_renewal_invoice_bills_the_lower_plan(self):
        with self.run_at(5):
            self.schedule()
            services.process_subscriptions()
        invoice = Invoice.objects.get(kind=Invoice.KIND_RENEWAL)
        self.assertEqual(invoice.plan_name, 'Basic')
        self.assertEqual(invoice.amount, services.price_for(services.find_plan('Basic'), invoice.months)['amount'])

    def test_a_renewal_may_pick_the_lower_plan_but_not_any_other(self):
        with self.run_at(15):
            self.schedule()
            ok = self.ceo.get('/api/v1/billing/quote/', {'plan': 'Basic', 'months': 1})
            self.assertEqual(ok.status_code, 200, ok.data)
            self.assertEqual(ok.data['data']['kind'], 'renewal')
            bad = self.ceo.get('/api/v1/billing/quote/', {'plan': 'Enterprise', 'months': 1})
            self.assertEqual(code(bad), 'PLAN_CHANGE_NOT_VIA_RENEWAL')

    def test_paying_the_lower_plan_early_keeps_the_current_plan_until_the_new_period_begins(self):
        with self.run_at(15):
            self.schedule()
            pay_id = self.ceo.post(PAYMENTS, body(plan='Basic', months=1), format='json').data['id']
            make_admin().post(f'{ADMIN}{pay_id}/approve/')
            sub = sub_of('u-co')
            old_end = TODAY + datetime.timedelta(days=15)
            self.assertEqual((sub.plan.name, sub.next_plan.name), ('Professional', 'Basic'))
            self.assertEqual(sub.next_plan_from, old_end + datetime.timedelta(days=1))
            self.assertEqual(code(self.ceo.post(f'{DOWNGRADE}cancel/')), 'DOWNGRADE_ALREADY_PAID')
            self.assertEqual(self.ceo.get(SUBSCRIPTION).data['data']['plan']['name'], 'Professional')
        with at(old_end + datetime.timedelta(days=1)):
            self.assertEqual(self.ceo.get(SUBSCRIPTION).data['data']['plan']['name'], 'Basic')
        sub = sub_of('u-co')
        self.assertEqual((sub.plan.name, sub.next_plan_id, sub.next_plan_from), ('Basic', None, None))

    def test_the_daily_job_starts_the_lower_plan(self):
        with self.run_at(15):
            self.schedule()
            pay_id = self.ceo.post(PAYMENTS, body(plan='Basic', months=1), format='json').data['id']
            make_admin().post(f'{ADMIN}{pay_id}/approve/')
        with at(TODAY + datetime.timedelta(days=16)):
            services.process_subscriptions()
        self.assertEqual(sub_of('u-co').plan.name, 'Basic')

    def test_renewing_the_current_plan_forgets_the_scheduled_one(self):
        with self.run_at(15):
            self.schedule()
            pay_id = self.ceo.post(PAYMENTS, body(plan='Professional', months=1), format='json').data['id']
            make_admin().post(f'{ADMIN}{pay_id}/approve/')
        sub = sub_of('u-co')
        self.assertEqual((sub.plan.name, sub.next_plan_id), ('Professional', None))

    def test_an_upgrade_cancels_a_scheduled_lower_plan(self):
        with self.run_at(15):
            self.schedule()
            pay_id = self.ceo.post(PAYMENTS, upgrade_body(plan='Enterprise'), format='json').data['id']
            make_admin().post(f'{ADMIN}{pay_id}/approve/')
        sub = sub_of('u-co')
        self.assertEqual((sub.plan.name, sub.next_plan_id), ('Enterprise', None))

    def test_needs_manage_billing(self):
        give_role(self.company.id, add_employee(self.ceo, 'v@u.com', 'U-3')['id'], ['view_billing'], 'Billing viewer')
        with self.run_at(15):
            self.assertEqual(login_as('v@u.com').post(DOWNGRADE, {'plan': 'Basic'}, format='json').status_code, 403)
