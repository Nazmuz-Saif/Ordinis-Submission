"""ST-148: the Platform Admin's subscriptions list (days left, filters, order) and the pending-payments count."""
import datetime

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from billing.models import Subscription
from billing.test_payments import ADMIN, PAYMENTS, body, code, make_admin, waiting_company
from billing.test_subscription import at, end_on
from core.test_utils import login_as, register_company, rows
from tenants.models import Company, CompanySettings

D = datetime.date
SUBS = '/api/v1/platform-admin/admin/subscriptions/'
COUNT = '/api/v1/platform-admin/admin/payments/pending-count/'
TODAY = D(2026, 11, 10)


def company_with_end(subdomain, end, status=Subscription.STATUS_ACTIVE):
    register_company(subdomain.upper(), subdomain, f'ceo@{subdomain}.com')
    end_on(subdomain, end, status=status)


class SubscriptionListTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        company_with_end('far', D(2027, 6, 1))                          # 203 days left
        company_with_end('soon', D(2026, 11, 15))                       # 5 days left: expiring
        company_with_end('today', D(2026, 11, 10))                      # 0 days left: expiring
        company_with_end('grace', D(2026, 11, 8))                       # -2: grace, still working, expiring
        company_with_end('late', D(2026, 10, 20), status=Subscription.STATUS_EXPIRED)   # expired
        waiting_company('new', 'ceo@new.com')                            # waiting for the first payment

    def get(self, **params):
        with at(TODAY):
            return self.admin.get(SUBS, params)

    def test_sorted_by_days_left_with_the_waiting_company_last(self):
        names = [r['company_subdomain'] for r in rows(self.get())]
        self.assertEqual(names, ['late', 'grace', 'today', 'soon', 'far', 'new'])

    def test_each_row_has_the_plan_state_end_date_and_days_left(self):
        by = {r['company_subdomain']: r for r in rows(self.get())}
        self.assertEqual((by['soon']['days_left'], by['soon']['status'], by['soon']['restricted']), (5, 'active', False))
        self.assertEqual((by['today']['days_left'], by['today']['status']), (0, 'active'))
        self.assertEqual((by['grace']['days_left'], by['grace']['status'], by['grace']['restricted']), (-2, 'grace', False))
        self.assertEqual((by['late']['days_left'], by['late']['status'], by['late']['restricted']), (-21, 'expired', True))
        self.assertEqual((by['new']['days_left'], by['new']['status'], by['new']['restricted']), (None, 'pending_payment', True))
        self.assertEqual(by['soon']['plan_name'], 'Basic')
        self.assertEqual(by['soon']['period_end'], D(2026, 11, 15))
        self.assertEqual(by['soon']['company_name'], 'SOON')
        self.assertFalse(by['soon']['company_suspended'])

    def test_the_expiring_filter_is_seven_days_or_fewer_and_still_working(self):
        names = [r['company_subdomain'] for r in rows(self.get(filter='expiring'))]
        self.assertEqual(names, ['grace', 'today', 'soon'])               # not far, not expired, not waiting

    def test_the_seventh_day_counts_and_the_eighth_does_not(self):
        company_with_end('seven', D(2026, 11, 17))
        company_with_end('eight', D(2026, 11, 18))
        names = [r['company_subdomain'] for r in rows(self.get(filter='expiring'))]
        self.assertIn('seven', names)
        self.assertNotIn('eight', names)

    def test_the_restricted_filter_is_expired_or_waiting(self):
        names = [r['company_subdomain'] for r in rows(self.get(filter='restricted'))]
        self.assertEqual(names, ['late', 'new'])

    def test_a_company_past_its_grace_is_listed_as_expired_even_if_the_job_never_ran(self):
        company_with_end('lapsed', D(2026, 11, 1))                        # stored active, 9 days past the end
        by = {r['company_subdomain']: r for r in rows(self.get())}
        self.assertEqual((by['lapsed']['status'], by['lapsed']['restricted']), ('expired', True))
        self.assertIn('lapsed', [r['company_subdomain'] for r in rows(self.get(filter='restricted'))])

    def test_days_left_use_each_companys_own_time_zone(self):
        CompanySettings.objects.filter(company__subdomain='today').update(timezone='America/New_York')
        with at(D(2026, 11, 10), hour=20):       # already 11 Nov in Dhaka, still 10 Nov in New York
            by = {r['company_subdomain']: r for r in rows(self.admin.get(SUBS))}
        self.assertEqual(by['today']['days_left'], 0)
        self.assertEqual(by['soon']['days_left'], 4)          # Dhaka is a day ahead

    def test_search_by_name(self):
        self.assertEqual([r['company_subdomain'] for r in rows(self.get(q='SOO'))], ['soon'])
        self.assertEqual(rows(self.get(q='nothing like this')), [])

    def test_a_suspended_company_is_marked(self):
        Company.objects.filter(subdomain='far').update(is_active=False)
        by = {r['company_subdomain']: r for r in rows(self.get())}
        self.assertTrue(by['far']['company_suspended'])

    def test_the_list_is_paginated(self):
        with at(TODAY):
            res = self.admin.get(SUBS, {'page_size': 2})
        self.assertEqual(len(res.data['data']), 2)
        self.assertEqual(res.data['pagination']['count'], 6)
        self.assertIsNotNone(res.data['pagination']['next'])

    def test_the_query_count_does_not_grow_with_the_number_of_companies(self):
        def queries():
            with at(TODAY), CaptureQueriesContext(connection) as ctx:
                self.admin.get(SUBS)
            return len(ctx)
        before = queries()
        for n in range(6):
            company_with_end(f'extra{n}', D(2026, 12, 1 + n))
        self.assertEqual(queries(), before)


