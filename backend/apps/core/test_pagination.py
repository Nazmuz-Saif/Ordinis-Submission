from django.test import TestCase

from core.test_utils import add_employee, login_as, register_company, rows

DEPARTMENTS = '/api/v1/organization/departments/'
EMPLOYEES = '/api/v1/organization/employees/'


class PaginationTests(TestCase):
    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        for i in range(25):
            res = self.ceo.post(DEPARTMENTS, {'name': f'Dept {i:02d}'}, format='json')
            assert res.status_code == 201, res.content

    def test_first_page_has_twenty_items_and_a_next_link(self):
        res = self.ceo.get(DEPARTMENTS)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data['success'])
        self.assertEqual(len(res.data['data']), 20)
        self.assertEqual(res.data['pagination']['count'], 25)
        self.assertIsNotNone(res.data['pagination']['next'])
        self.assertIsNone(res.data['pagination']['previous'])

    def test_second_page_has_the_rest_and_no_next_link(self):
        res = self.ceo.get(DEPARTMENTS + '?page=2')
        self.assertEqual(len(res.data['data']), 5)
        self.assertIsNone(res.data['pagination']['next'])
        self.assertIsNotNone(res.data['pagination']['previous'])

    def test_pages_do_not_overlap_and_are_in_a_stable_order(self):
        first = [d['name'] for d in rows(self.ceo.get(DEPARTMENTS))]
        second = [d['name'] for d in rows(self.ceo.get(DEPARTMENTS + '?page=2'))]
        self.assertEqual(first + second, sorted(first + second))
        self.assertEqual(len(set(first + second)), 25)

    def test_page_size_can_be_changed_but_is_capped_at_100(self):
        self.assertEqual(len(rows(self.ceo.get(DEPARTMENTS + '?page_size=5'))), 5)
        self.assertEqual(self.ceo.get(DEPARTMENTS + '?page_size=1000').data['pagination']['count'], 25)
        self.assertEqual(len(rows(self.ceo.get(DEPARTMENTS + '?page_size=1000'))), 25)

    def test_page_beyond_the_end_is_404(self):
        self.assertEqual(self.ceo.get(DEPARTMENTS + '?page=9').status_code, 404)

    def test_count_only_counts_my_company(self):
        other = register_company('Beta', 'beta', 'ceo@beta.com')
        res = other.get(DEPARTMENTS)
        self.assertEqual(res.data['pagination']['count'], 0)
        self.assertEqual(rows(res), [])

    def test_employee_list_and_subordinates_are_paginated(self):
        for i in range(21):
            add_employee(self.ceo, f'e{i}@acme.com', f'ACME-{i + 10:03d}', reports_to=self.ceo.employee_id)
        res = self.ceo.get(EMPLOYEES)
        self.assertEqual(len(res.data['data']), 20)
        self.assertEqual(res.data['pagination']['count'], 22)
        team = self.ceo.get(f'{EMPLOYEES}{self.ceo.employee_id}/subordinates/')
        self.assertEqual(len(team.data['data']), 20)
        self.assertEqual(team.data['pagination']['count'], 21)

    def test_anonymous_user_gets_no_list(self):
        from rest_framework.test import APIClient
        self.assertIn(APIClient().get(DEPARTMENTS).status_code, (401, 403))
