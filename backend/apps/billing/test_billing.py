import datetime
import io
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from billing import services
from billing.models import Invoice, Subscription, SubscriptionPlan
from core import demo
from core.test_utils import add_employee, give_role, login_as, register_company, rows
from organization.models import Employee
from tenants.models import Company

EMPLOYEES = '/api/v1/organization/employees/'
BILLING = '/api/v1/billing/'


def company(subdomain):
    return Company.objects.get(subdomain=subdomain)


def fill_to(ceo, total, prefix='x'):
    """Add employees until the company has `total`. The CEO counts as one."""
    have = Employee.objects.filter(company_id=ceo.company_id).count()
    for n in range(total - have):
        add_employee(ceo, f'{prefix}{have + n}@{prefix}.com', f'{prefix.upper()}-{have + n:03d}')


class PlanSeedTests(TestCase):
    def test_the_three_plans_exist_with_their_limits(self):
        plans = {p.name: p for p in SubscriptionPlan.objects.all()}
        self.assertEqual({n: p.max_employees for n, p in plans.items()}, {'Basic': 10, 'Professional': 50, 'Enterprise': None})
        self.assertTrue(all(p.price_monthly > 0 for p in plans.values()))
        self.assertLess(plans['Basic'].price_monthly, plans['Professional'].price_monthly)
        self.assertLess(plans['Professional'].price_monthly, plans['Enterprise'].price_monthly)

    def test_seeding_again_changes_nothing(self):
        before = list(SubscriptionPlan.objects.values_list('id', flat=True))
        services.seed_plans()
        self.assertEqual(list(SubscriptionPlan.objects.values_list('id', flat=True)), before)

    def test_a_new_company_starts_on_basic_and_the_sidebar_badge_gets_the_name(self):
        ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.assertEqual(company('acme').subscription.plan.name, 'Basic')
        me = ceo.get('/api/v1/auth/me/').json()
        self.assertEqual((me.get('data') or me)['plan_name'], 'Basic')

    def test_a_company_that_has_no_subscription_yet_is_put_on_basic(self):
        orphan = Company.objects.create(name='Old Co', subdomain='old-co')
        self.assertFalse(Subscription.objects.filter(company=orphan).exists())
        self.assertEqual(services.get_subscription(orphan).plan.name, 'Basic')


class LimitTests(TestCase):
    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')

    def create(self, n):
        return self.ceo.post(EMPLOYEES, {'email': f'n{n}@acme.com', 'password': 'StrongPass123', 'employee_code': f'N-{n:03d}'}, format='json')

    def test_exactly_full_is_allowed_and_one_more_is_refused_with_an_upgrade_message(self):
        for n in range(9):                       # the CEO is the 1st: 9 more make exactly 10
            self.assertEqual(self.create(n).status_code, 201, n)
        self.assertEqual(Employee.objects.filter(company=company('acme')).count(), 10)
        users, people = User.objects.count(), Employee.objects.count()
        res = self.create(99)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data['error']['code'], 'PLAN_LIMIT_REACHED')
        self.assertIn('Upgrade your plan', res.data['error']['message'])
        self.assertIn('Basic', res.data['error']['message'])
        self.assertIn('10', res.data['error']['message'])
        self.assertEqual((User.objects.count(), Employee.objects.count()), (users, people), 'nothing was created')

    def test_the_check_is_in_the_serializer_so_every_creation_path_is_covered(self):
        fill_to(self.ceo, 10)
        with self.assertRaises(services.PlanLimitError):
            services.ensure_can_add_employee(company('acme'))
        self.assertFalse(services.can_add_employee(company('acme')))

    def test_removing_an_employee_frees_a_seat(self):
        fill_to(self.ceo, 10)
        self.assertEqual(self.create(1).status_code, 400)
        victim = Employee.objects.filter(company=company('acme')).exclude(user__email='ceo@acme.com').first()
        self.assertEqual(self.ceo.delete(f'{EMPLOYEES}{victim.id}/').status_code, 204)
        self.assertEqual(self.create(2).status_code, 201)

    def test_a_bigger_plan_lifts_the_limit_and_enterprise_has_none(self):
        fill_to(self.ceo, 10)
        services.change_plan(company('acme'), 'Professional')
        self.assertEqual(self.create(1).status_code, 201)
        fill_to(self.ceo, 50)
        self.assertEqual(self.create(2).status_code, 400)
        services.change_plan(company('acme'), 'Enterprise')
        self.assertEqual(self.create(3).status_code, 201)
        self.assertEqual(services.usage(company('acme'))['unlimited'], True)

    def test_a_plan_too_small_for_the_team_is_refused(self):
        services.change_plan(company('acme'), 'Professional')
        fill_to(self.ceo, 12)
        with self.assertRaises(services.BillingError) as caught:
            services.change_plan(company('acme'), 'Basic')
        self.assertEqual(caught.exception.code, 'PLAN_TOO_SMALL')
        self.assertEqual(company('acme').subscription.plan.name, 'Professional')

    def test_an_unknown_plan_is_refused(self):
        with self.assertRaises(services.BillingError):
            services.change_plan(company('acme'), 'Platinum')

    def test_the_limit_is_per_company(self):
        other = register_company('Beta', 'beta', 'ceo@beta.com')
        fill_to(self.ceo, 10)
        self.assertEqual(self.create(1).status_code, 400)
        res = other.post(EMPLOYEES, {'email': 'n@beta.com', 'password': 'StrongPass123', 'employee_code': 'B-002'}, format='json')
        self.assertEqual(res.status_code, 201)

    def test_updating_an_existing_employee_is_never_blocked_by_the_limit(self):
        fill_to(self.ceo, 10)
        person = Employee.objects.filter(company=company('acme')).exclude(user__email='ceo@acme.com').first()
        res = self.ceo.patch(f'{EMPLOYEES}{person.id}/', {'employee_code': 'CHANGED-1'}, format='json')
        self.assertEqual(res.status_code, 200, res.content)


