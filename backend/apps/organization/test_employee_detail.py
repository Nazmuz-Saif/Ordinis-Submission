"""ST-143: the Employee detail page: who sees what, and the Roles and Permissions a person really has."""
import datetime

from rest_framework.test import APITestCase

from billing.services import change_plan
from core.test_utils import add_employee, give_role, login_as, register_company, rows
from organization.models import Department, Designation, Employee
from payroll.models import Payslip, SalaryStructure
from rbac.models import EmployeeRole, Role
from tenants.models import Company

BASE = '/api/v1/organization/employees/'
PRIVATE = ('phone', 'address', 'emergency_contact_name', 'emergency_contact_phone', 'joined_on')


class DetailBase(APITestCase):
    def setUp(self):
        self.ceo = register_company('Det Co', 'det-co', 'ceo@det.com', full_name='Chief Exec')
        change_plan(Company.objects.get(subdomain='det-co'), 'Enterprise')
        self.cid = self.ceo.company_id
        # manager -> report -> sub ; peer under the CEO ; hr with manage_employees only
        self.mgr = add_employee(self.ceo, 'mgr@det.com', 'M1', full_name='Mona Manager', reports_to=str(self.ceo.employee_id))
        self.rep = add_employee(self.ceo, 'rep@det.com', 'R1', full_name='Rafi Report', reports_to=self.mgr['id'])
        self.sub = add_employee(self.ceo, 'sub@det.com', 'S1', full_name='Sadia Sub', reports_to=self.rep['id'])
        self.peer = add_employee(self.ceo, 'peer@det.com', 'P1', full_name='Pia Peer', reports_to=str(self.ceo.employee_id))
        self.hr = add_employee(self.ceo, 'hr@det.com', 'H1', full_name='Hana HR')
        give_role(self.cid, self.hr['id'], ['manage_employees'], 'HR')
        dept = Department.objects.create(company_id=self.cid, name='Engineering')
        title = Designation.objects.create(company_id=self.cid, title='Engineer')
        Employee.objects.filter(id=self.rep['id']).update(
            department=dept, designation=title,
            phone='0170000111', address='12 Road, Dhaka', emergency_contact_name='Sam', emergency_contact_phone='0180000222',
            joined_on=datetime.date(2024, 3, 1))
        self.clients = {k: login_as(f'{k}@det.com') for k in ('mgr', 'rep', 'sub', 'peer', 'hr')}

    def detail(self, client, emp):
        return client.get(f'{BASE}{emp["id"]}/')


class PrivateDetailsTests(DetailBase):
    def test_the_person_sees_their_own_details(self):
        data = self.detail(self.clients['rep'], self.rep).data
        self.assertTrue(data['contact_visible'])
        self.assertEqual((data['phone'], data['address']), ('0170000111', '12 Road, Dhaka'))
        self.assertEqual(data['joined_on'], '2024-03-01')

    def test_a_manager_above_sees_them_at_any_depth(self):
        self.assertEqual(self.detail(self.clients['mgr'], self.rep).data['phone'], '0170000111')
        self.assertEqual(self.detail(self.ceo, self.rep).data['phone'], '0170000111')   # the CEO is two levels up

    def test_a_manage_employees_holder_sees_them(self):
        self.assertEqual(self.detail(self.clients['hr'], self.rep).data['emergency_contact_name'], 'Sam')

    def test_a_colleague_outside_the_reporting_line_sees_the_public_part_only(self):
        data = self.detail(self.clients['peer'], self.rep).data
        self.assertFalse(data['contact_visible'])
        for field in PRIVATE:
            self.assertNotIn(field, data)
        self.assertEqual(data['full_name'], 'Rafi Report')
        self.assertEqual((data['designation_title'], data['department_name']), ('Engineer', 'Engineering'))
        self.assertNotIn('salary', data)

    def test_someone_below_does_not_see_their_manager_s_details(self):
        Employee.objects.filter(id=self.mgr['id']).update(phone='0199999999')
        data = self.detail(self.clients['sub'], self.mgr).data
        self.assertFalse(data['contact_visible'])
        self.assertNotIn('phone', data)

    def test_the_list_hides_private_fields_from_people_without_manage_employees(self):
        for row in rows(self.clients['peer'].get(BASE)):
            for field in PRIVATE:
                self.assertNotIn(field, row)
        for row in rows(self.clients['mgr'].get(BASE)):
            self.assertNotIn('phone', row)       # a manager sees details on the detail page, not in lists

    def test_the_list_shows_them_to_manage_employees_holders(self):
        found = {r['id']: r for r in rows(self.clients['hr'].get(BASE))}
        self.assertEqual(found[self.rep['id']]['phone'], '0170000111')

    def test_subordinates_endpoint_does_not_leak_private_fields_either(self):
        res = self.clients['peer'].get(f'{BASE}{self.mgr["id"]}/subordinates/')
        for row in rows(res):
            self.assertNotIn('phone', row)

    def test_another_companys_employee_is_a_404(self):
        other = register_company('Other Co', 'other-co', 'ceo@other.com')
        self.assertEqual(self.detail(other, self.rep).status_code, 404)
        self.assertEqual(other.get(f'{BASE}{self.rep["id"]}/access/').status_code, 404)


