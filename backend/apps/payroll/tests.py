from rest_framework.test import APITestCase

from core.test_utils import add_employee, give_role, login_as, register_company

SALARIES = '/api/v1/payroll/salary-structures/'


def make(client, employee_id, base='50000', allowances=None, **extra):
    return client.post(SALARIES, {
        'employee': employee_id, 'base_salary': base,
        'allowances': allowances if allowances is not None else {'House Rent': 8000, 'Transport': 2000},
        **extra,
    }, format='json')


class SalaryStructureTests(APITestCase):

    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        cid = self.ceo.company_id
        self.accountant = add_employee(self.ceo, 'acc@acme.com', 'A-1')
        give_role(cid, self.accountant['id'], ['manage_finance'], 'Accountant')
        # a manager ABOVE the accountant in the hierarchy, but without the finance permission
        self.manager = add_employee(self.ceo, 'mgr@acme.com', 'M-1')
        self.worker = add_employee(self.ceo, 'worker@acme.com', 'W-1', reports_to=self.manager['id'])
        self.ceo.patch(f"/api/v1/organization/employees/{self.accountant['id']}/", {'reports_to': self.manager['id']}, format='json')
        self.acc_c, self.mgr_c = login_as('acc@acme.com'), login_as('mgr@acme.com')
        self.worker_c = login_as('worker@acme.com')

    # --- the finance permission is the only key --------------------------
    def test_everything_is_403_without_the_permission(self):
        salary = make(self.acc_c, self.worker['id']).data['id']
        for client in (self.worker_c, self.mgr_c):      # a plain employee and the accountant's own manager
            self.assertEqual(client.get(SALARIES).status_code, 403)
            self.assertEqual(client.get(f'{SALARIES}{salary}/').status_code, 403)
            self.assertEqual(make(client, self.worker['id']).status_code, 403)
            self.assertEqual(client.patch(f'{SALARIES}{salary}/', {'base_salary': '1'}, format='json').status_code, 403)
            self.assertEqual(client.delete(f'{SALARIES}{salary}/').status_code, 403)

    def test_employee_cannot_read_own_salary_structure_either(self):
        make(self.acc_c, self.worker['id'])
        self.assertEqual(self.worker_c.get(SALARIES).status_code, 403)

    def test_accountant_can_create_read_edit_delete(self):
        res = make(self.acc_c, self.worker['id'])
        self.assertEqual(res.status_code, 201, res.content)
        sid = res.data['id']
        self.assertEqual(res.data['employee_email'], 'worker@acme.com')
        self.assertEqual(res.data['gross_amount'], '60000.00')
        self.assertEqual([s['id'] for s in self.acc_c.get(SALARIES).data], [sid])
        res = self.acc_c.patch(f'{SALARIES}{sid}/', {'base_salary': '55000', 'allowances': {'House Rent': 9000}}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['gross_amount'], '64000.00')
        self.assertEqual(self.acc_c.delete(f'{SALARIES}{sid}/').status_code, 204)
        self.assertEqual(self.acc_c.get(SALARIES).data, [])

    def test_ceo_has_access(self):
        self.assertEqual(make(self.ceo, self.worker['id']).status_code, 201)

    # --- tenant isolation -------------------------------------------------
    def test_cannot_set_salary_for_another_companys_employee(self):
        beta = register_company('Beta', 'beta', 'ceo@beta.com')
        foreign = add_employee(beta, 'x@beta.com', 'B-1')
        self.assertEqual(make(self.acc_c, foreign['id']).status_code, 400)

    def test_other_company_cannot_see_it(self):
        sid = make(self.acc_c, self.worker['id']).data['id']
        beta = register_company('Beta', 'beta', 'ceo@beta.com')   # its CEO has the permission
        self.assertEqual(beta.get(f'{SALARIES}{sid}/').status_code, 404)
        self.assertEqual(beta.get(SALARIES).data, [])

    # --- validation -------------------------------------------------------
    def test_one_structure_per_employee(self):
        make(self.acc_c, self.worker['id'])
        self.assertEqual(make(self.acc_c, self.worker['id']).status_code, 400)

    def test_negative_or_missing_base_salary_rejected(self):
        self.assertEqual(make(self.acc_c, self.worker['id'], base='-1').status_code, 400)
        res = self.acc_c.post(SALARIES, {'employee': self.worker['id']}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_bad_allowances_rejected(self):
        for bad in ({'Rent': -5}, {'Rent': 'abc'}, {'': 100}, ['Rent', 5], 'text'):
            self.assertEqual(make(self.acc_c, self.worker['id'], allowances=bad).status_code, 400, bad)

    def test_allowances_optional(self):
        res = self.acc_c.post(SALARIES, {'employee': self.worker['id'], 'base_salary': '30000'}, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['gross_amount'], '30000.00')

    def test_employee_of_a_structure_cannot_be_changed(self):
        sid = make(self.acc_c, self.worker['id']).data['id']
        res = self.acc_c.patch(f'{SALARIES}{sid}/', {'employee': self.manager['id']}, format='json')
        self.assertEqual(res.status_code, 400)