class UsageTests(TestCase):
    def test_usage_numbers(self):
        ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        fill_to(ceo, 5)
        body = ceo.get(BILLING + 'subscription/').json()
        data = body.get('data', body)
        self.assertEqual(data['plan']['name'], 'Basic')
        self.assertEqual(data['plan']['max_employees'], 10)
        self.assertEqual(Decimal(str(data['plan']['price_monthly'])), Decimal('1500.00'))
        self.assertEqual(data['usage'], {'employees': 5, 'limit': 10, 'unlimited': False, 'remaining': 5, 'percent': 50, 'is_full': False})
        fill_to(ceo, 10)
        usage = ceo.get(BILLING + 'subscription/').json()
        usage = (usage.get('data') or usage)['usage']
        self.assertEqual((usage['percent'], usage['is_full'], usage['remaining']), (100, True, 0))

    def test_enterprise_usage_has_no_limit(self):
        ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        services.change_plan(company('acme'), 'Enterprise')
        usage = ceo.get(BILLING + 'subscription/').json()
        usage = (usage.get('data') or usage)['usage']
        self.assertEqual((usage['limit'], usage['unlimited'], usage['remaining'], usage['percent'], usage['is_full']), (None, True, None, 0, False))


class AccessTests(TestCase):
    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.other = register_company('Beta', 'beta', 'ceo@beta.com')
        for sub in ('acme', 'beta'):
            subscription = services.get_subscription(company(sub))
            services.generate_invoice(subscription, 2026, 8)
            services.generate_invoice(subscription, 2026, 9)
        add_employee(self.ceo, 'plain@acme.com', 'P-1')
        self.plain = login_as('plain@acme.com')

    def test_without_the_permission_nothing_is_visible(self):
        for path in ('plans/', 'subscription/', 'invoices/'):
            self.assertEqual(self.plain.get(BILLING + path).status_code, 403, path)

    def test_with_the_permission_it_is_visible(self):
        person = Employee.objects.get(user__email='plain@acme.com')
        give_role(self.ceo.company_id, str(person.id), ['view_billing'], 'Billing viewer')
        client = login_as('plain@acme.com')
        for path in ('plans/', 'subscription/', 'invoices/'):
            self.assertEqual(client.get(BILLING + path).status_code, 200, path)

    def test_the_ceo_has_the_permission(self):
        self.assertEqual(self.ceo.get(BILLING + 'invoices/').status_code, 200)

    def test_a_login_is_required(self):
        self.assertEqual(APIClient().get(BILLING + 'invoices/').status_code, 401)

    def test_a_company_sees_only_its_own_invoices(self):
        mine = rows(self.ceo.get(BILLING + 'invoices/'))
        theirs = rows(self.other.get(BILLING + 'invoices/'))
        self.assertEqual(len(mine), 2)
        self.assertEqual({r['id'] for r in mine} & {r['id'] for r in theirs}, set())

    def test_another_companys_invoice_is_a_404(self):
        theirs = Invoice.objects.filter(company=company('beta')).first()
        self.assertEqual(self.ceo.get(f'{BILLING}invoices/{theirs.id}/').status_code, 404)
        self.assertEqual(self.other.get(f'{BILLING}invoices/{theirs.id}/').status_code, 200)

    def test_nobody_can_write_through_the_api(self):
        mine = Invoice.objects.filter(company=company('acme')).first()
        for method, url in (('post', 'invoices/'), ('patch', f'invoices/{mine.id}/'), ('delete', f'invoices/{mine.id}/'),
                            ('post', 'subscription/'), ('post', 'plans/'), ('put', 'subscription/')):
            self.assertIn(getattr(self.ceo, method)(BILLING + url, {}, format='json').status_code, (404, 405), f'{method} {url}')
        self.assertEqual(company('acme').subscription.plan.name, 'Basic', 'a company cannot change its own plan')

    def test_a_platform_admin_has_no_access_to_a_companys_billing(self):
        User.objects.create_user(email='root@x.com', password='StrongPass123', is_platform_admin=True)
        self.assertEqual(login_as('root@x.com').get(BILLING + 'invoices/').status_code, 403)

    def test_status_filter(self):
        invoice = Invoice.objects.filter(company=company('acme')).first()
        services.mark_paid(invoice)
        paid = rows(self.ceo.get(BILLING + 'invoices/?status=paid'))
        self.assertEqual([r['id'] for r in paid], [str(invoice.id)])


