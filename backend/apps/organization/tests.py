from django.test import TestCase

from core.test_utils import add_employee, give_role, login_as, register_company
from organization.models import Department
from rbac.models import EmployeeRole
from rbac.models import Permission, Role
from rbac.services import sync_system_roles


class PermissionEnforcementTests(TestCase):
    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.emp = add_employee(self.ceo, 'emp@acme.com', 'ACME-002')
        self.emp_client = login_as('emp@acme.com')

    def test_employee_without_permission_is_blocked_but_can_read(self):
        self.assertEqual(self.emp_client.get('/api/v1/organization/departments/').status_code, 200)
        res = self.emp_client.post('/api/v1/organization/departments/', {'name': 'HR'}, format='json')
        self.assertEqual(res.status_code, 403)
        self.assertFalse(Department.objects.exists())

    def test_employee_with_permission_is_allowed(self):
        give_role(self.ceo.company_id, self.emp['id'], ['manage_departments'])
        res = self.emp_client.post('/api/v1/organization/departments/', {'name': 'HR'}, format='json')
        self.assertEqual(res.status_code, 201)

    def test_ceo_can_create_right_after_registration(self):
        res = self.ceo.post('/api/v1/organization/departments/', {'name': 'Sales'}, format='json')
        self.assertEqual(res.status_code, 201)

    def test_only_assign_roles_permission_can_assign(self):
        role = give_role(self.ceo.company_id, self.emp['id'], ['manage_departments'], 'Dept only')
        body = {'employee': self.emp['id'], 'role': str(role.id)}
        self.assertEqual(self.emp_client.post('/api/v1/rbac/employee-roles/', body, format='json').status_code, 403)


