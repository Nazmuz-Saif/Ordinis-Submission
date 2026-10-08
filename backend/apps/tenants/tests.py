from django.test import TestCase

from core.test_utils import add_employee, give_role, login_as, register_company, rows

SETTINGS = '/api/v1/tenants/settings/'


class CompanySettingsTests(TestCase):
    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.emp = add_employee(self.ceo, 'emp@acme.com', 'ACME-002')
        self.emp_c = login_as('emp@acme.com')
        self.beta = register_company('Beta', 'beta', 'ceo@beta.com')

    def _id(self, client):
        return rows(client.get(SETTINGS))[0]['id']

    def test_every_employee_can_read_own_company_settings(self):
        res = self.emp_c.get(SETTINGS)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(rows(res)), 1)
        self.assertEqual(rows(res)[0]['currency'], 'BDT')

    def test_employee_without_permission_cannot_change_settings(self):
        sid = self._id(self.emp_c)
        res = self.emp_c.patch(f'{SETTINGS}{sid}/', {'currency': 'USD'}, format='json')
        self.assertEqual(res.status_code, 403)
        self.assertEqual(rows(self.ceo.get(SETTINGS))[0]['currency'], 'BDT')

    def test_ceo_admin_role_can_change_settings(self):
        sid = self._id(self.ceo)
        res = self.ceo.patch(f'{SETTINGS}{sid}/', {'currency': 'USD'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['currency'], 'USD')

    def test_employee_with_the_permission_can_change_settings(self):
        give_role(self.ceo.company_id, self.emp['id'], ['manage_company_settings'])
        sid = self._id(self.emp_c)
        res = self.emp_c.patch(f'{SETTINGS}{sid}/', {'timezone': 'Asia/Kolkata'}, format='json')
        self.assertEqual(res.status_code, 200)

    def test_nobody_can_create_or_delete_settings(self):
        sid = self._id(self.ceo)
        self.assertEqual(self.ceo.post(SETTINGS, {'currency': 'USD'}, format='json').status_code, 405)
        self.assertEqual(self.ceo.delete(f'{SETTINGS}{sid}/').status_code, 405)

    def test_other_company_settings_are_404_and_untouched(self):
        sid = self._id(self.ceo)
        res = self.beta.patch(f'{SETTINGS}{sid}/', {'currency': 'USD'}, format='json')
        self.assertEqual(res.status_code, 404)
        self.assertEqual(rows(self.ceo.get(SETTINGS))[0]['currency'], 'BDT')