class InvoiceTests(TestCase):
    def setUp(self):
        register_company('Acme', 'acme', 'ceo@acme.com')
        self.subscription = company('acme').subscription

    def test_one_invoice_per_month_and_a_second_call_returns_the_same_one(self):
        first, made = services.generate_invoice(self.subscription, 2026, 9)
        again, made_again = services.generate_invoice(self.subscription, 2026, 9)
        self.assertEqual((made, made_again, first.id), (True, False, again.id))
        self.assertEqual(Invoice.objects.count(), 1)

    def test_the_invoice_has_the_month_the_amount_and_a_unique_number(self):
        invoice, _ = services.generate_invoice(self.subscription, 2026, 9)
        self.assertEqual((invoice.period_start, invoice.period_end), (datetime.date(2026, 9, 1), datetime.date(2026, 9, 30)))
        self.assertEqual((invoice.amount, invoice.status, invoice.plan_name), (Decimal('1500.00'), 'open', 'Basic'))
        self.assertEqual(invoice.due_on, datetime.date(2026, 9, 15))
        other, _ = services.generate_invoice(self.subscription, 2026, 10)
        self.assertNotEqual(invoice.number, other.number)
        self.assertRegex(invoice.number, r'^INV-202609-[0-9A-F]{6}$')

    def test_an_old_invoice_keeps_its_amount_when_the_plan_changes(self):
        old, _ = services.generate_invoice(self.subscription, 2026, 8)
        services.change_plan(company('acme'), 'Professional')
        new, _ = services.generate_invoice(company('acme').subscription, 2026, 9)
        old.refresh_from_db()
        self.assertEqual((old.amount, old.plan_name), (Decimal('1500.00'), 'Basic'))
        self.assertEqual((new.amount, new.plan_name), (Decimal('5000.00'), 'Professional'))

    def test_marking_paid_and_a_void_invoice_cannot_be_paid(self):
        invoice, _ = services.generate_invoice(self.subscription, 2026, 9)
        services.mark_paid(invoice, on=datetime.date(2026, 9, 3))
        self.assertEqual((invoice.status, invoice.paid_on), ('paid', datetime.date(2026, 9, 3)))
        invoice.status = 'void'
        invoice.save()
        with self.assertRaises(services.BillingError):
            services.mark_paid(invoice)

    def test_the_database_refuses_a_negative_amount(self):
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError), transaction.atomic():
            Invoice.objects.create(company=company('acme'), subscription=self.subscription, number='X', plan_name='Basic',
                                   period_start=datetime.date(2026, 1, 1), period_end=datetime.date(2026, 1, 31), amount=Decimal('-1'),
                                   issued_on=datetime.date(2026, 1, 1), due_on=datetime.date(2026, 1, 15))

    def test_the_generate_invoices_command_is_safe_to_run_twice(self):
        call_command('generate_invoices', '--month', '2026-07', stdout=io.StringIO())
        call_command('generate_invoices', '--month', '2026-07', stdout=io.StringIO())
        self.assertEqual(Invoice.objects.filter(period_start=datetime.date(2026, 7, 1)).count(), 1)


class CommandAndDemoTests(TestCase):
    def test_set_company_plan(self):
        register_company('Acme', 'acme', 'ceo@acme.com')
        call_command('set_company_plan', 'acme', 'Professional', stdout=io.StringIO())
        self.assertEqual(company('acme').subscription.plan.name, 'Professional')
        with self.assertRaises(CommandError):
            call_command('set_company_plan', 'acme', 'Nonsense', stdout=io.StringIO())
        with self.assertRaises(CommandError):
            call_command('set_company_plan', 'no-such-company', 'Basic', stdout=io.StringIO())

    def test_the_demo_company_is_on_basic_and_full_with_four_invoices(self):
        call_command('seed_demo_data', stdout=io.StringIO())
        demo_company = company(demo.SUBDOMAIN)
        self.assertEqual(demo_company.subscription.plan.name, 'Basic')
        usage = services.usage(demo_company)
        self.assertEqual((usage['employees'], usage['limit'], usage['is_full']), (10, 10, True))
        invoices = Invoice.objects.filter(company=demo_company)
        self.assertEqual(invoices.count(), 4)
        self.assertEqual(invoices.filter(status='paid').count(), 3)
        self.assertEqual(invoices.filter(status='open').count(), 1)

    def test_the_demo_loader_again_adds_no_invoice(self):
        call_command('seed_demo_data', stdout=io.StringIO())
        call_command('seed_demo_data', stdout=io.StringIO())
        self.assertEqual(Invoice.objects.filter(company=company(demo.SUBDOMAIN)).count(), 4)