class EditPrivateDetailsTests(DetailBase):
    def test_manage_employees_can_edit_the_details(self):
        res = self.clients['hr'].patch(f'{BASE}{self.sub["id"]}/', {
            'phone': '0171', 'address': 'Somewhere', 'emergency_contact_name': 'Kin',
            'emergency_contact_phone': '0172', 'joined_on': '2025-01-15'}, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        emp = Employee.objects.get(id=self.sub['id'])
        self.assertEqual((emp.phone, emp.address, emp.emergency_contact_name, emp.joined_on), ('0171', 'Somewhere', 'Kin', datetime.date(2025, 1, 15)))
        self.assertEqual(res.data['phone'], '0171')

    def test_everyone_else_cannot_edit_them(self):
        for key in ('peer', 'mgr', 'rep'):
            res = self.clients[key].patch(f'{BASE}{self.rep["id"]}/', {'phone': '0000'}, format='json')
            self.assertEqual(res.status_code, 403, key)
        self.assertEqual(Employee.objects.get(id=self.rep['id']).phone, '0170000111')

    def test_a_bad_phone_is_refused(self):
        res = self.clients['hr'].patch(f'{BASE}{self.sub["id"]}/', {'phone': 'call me'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('phone', res.data['error']['field_errors'])


class HierarchyTests(DetailBase):
    def test_the_manager_chain_runs_from_the_direct_manager_to_the_top(self):
        data = self.detail(self.clients['peer'], self.sub).data
        self.assertEqual([m['full_name'] for m in data['managers']], ['Rafi Report', 'Mona Manager', 'Chief Exec'])

    def test_direct_reports_are_listed(self):
        data = self.detail(self.ceo, self.mgr).data
        self.assertEqual([r['full_name'] for r in data['direct_reports']], ['Rafi Report'])
        self.assertEqual(self.detail(self.ceo, self.sub).data['direct_reports'], [])

    def test_the_top_person_has_no_managers(self):
        me = Employee.objects.get(id=self.ceo.employee_id)
        self.assertEqual(self.ceo.get(f'{BASE}{me.id}/').data['managers'], [])


class SalaryVisibilityTests(DetailBase):
    def setUp(self):
        super().setUp()
        SalaryStructure.objects.create(company_id=self.cid, employee_id=self.rep['id'], base_salary=50000, allowances={'Rent': 8000})
        Payslip.objects.create(company_id=self.cid, employee_id=self.rep['id'], year=2026, month=9, base_salary=50000,
                               allowances={'Rent': 8000}, gross_amount=58000, deductions=0, net_amount=58000)
        self.acc = add_employee(self.ceo, 'acc@det.com', 'A1', full_name='Ali Accountant')
        give_role(self.cid, self.acc['id'], ['manage_finance'], 'Finance')

    def test_manage_finance_sees_the_salary_lines(self):
        data = self.detail(login_as('acc@det.com'), self.rep).data
        self.assertEqual(data['salary']['base_salary'], '50000.00')
        self.assertEqual(data['recent_payslips'][0]['net_amount'], '58000.00')

    def test_a_person_with_manage_finance_but_no_hierarchy_access_sees_no_private_details(self):
        data = self.detail(login_as('acc@det.com'), self.rep).data
        self.assertNotIn('phone', data)       # finance is not HR

    def test_nobody_else_sees_salary_not_even_the_manager_or_hr_or_the_person(self):
        for key in ('mgr', 'hr', 'rep', 'peer'):
            data = self.detail(self.clients[key], self.rep).data
            self.assertNotIn('salary', data, key)
            self.assertNotIn('recent_payslips', data, key)
        self.assertNotIn('50000', str(self.detail(self.clients['hr'], self.rep).data))

    def test_a_person_without_a_salary_structure_gets_null(self):
        self.assertIsNone(self.detail(self.ceo, self.sub).data['salary'])


class AccessTests(DetailBase):
    def access(self, client, emp):
        return client.get(f'{BASE}{emp["id"]}/access/')

    def test_a_person_with_no_role_has_no_permissions(self):
        data = self.access(self.ceo, self.sub).data
        self.assertEqual((data['roles'], data['permissions']), ([], []))

    def test_one_role_lists_its_permissions_with_descriptions(self):
        data = self.access(self.ceo, self.hr).data
        self.assertEqual([r['name'] for r in data['roles']], ['HR'])
        perm = data['permissions'][0]
        self.assertEqual(perm['codename'], 'manage_employees')
        self.assertTrue(perm['description'])
        self.assertEqual(perm['roles'], ['HR'])

    def test_several_roles_are_unioned_without_duplicates(self):
        give_role(self.cid, self.hr['id'], ['manage_employees', 'view_billing', 'create_task'], 'Mixed')
        data = self.access(self.ceo, self.hr).data
        self.assertEqual({r['name'] for r in data['roles']}, {'HR', 'Mixed'})
        codenames = [p['codename'] for p in data['permissions']]
        self.assertEqual(sorted(codenames), sorted(set(codenames)))
        self.assertEqual(set(codenames), {'manage_employees', 'view_billing', 'create_task'})
        shared = next(p for p in data['permissions'] if p['codename'] == 'manage_employees')
        self.assertEqual(sorted(shared['roles']), ['HR', 'Mixed'])

    def test_the_ceo_role_holds_every_permission(self):
        data = self.access(self.ceo, {'id': str(self.ceo.employee_id)}).data
        self.assertGreaterEqual(len(data['permissions']), 14)

    def test_a_role_with_no_permission_shows_up_with_an_empty_list(self):
        role = Role.objects.create(company_id=self.cid, name='Empty')
        EmployeeRole.objects.create(employee_id=self.sub['id'], role=role, company_id=self.cid)
        data = self.access(self.ceo, self.sub).data
        self.assertEqual(data['roles'][0]['permissions'], [])
        self.assertEqual(data['permissions'], [])

    def test_who_may_ask(self):
        self.assertEqual(self.access(self.clients['rep'], self.rep).status_code, 200)     # themself
        self.assertEqual(self.access(self.clients['mgr'], self.rep).status_code, 200)     # their manager
        self.assertEqual(self.access(self.clients['hr'], self.rep).status_code, 200)      # manage_employees
        self.assertEqual(self.access(self.clients['peer'], self.rep).status_code, 403)    # a colleague
        self.assertEqual(self.access(self.clients['sub'], self.rep).status_code, 403)     # someone below

    def test_assign_roles_holders_may_ask(self):
        role_admin = add_employee(self.ceo, 'ra@det.com', 'RA', full_name='Role Admin')
        give_role(self.cid, role_admin['id'], ['assign_roles'], 'Role admin')
        self.assertEqual(self.access(login_as('ra@det.com'), self.rep).status_code, 200)
