"""ST-145: subscription period, days left, reminders, the daily job and restricted mode."""
import datetime
import io
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from billing import services
from billing.models import Subscription
from core.api_matrix import discover_routes
from core.test_utils import add_employee, give_role, login_as, register_company
from notifications.models import Notification
from organization.models import Employee
from tenants.models import Company, CompanySettings

D = datetime.date
NOW = datetime.datetime(2026, 11, 10, 12, 0, tzinfo=datetime.timezone.utc)   # 18:00 in Dhaka, same date there and in UTC


def at(day, hour=12):
    return mock.patch('attendance.services._now', return_value=datetime.datetime(day.year, day.month, day.day, hour, 0, tzinfo=datetime.timezone.utc))


def sub_of(subdomain):
    return Subscription.objects.get(company__subdomain=subdomain)


def end_on(subdomain, end, status=Subscription.STATUS_ACTIVE):
    sub = sub_of(subdomain)
    sub.current_period_start = end - datetime.timedelta(days=29)
    sub.current_period_end = end
    sub.status = status
    sub.reminders_sent = []
    sub.save()
    return sub


def notes(email, kind=Notification.KIND_BILLING_REMINDER):
    return Notification.objects.filter(recipient__user__email=email, kind=kind)


class PeriodMathTests(TestCase):
    def test_add_months_cuts_to_the_last_day_of_a_short_month(self):
        self.assertEqual(services.add_months(D(2026, 1, 31), 1), D(2026, 2, 28))
        self.assertEqual(services.add_months(D(2028, 1, 31), 1), D(2028, 2, 29))
        self.assertEqual(services.add_months(D(2026, 11, 15), 3), D(2027, 2, 15))
        self.assertEqual(services.add_months(D(2026, 12, 1), 1), D(2027, 1, 1))

    def test_the_period_ends_on_the_day_before_the_next_one_starts(self):
        self.assertEqual(services.period_end_for(D(2026, 1, 1), 1), D(2026, 1, 31))
        self.assertEqual(services.period_end_for(D(2026, 1, 15), 12), D(2027, 1, 14))
        self.assertEqual(services.period_end_for(D(2026, 1, 1), 36), D(2028, 12, 31))

    def test_a_new_company_is_active_with_a_twelve_month_period(self):
        register_company('P Co', 'p-co', 'a@p.com')
        sub = sub_of('p-co')
        self.assertEqual(sub.status, Subscription.STATUS_ACTIVE)
        self.assertEqual(sub.billing_months, 12)
        self.assertEqual(sub.current_period_end, services.period_end_for(sub.current_period_start, 12))
        self.assertEqual(sub.reminders_sent, [])


class DaysLeftTests(TestCase):
    def setUp(self):
        register_company('D Co', 'd-co', 'a@d.com')
        self.sub = end_on('d-co', D(2026, 11, 10))

    def test_boundary_days(self):
        for today, left in [(D(2026, 11, 9), 1), (D(2026, 11, 10), 0), (D(2026, 11, 11), -1), (D(2026, 11, 3), 7)]:
            with at(today):
                self.assertEqual(services.days_left(self.sub), left, today)

    def test_days_left_follow_the_company_time_zone(self):
        # 20:00 UTC on 10 Nov is already 11 Nov 02:00 in Dhaka (UTC+6), but still 10 Nov in New York.
        with at(D(2026, 11, 10), hour=20):
            self.assertEqual(services.days_left(self.sub), -1)          # Asia/Dhaka (the default)
            CompanySettings.objects.filter(company__subdomain='d-co').update(timezone='America/New_York')
            self.assertEqual(services.days_left(self.sub), 0)

    def test_nothing_is_stored_for_days_left(self):
        self.assertNotIn('days_left', [f.name for f in Subscription._meta.get_fields()])

    def test_states_around_the_end_and_the_grace_period(self):
        cases = [
            (D(2026, 11, 10), services.STATE_ACTIVE),
            (D(2026, 11, 11), services.STATE_GRACE),
            (D(2026, 11, 13), services.STATE_GRACE),      # the 3rd grace day still works
            (D(2026, 11, 14), services.STATE_EXPIRED),    # restricted from the 4th day
        ]
        for today, state in cases:
            with at(today):
                self.assertEqual(services.effective_state(self.sub), state, today)
                self.assertEqual(services.is_restricted(self.sub), state == services.STATE_EXPIRED, today)

    def test_pending_payment_and_expired_are_restricted_whatever_the_dates(self):
        for status in (Subscription.STATUS_PENDING_PAYMENT, Subscription.STATUS_EXPIRED):
            self.sub.status = status
            self.assertTrue(services.is_restricted(self.sub, D(2026, 11, 1)))