class TenantIsolationTests(TestCase):
    def setUp(self):
        self.a = register_company('Acme', 'acme', 'ceo@acme.com')
        self.b = register_company('Beta', 'beta', 'ceo@beta.com')

    def test_cross_company_object_returns_404(self):
        dept = self.b.post('/api/v1/organization/departments/', {'name': 'Secret'}, format='json').data
        self.assertEqual(self.a.get(f"/api/v1/organization/departments/{dept['id']}/").status_code, 404)

    def test_cannot_link_employee_to_another_companys_department(self):
        dept = self.b.post('/api/v1/organization/departments/', {'name': 'Secret'}, format='json').data
        res = self.a.post('/api/v1/organization/employees/', {
            'email': 'x@acme.com', 'password': 'StrongPass123',
            'employee_code': 'ACME-009', 'department': dept['id'],
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_cannot_assign_another_companys_role(self):
        b_role = Role.objects.get(company_id=self.b.company_id)
        res = self.a.post('/api/v1/rbac/employee-roles/', {
            'employee': self.a.employee_id, 'role': str(b_role.id),
        }, format='json')
        self.assertEqual(res.status_code, 400)


class HierarchyCycleTests(TestCase):
    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.b = add_employee(self.ceo, 'b@acme.com', 'ACME-002', reports_to=self.ceo.employee_id)
        self.c = add_employee(self.ceo, 'c@acme.com', 'ACME-003', reports_to=self.b['id'])

    def patch(self, emp_id, manager_id):
        return self.ceo.patch(f'/api/v1/organization/employees/{emp_id}/', {'reports_to': manager_id}, format='json')

    def test_employee_cannot_report_to_self(self):
        self.assertEqual(self.patch(self.b['id'], self.b['id']).status_code, 400)

    def test_indirect_cycle_is_blocked(self):
        # CEO -> B -> C ; making the CEO report to C would loop.
        self.assertEqual(self.patch(self.ceo.employee_id, self.c['id']).status_code, 400)

    def test_valid_reassignment_still_works(self):
        self.assertEqual(self.patch(self.c['id'], self.ceo.employee_id).status_code, 200)


class SystemRoleTests(TestCase):
    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.role = Role.objects.get(company_id=self.ceo.company_id, is_system_default=True)

    def test_system_role_cannot_be_edited_or_deleted(self):
        self.assertEqual(self.ceo.patch(f'/api/v1/rbac/roles/{self.role.id}/', {'name': 'X'}, format='json').status_code, 400)
        self.assertEqual(self.ceo.delete(f'/api/v1/rbac/roles/{self.role.id}/').status_code, 400)

    def test_last_ceo_holder_cannot_be_removed(self):
        assignment = EmployeeRole.objects.get(role=self.role)
        self.assertEqual(self.ceo.delete(f'/api/v1/rbac/employee-roles/{assignment.id}/').status_code, 400)

    def test_new_permission_reaches_existing_ceo_role(self):
        Permission.objects.create(codename='brand_new', name='Brand New', module='test')
        sync_system_roles()
        self.assertTrue(self.role.permissions.filter(codename='brand_new').exists())


class SubordinatesEndpointTests(TestCase):
    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.b = add_employee(self.ceo, 'b@acme.com', 'ACME-002', reports_to=self.ceo.employee_id)
        self.c = add_employee(self.ceo, 'c@acme.com', 'ACME-003', reports_to=self.b['id'])
        self.other = register_company('Beta', 'beta', 'ceo@beta.com')

    def test_returns_all_levels(self):
        res = self.ceo.get(f'/api/v1/organization/employees/{self.ceo.employee_id}/subordinates/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual({e['employee_code'] for e in res.data}, {'ACME-002', 'ACME-003'})

    def test_leaf_has_none(self):
        res = self.ceo.get(f"/api/v1/organization/employees/{self.c['id']}/subordinates/")
        self.assertEqual(res.data, [])

    def test_other_company_gets_404(self):
        res = self.other.get(f'/api/v1/organization/employees/{self.ceo.employee_id}/subordinates/')
        self.assertEqual(res.status_code, 404)


class RemovedEmployeeAccessTests(TestCase):
    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.emp = add_employee(self.ceo, 'x@acme.com', 'ACME-002')
        self.emp_client = login_as('x@acme.com')

    def test_deleted_employee_loses_all_access(self):
        self.assertEqual(self.emp_client.get('/api/v1/organization/employees/').status_code, 200)
        self.assertEqual(self.ceo.delete(f"/api/v1/organization/employees/{self.emp['id']}/").status_code, 204)

        # The token they already hold stops working...
        self.assertEqual(self.emp_client.get('/api/v1/organization/employees/').status_code, 401)
        # ...and they cannot log in again.
        from rest_framework.test import APIClient
        res = APIClient().post('/api/v1/auth/login/', {'email': 'x@acme.com', 'password': 'StrongPass123'}, format='json')
        self.assertEqual(res.status_code, 401)

    def test_cannot_delete_yourself(self):
        res = self.ceo.delete(f'/api/v1/organization/employees/{self.ceo.employee_id}/')
        self.assertEqual(res.status_code, 400)

    def test_cannot_delete_an_employee_who_still_has_a_team(self):
        add_employee(self.ceo, 'sub@acme.com', 'ACME-003', reports_to=self.emp['id'])
        res = self.ceo.delete(f"/api/v1/organization/employees/{self.emp['id']}/")
        self.assertEqual(res.status_code, 400)

    def test_cannot_delete_the_last_ceo_role_holder(self):
        role = Role.objects.get(company_id=self.ceo.company_id, is_system_default=True)
        # A different employee (with manage_employees) will try the delete, so set them up first.
        admin = add_employee(self.ceo, 'admin@acme.com', 'ACME-004')
        give_role(self.ceo.company_id, admin['id'], ['manage_employees'], 'HR')
        # Make the target the ONLY holder of the CEO role.
        EmployeeRole.objects.filter(role=role).delete()
        EmployeeRole.objects.create(employee_id=self.emp['id'], role=role, company_id=self.ceo.company_id)
        res = login_as('admin@acme.com').delete(f"/api/v1/organization/employees/{self.emp['id']}/")
        self.assertEqual(res.status_code, 400)


class EmployeeCodeScopeTests(TestCase):
    def setUp(self):
        self.a = register_company('Acme', 'acme', 'ceo@acme.com')
        self.b = register_company('Beta', 'beta', 'ceo@beta.com')

    def create(self, client, email, code):
        return client.post('/api/v1/organization/employees/',
                           {'email': email, 'password': 'StrongPass123', 'employee_code': code}, format='json')

    def test_two_companies_can_use_the_same_code(self):
        self.assertEqual(self.create(self.a, 'p@acme.com', 'EMP-001').status_code, 201)
        self.assertEqual(self.create(self.b, 'q@beta.com', 'EMP-001').status_code, 201)

    def test_duplicate_inside_one_company_is_rejected_without_leaking(self):
        self.create(self.a, 'p@acme.com', 'EMP-001')
        res = self.create(self.a, 'r@acme.com', 'EMP-001')
        self.assertEqual(res.status_code, 400)
        self.assertIn('your company', str(res.data))

    def test_editing_an_employee_keeps_its_own_code(self):
        emp = self.create(self.a, 'p@acme.com', 'EMP-001').data
        res = self.a.patch(f"/api/v1/organization/employees/{emp['id']}/", {'employee_code': 'EMP-001'}, format='json')
        self.assertEqual(res.status_code, 200)