class SubscriptionAccessTests(TestCase):
    def test_only_a_platform_admin_can_open_it(self):
        ceo = register_company('A Co', 'a-co', 'ceo@a.com')
        for url in (SUBS, COUNT):
            self.assertEqual(ceo.get(url).status_code, 403, url)
        from rest_framework.test import APIClient
        self.assertEqual(APIClient().get(SUBS).status_code, 401)
        self.assertEqual(APIClient().get(COUNT).status_code, 401)
        make_admin()
        self.assertEqual(login_as('root@x.com').get(SUBS).status_code, 200)


class PendingCountTests(TestCase):
    def test_counts_only_pending_payments_and_follows_every_decision(self):
        admin = make_admin()
        self.assertEqual(admin.get(COUNT).data['data']['count'], 0)
        ids = []
        for n in range(3):
            ceo = waiting_company(f'p{n}-co', f'ceo@p{n}.com')
            ids.append(ceo.post(PAYMENTS, body(transaction_id=f'COUNT000{n}X'), format='json').data['id'])
        self.assertEqual(admin.get(COUNT).data['data']['count'], 3)
        admin.post(f'{ADMIN}{ids[0]}/approve/', {}, format='json')
        self.assertEqual(admin.get(COUNT).data['data']['count'], 2)
        admin.post(f'{ADMIN}{ids[1]}/reject/', {'note': 'No match.'}, format='json')
        self.assertEqual(admin.get(COUNT).data['data']['count'], 1)
        self.assertEqual(admin.get(COUNT).status_code, 200)

    def test_the_payments_list_is_newest_first_and_filters_to_pending(self):
        admin = make_admin()
        first = waiting_company('f-co', 'ceo@f.com')
        pid1 = first.post(PAYMENTS, body(transaction_id='NEWEST0001'), format='json').data['id']
        second = waiting_company('g-co', 'ceo@g.com')
        pid2 = second.post(PAYMENTS, body(transaction_id='NEWEST0002'), format='json').data['id']
        admin.post(f'{ADMIN}{pid1}/approve/', {}, format='json')
        self.assertEqual([p['id'] for p in rows(admin.get(ADMIN))], [pid2, pid1])
        self.assertEqual([p['id'] for p in rows(admin.get(ADMIN, {'status': 'pending'}))], [pid2])
        detail = admin.get(f'{ADMIN}{pid1}/').data
        self.assertEqual((detail['status'], detail['invoice_number'] is not None, detail['period_end'] is not None), ('approved', True, True))