class DailyJobTests(TestCase):
    def setUp(self):
        self.ceo = register_company('J Co', 'j-co', 'ceo@j.com')
        self.billing_holder = add_employee(self.ceo, 'bill@j.com', 'J-2')
        give_role(self.ceo.company_id, self.billing_holder['id'], ['view_billing'], 'Billing')
        add_employee(self.ceo, 'plain@j.com', 'J-3')
        self.sub = end_on('j-co', D(2026, 11, 20))

    def run_job(self, today):
        with at(today):
            return services.process_subscriptions()

    def test_a_reminder_goes_to_the_ceo_and_billing_holders_only_once_per_threshold(self):
        result = self.run_job(D(2026, 11, 13))             # 7 days left
        self.assertEqual(result['reminded'], 1)
        self.assertEqual(notes('ceo@j.com').count(), 1)
        self.assertEqual(notes('bill@j.com').count(), 1)
        self.assertEqual(notes('plain@j.com').count(), 0)
        self.assertEqual(self.run_job(D(2026, 11, 13))['reminded'], 0)     # the second run changes nothing
        self.assertEqual(self.run_job(D(2026, 11, 14))['reminded'], 0)     # 6 days left: no new threshold
        self.assertEqual(notes('ceo@j.com').count(), 1)

    def test_every_threshold_sends_one_reminder(self):
        for today in (D(2026, 11, 13), D(2026, 11, 17), D(2026, 11, 19)):    # 7, 3, 1 days left
            self.run_job(today)
            self.run_job(today)
        self.assertEqual(notes('ceo@j.com').count(), 3)
        self.assertEqual(sorted(sub_of('j-co').reminders_sent), [1, 3, 7])
        titles = [n.title for n in notes('ceo@j.com').order_by('created_at')]
        self.assertIn('7 days', titles[0])
        self.assertIn('1 day', titles[2])

    def test_a_missed_day_still_gets_one_reminder_and_no_duplicates(self):
        self.run_job(D(2026, 11, 15))                       # 5 days left, the 7-day run never happened
        self.assertEqual(notes('ceo@j.com').count(), 1)
        self.run_job(D(2026, 11, 15))
        self.assertEqual(notes('ceo@j.com').count(), 1)
        self.run_job(D(2026, 11, 19))                       # 1 day left: 3 and 1 are due, one message for both
        self.assertEqual(notes('ceo@j.com').count(), 2)
        self.assertEqual(sorted(sub_of('j-co').reminders_sent), [1, 3, 7])

    def test_no_reminder_far_from_the_end_or_after_it(self):
        self.assertEqual(self.run_job(D(2026, 11, 1))['reminded'], 0)
        self.assertEqual(self.run_job(D(2026, 11, 22))['reminded'], 0)      # in the grace period
        self.assertEqual(notes('ceo@j.com').count(), 0)

    def test_it_expires_only_after_the_grace_period_and_only_once(self):
        self.assertEqual(self.run_job(D(2026, 11, 23))['expired'], 0)       # the 3rd grace day
        self.assertEqual(sub_of('j-co').status, Subscription.STATUS_ACTIVE)
        self.assertEqual(self.run_job(D(2026, 11, 24))['expired'], 1)
        self.assertEqual(sub_of('j-co').status, Subscription.STATUS_EXPIRED)
        again = self.run_job(D(2026, 11, 24))
        self.assertEqual((again['checked'], again['expired']), (0, 0))      # no longer an active subscription

    def test_a_suspended_company_gets_no_reminder(self):
        Company.objects.filter(subdomain='j-co').update(is_active=False)
        self.assertEqual(self.run_job(D(2026, 11, 13))['reminded'], 0)
        self.assertEqual(Notification.objects.filter(kind=Notification.KIND_BILLING_REMINDER).count(), 0)

    def test_one_failing_company_does_not_stop_the_others(self):
        register_company('K Co', 'k-co', 'ceo@k.com')
        end_on('k-co', D(2026, 11, 20))
        real = services.send_reminder

        def flaky(subscription, left):
            if subscription.company.subdomain == 'j-co':
                raise RuntimeError('boom')
            return real(subscription, left)

        with mock.patch.object(services, 'send_reminder', flaky), self.assertLogs('billing.services', 'ERROR'):
            result = self.run_job(D(2026, 11, 13))
        self.assertEqual((result['errors'], result['reminded']), (1, 1))
        self.assertEqual(notes('ceo@k.com').count(), 1)
        self.assertEqual(notes('ceo@j.com').count(), 0)
        self.assertEqual(sub_of('j-co').reminders_sent, [])          # the failed company is retried next run

    def test_a_new_period_starts_with_no_reminders_sent(self):
        self.run_job(D(2026, 11, 13))
        sub = sub_of('j-co')
        services.set_period(sub, D(2026, 11, 21), 1)
        sub.save()
        self.assertEqual(sub.reminders_sent, [])
        self.assertEqual(sub.current_period_end, D(2026, 12, 20))

    def test_the_command_runs_and_reports(self):
        out = io.StringIO()
        with at(D(2026, 11, 13)):
            call_command('process_subscriptions', stdout=out)
        self.assertIn('1 reminder(s) sent', out.getvalue())


