"""ST-140: full names, the profile endpoint and its whitelist."""
from rest_framework.test import APIClient, APITestCase

from accounts.models import User
from core.test_utils import add_employee, give_role, login_as, register_company, rows
from organization.models import Department, Designation, Employee
from payroll.models import SalaryStructure


class RegistrationNameTests(APITestCase):
    def payload(self, **extra):
        return {'company_name': 'N Co', 'subdomain': 'n-co', 'ceo_full_name': 'Reza Chowdhury',
                'ceo_email': 'ceo@n.com', 'ceo_password': 'StrongPass123', **extra}

    def test_the_owner_name_is_saved_on_the_user(self):
        res = APIClient().post('/api/v1/auth/register/', self.payload(), format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(User.objects.get(email='ceo@n.com').full_name, 'Reza Chowdhury')

    def test_the_name_is_required_and_cannot_be_blank(self):
        data = self.payload(); data.pop('ceo_full_name')
        self.assertEqual(APIClient().post('/api/v1/auth/register/', data, format='json').status_code, 400)
        res = APIClient().post('/api/v1/auth/register/', self.payload(ceo_full_name='   '), format='json')
        self.assertEqual(res.status_code, 400)
        self.assertFalse(User.objects.filter(email='ceo@n.com').exists())

    def test_me_returns_the_full_name(self):
        ceo = register_company('Me Co', 'me-co', 'ceo@me.com', full_name='Asha Rahman')
        self.assertEqual(ceo.get('/api/v1/auth/me/').data['data']['full_name'], 'Asha Rahman')


class EmployeeNameTests(APITestCase):
    def setUp(self):
        self.ceo = register_company('Emp Co', 'emp-co', 'ceo@emp.com', full_name='Boss Person')

    def test_create_and_edit_an_employee_with_a_name(self):
        res = self.ceo.post('/api/v1/organization/employees/', {
            'email': 'a@emp.com', 'password': 'StrongPass123', 'employee_code': 'E1', 'full_name': '  Nusrat Jahan ',
        }, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.data['full_name'], 'Nusrat Jahan')
        self.assertEqual(User.objects.get(email='a@emp.com').full_name, 'Nusrat Jahan')
        res = self.ceo.patch(f"/api/v1/organization/employees/{res.data['id']}/", {'full_name': 'Nusrat J. Khan'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(User.objects.get(email='a@emp.com').full_name, 'Nusrat J. Khan')

    def test_an_old_row_without_a_name_still_works_everywhere(self):
        emp = add_employee(self.ceo, 'old@emp.com', 'OLD')   # no name given
        self.assertEqual(emp['full_name'], '')
        self.assertEqual(self.ceo.get(f"/api/v1/organization/employees/{emp['id']}/").status_code, 200)
        res = self.ceo.post('/api/v1/tasks/tasks/', {'title': 'T', 'assigned_to': emp['id']}, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['assigned_to_name'], '')
        self.assertEqual(res.data['assigned_to_email'], 'old@emp.com')

    def test_names_come_with_the_email_in_the_other_serializers(self):
        emp = add_employee(self.ceo, 'w@emp.com', 'W1', full_name='Worker One')
        task = self.ceo.post('/api/v1/tasks/tasks/', {'title': 'T', 'assigned_to': emp['id']}, format='json').data
        self.assertEqual(task['assigned_to_name'], 'Worker One')
        self.assertEqual(task['assigned_by_name'], 'Boss Person')
        board = self.ceo.get('/api/v1/tasks/tasks/board/').data
        cards = [c for col in board['columns'] for c in col['cards']]
        self.assertEqual(cards[0]['assigned_to_name'], 'Worker One')
        SalaryStructure.objects.create(company_id=self.ceo.company_id, employee_id=emp['id'], base_salary=1000)
        sal = rows(self.ceo.get('/api/v1/payroll/salary-structures/'))
        self.assertEqual(sal[0]['employee_name'], 'Worker One')
        roles = self.ceo.post('/api/v1/rbac/roles/', {'name': 'R'}, format='json').data['id']
        link = self.ceo.post('/api/v1/rbac/employee-roles/', {'employee': emp['id'], 'role': roles}, format='json').data
        self.assertEqual(link['employee_name'], 'Worker One')
        detail = self.ceo.get(f'/api/v1/rbac/roles/{roles}/').data
        self.assertEqual(detail['employees'][0]['name'], 'Worker One')
        log = rows(self.ceo.get('/api/v1/audit-log/logs/'))
        self.assertIn('actor_name', log[0])

    def test_display_name_falls_back_to_the_email(self):
        self.assertEqual(User(email='x@y.com', full_name='').display_name, 'x@y.com')
        self.assertEqual(User(email='x@y.com', full_name=' Ann ').display_name, 'Ann')


class ProfileTests(APITestCase):
    def setUp(self):
        self.ceo = register_company('Prof Co', 'prof-co', 'ceo@prof.com', full_name='Boss Person')
        self.dept = Department.objects.create(company_id=self.ceo.company_id, name='Eng')
        self.emp = add_employee(self.ceo, 'p@prof.com', 'P1', full_name='Pat One', department=str(self.dept.id))
        self.me = login_as('p@prof.com')

    def test_get_returns_the_own_details(self):
        data = self.me.get('/api/v1/auth/profile/').data['data']
        self.assertEqual((data['full_name'], data['email'], data['employee_code']), ('Pat One', 'p@prof.com', 'P1'))
        self.assertEqual(data['department_name'], 'Eng')
        self.assertEqual(data['phone'], '')

    def test_patch_changes_the_whitelisted_details(self):
        res = self.me.patch('/api/v1/auth/profile/', {
            'full_name': 'Pat Two', 'phone': '+880 1700-000000', 'address': '12 Road, Dhaka',
            'emergency_contact_name': 'Sam', 'emergency_contact_phone': '01800000000',
        }, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        emp = Employee.objects.get(id=self.emp['id'])
        self.assertEqual((emp.user.full_name, emp.phone, emp.address, emp.emergency_contact_name, emp.emergency_contact_phone),
                         ('Pat Two', '+880 1700-000000', '12 Road, Dhaka', 'Sam', '01800000000'))

    def test_a_partial_patch_changes_only_what_was_sent(self):
        self.me.patch('/api/v1/auth/profile/', {'phone': '0170'}, format='json')
        emp = Employee.objects.get(id=self.emp['id'])
        self.assertEqual((emp.phone, emp.user.full_name), ('0170', 'Pat One'))

    def test_fields_that_may_not_change_are_refused_and_nothing_is_saved(self):
        other = Department.objects.create(company_id=self.ceo.company_id, name='Sales')
        for field, value in [('email', 'new@prof.com'), ('department', str(other.id)), ('designation', None),
                             ('reports_to', None), ('employee_code', 'ZZ'), ('base_salary', '99999'),
                             ('roles', []), ('is_platform_admin', True), ('company', None), ('joined_on', '2020-01-01')]:
            res = self.me.patch('/api/v1/auth/profile/', {'phone': '0999', field: value}, format='json')
            self.assertEqual(res.status_code, 400, field)
            self.assertIn(field, res.data['error']['field_errors'])
        emp = Employee.objects.get(id=self.emp['id'])
        self.assertEqual(emp.phone, '')
        self.assertEqual(emp.user.email, 'p@prof.com')
        self.assertEqual(emp.department_id, self.dept.id)
        self.assertFalse(User.objects.get(email='p@prof.com').is_platform_admin)

    def test_the_salary_cannot_be_reached_through_the_profile(self):
        SalaryStructure.objects.create(company_id=self.ceo.company_id, employee_id=self.emp['id'], base_salary=1000)
        self.assertNotIn('salary', str(self.me.get('/api/v1/auth/profile/').data).lower())
        self.assertEqual(self.me.patch('/api/v1/auth/profile/', {'base_salary': 5}, format='json').status_code, 400)
        self.assertEqual(SalaryStructure.objects.get(employee_id=self.emp['id']).base_salary, 1000)

    def test_roles_cannot_be_granted_through_the_profile(self):
        self.me.patch('/api/v1/auth/profile/', {'roles': ['x']}, format='json')
        self.assertEqual(Employee.objects.get(id=self.emp['id']).employee_roles.count(), 0)

    def test_bad_values_are_refused(self):
        for body in ({'full_name': '   '}, {'full_name': 'x' * 151}, {'phone': 'call me'}, {'phone': '1' * 31},
                     {'address': 'x' * 256}, {'emergency_contact_phone': 'abc'}):
            self.assertEqual(self.me.patch('/api/v1/auth/profile/', body, format='json').status_code, 400, body)

    def test_blank_optional_details_can_be_cleared(self):
        self.me.patch('/api/v1/auth/profile/', {'phone': '0170'}, format='json')
        self.assertEqual(self.me.patch('/api/v1/auth/profile/', {'phone': ''}, format='json').status_code, 200)
        self.assertEqual(Employee.objects.get(id=self.emp['id']).phone, '')

    def test_login_is_required(self):
        self.assertEqual(APIClient().get('/api/v1/auth/profile/').status_code, 401)
        self.assertEqual(APIClient().patch('/api/v1/auth/profile/', {'phone': '1'}, format='json').status_code, 401)

    def test_a_profile_is_only_ever_the_callers_own(self):
        other = register_company('Other Co', 'other-co', 'ceo@other.com', full_name='Other Boss')
        self.assertEqual(other.get('/api/v1/auth/profile/').data['data']['full_name'], 'Other Boss')
        other.patch('/api/v1/auth/profile/', {'phone': '0555'}, format='json')
        self.assertEqual(Employee.objects.get(id=self.emp['id']).phone, '')

    def test_an_old_user_without_a_name_can_read_and_set_it(self):
        User.objects.filter(email='p@prof.com').update(full_name='')
        self.assertEqual(self.me.get('/api/v1/auth/profile/').data['data']['full_name'], '')
        self.assertEqual(self.me.patch('/api/v1/auth/profile/', {'full_name': 'Now Named'}, format='json').status_code, 200)

    def test_a_manager_name_is_shown_but_not_changeable(self):
        Employee.objects.filter(id=self.emp['id']).update(reports_to_id=self.ceo.employee_id)
        self.assertEqual(self.me.get('/api/v1/auth/profile/').data['data']['manager_name'], 'Boss Person')


class PlatformAdminProfileTests(APITestCase):
    def setUp(self):
        User.objects.create_user(email='pa@ordinis.test', password='StrongPass123', is_platform_admin=True)
        self.pa = login_as('pa@ordinis.test')

    def test_the_platform_admin_can_read_and_set_a_name(self):
        data = self.pa.get('/api/v1/auth/profile/').data['data']
        self.assertEqual((data['full_name'], data['is_platform_admin'], data['phone']), ('', True, None))
        res = self.pa.patch('/api/v1/auth/profile/', {'full_name': 'Ordinis Support'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(User.objects.get(email='pa@ordinis.test').full_name, 'Ordinis Support')
        self.assertEqual(self.pa.get('/api/v1/auth/me/').data['data']['full_name'], 'Ordinis Support')

    def test_the_platform_admin_has_no_employee_details_to_change(self):
        res = self.pa.patch('/api/v1/auth/profile/', {'phone': '0170'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('phone', res.data['error']['field_errors'])