class RestrictedModeTests(TestCase):
    OPEN_PREFIXES = ('/api/v1/billing/plans', '/api/v1/billing/subscription', '/api/v1/billing/invoices',
                     '/api/v1/platform-admin/company/tickets', '/api/v1/auth/')

    def setUp(self):
        self.ceo = register_company('R Co', 'r-co', 'ceo@r.com')

    def restrict(self, status=Subscription.STATUS_EXPIRED):
        sub = sub_of('r-co')
        sub.status = status
        sub.save()

    def code(self, res):
        return ((res.data or {}).get('error') or {}).get('code') if isinstance(res.data, dict) else None

    def test_an_active_company_is_not_restricted(self):
        self.assertEqual(self.ceo.get('/api/v1/organization/departments/').status_code, 200)

    def test_restricted_company_can_still_log_in_and_pay_but_nothing_else(self):
        for status in (Subscription.STATUS_EXPIRED, Subscription.STATUS_PENDING_PAYMENT):
            self.restrict(status)
            me = login_as('ceo@r.com')
            for url in ('/api/v1/organization/departments/', '/api/v1/tasks/tasks/', '/api/v1/analytics/overview/',
                        '/api/v1/notifications/', '/api/v1/dashboard/summary/'):
                res = me.get(url)
                self.assertEqual((res.status_code, self.code(res)), (403, 'SUBSCRIPTION_RESTRICTED'), (status, url))
            for url in ('/api/v1/billing/plans/', '/api/v1/billing/subscription/', '/api/v1/billing/invoices/',
                        '/api/v1/platform-admin/company/tickets/', '/api/v1/auth/me/', '/api/v1/auth/profile/'):
                self.assertEqual(me.get(url).status_code, 200, (status, url))

    def test_a_ticket_can_still_be_sent_while_restricted(self):
        self.restrict()
        res = self.ceo.post('/api/v1/platform-admin/company/tickets/', {'subject': 'Payment help', 'description': 'We paid by bKash.'}, format='json')
        self.assertEqual(res.status_code, 201, res.content)

    def test_change_password_and_logout_still_work_while_restricted(self):
        self.restrict()
        res = login_as('ceo@r.com').post('/api/v1/auth/change-password/', {
            'current_password': 'StrongPass123', 'new_password': 'Brand-New-Pass-7391', 'confirm_password': 'Brand-New-Pass-7391',
        }, format='json')
        self.assertEqual(res.status_code, 200, res.content)

    def test_me_tells_the_frontend(self):
        data = self.ceo.get('/api/v1/auth/me/').data['data']['subscription']
        self.assertEqual((data['status'], data['restricted']), ('active', False))
        self.restrict()
        data = self.ceo.get('/api/v1/auth/me/').data['data']['subscription']
        self.assertEqual((data['status'], data['restricted']), ('expired', True))
        self.assertIn('days_left', data)

    def test_a_company_past_its_end_is_restricted_even_if_the_job_never_ran(self):
        with at(D(2026, 11, 10)):
            end_on('r-co', D(2026, 11, 5))                  # 5 days past the end: grace (3) is over
            res = login_as('ceo@r.com').get('/api/v1/organization/departments/')
            self.assertEqual((res.status_code, self.code(res)), (403, 'SUBSCRIPTION_RESTRICTED'))
            self.assertEqual(sub_of('r-co').status, Subscription.STATUS_ACTIVE)   # the stored status was never touched

    def test_the_grace_period_still_works_with_a_warning_state(self):
        with at(D(2026, 11, 10)):
            end_on('r-co', D(2026, 11, 8))                  # 2 days past the end
            me = login_as('ceo@r.com')
            self.assertEqual(me.get('/api/v1/organization/departments/').status_code, 200)
            data = me.get('/api/v1/auth/me/').data['data']['subscription']
            self.assertEqual((data['status'], data['restricted'], data['days_left']), ('grace', False, -2))

    def test_suspend_still_blocks_login_completely(self):
        Company.objects.filter(subdomain='r-co').update(is_active=False)
        res = APIClient().post('/api/v1/auth/login/', {'email': 'ceo@r.com', 'password': 'StrongPass123'}, format='json')
        self.assertEqual(res.status_code, 400)          # the specific suspended-company message (FR-3)
        self.assertNotIn('access', res.data)             # no token is issued
        self.assertNotEqual(self.code(res), 'SUBSCRIPTION_RESTRICTED')

    def test_another_company_is_not_affected(self):
        other = register_company('O Co', 'o-co', 'ceo@o.com')
        self.restrict()
        self.assertEqual(other.get('/api/v1/organization/departments/').status_code, 200)

    def test_an_employee_is_restricted_too(self):
        add_employee(self.ceo, 'emp@r.com', 'R-2')
        self.restrict()
        res = login_as('emp@r.com').get('/api/v1/tasks/tasks/')
        self.assertEqual((res.status_code, self.code(res)), (403, 'SUBSCRIPTION_RESTRICTED'))

    def test_the_check_adds_a_fixed_number_of_queries(self):
        me = login_as('ceo@r.com')
        me.get('/api/v1/organization/departments/')
        with self.assertNumQueries(self.queries(me)):
            me.get('/api/v1/organization/departments/')

    def queries(self, client):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx:
            client.get('/api/v1/organization/departments/')
        return len(ctx)


class GateCoversEveryCompanyRouteTests(TestCase):
    """A route that forgot the gate would stay open to a restricted company without a sound, so every route is tried."""

    def test_every_company_route_except_the_allow_list_answers_subscription_restricted(self):
        ceo = register_company('G Co', 'g-co', 'ceo@g.com')
        Subscription.objects.filter(company__subdomain='g-co').update(status=Subscription.STATUS_EXPIRED)
        me = login_as('ceo@g.com')
        checked, failures = 0, []
        for route in discover_routes():
            names = route.permission_class_names()
            if 'AllowAny' in names or 'IsPlatformAdmin' in names or route.url().startswith('/api/v1/auth/'):
                continue
            allowed = route.url().startswith(RestrictedModeTests.OPEN_PREFIXES)
            for method in route.methods:
                res = me.generic(method, route.url())
                code = (res.data or {}).get('error', {}).get('code') if isinstance(getattr(res, 'data', None), dict) else None
                restricted = res.status_code == 403 and code == 'SUBSCRIPTION_RESTRICTED'
                checked += 1
                if restricted == allowed:
                    failures.append(f'{route.label(method)} -> {res.status_code} {code} (allow-list: {allowed})')
        self.assertGreater(checked, 80)
        self.assertEqual(failures, [], '\n' + '\n'.join(failures))


class MigrationAndSeedTests(TestCase):
    def test_the_demo_company_is_active_with_a_long_period_and_stays_so_when_seeded_twice(self):
        from core import demo
        demo.seed_demo_data() if hasattr(demo, 'seed_demo_data') else call_command('seed_demo_data', stdout=io.StringIO())
        call_command('seed_demo_data', stdout=io.StringIO())
        for sub in Subscription.objects.all():
            self.assertEqual(sub.status, Subscription.STATUS_ACTIVE)
            self.assertFalse(services.is_restricted(sub))
            self.assertGreater(sub.current_period_end - datetime.date.today(), datetime.timedelta(days=60))
