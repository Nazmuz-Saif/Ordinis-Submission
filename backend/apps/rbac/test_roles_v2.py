"""ST-139: Role detail, edit, holder counts, ROLE_IN_USE and unique Role names."""
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APITestCase

from core.test_utils import add_employee, give_role, login_as, register_company, rows
from rbac.models import EmployeeRole, Permission, Role


def ids(*codenames):
    return [str(i) for i in Permission.objects.filter(codename__in=codenames).values_list('id', flat=True)]


class RoleV2Tests(APITestCase):
    def setUp(self):
        self.ceo = register_company('Role Co', 'role-co', 'ceo@role.com')
        res = self.ceo.post('/api/v1/rbac/roles/', {'name': 'Lead', 'description': 'Leads a team', 'permissions': ids('create_task', 'view_analytics')}, format='json')
        self.role_id = res.data['id']
        self.emp = add_employee(self.ceo, 'a@role.com', 'E1')

    def assign(self, emp_id):
        return self.ceo.post('/api/v1/rbac/employee-roles/', {'employee': emp_id, 'role': self.role_id}, format='json')

    def test_list_shows_the_real_holder_count(self):
        self.assign(self.emp['id'])
        by_name = {r['name']: r for r in rows(self.ceo.get('/api/v1/rbac/roles/'))}
        self.assertEqual(by_name['Lead']['employee_count'], 1)
        self.assertEqual(by_name['CEO']['employee_count'], 1)
        self.assertEqual(len(by_name['Lead']['permission_details']), 2)

    def test_detail_has_permissions_with_descriptions_and_the_holders(self):
        self.assign(self.emp['id'])
        data = self.ceo.get(f'/api/v1/rbac/roles/{self.role_id}/').data
        self.assertEqual(data['employee_count'], 1)
        self.assertEqual([e['employee_code'] for e in data['employees']], ['E1'])
        self.assertEqual(data['employees'][0]['email'], 'a@role.com')
        for perm in data['permission_details']:
            self.assertTrue(perm['description'])

    def test_detail_of_a_role_with_no_holder(self):
        data = self.ceo.get(f'/api/v1/rbac/roles/{self.role_id}/').data
        self.assertEqual((data['employee_count'], data['employees']), (0, []))

    def test_edit_name_description_and_permissions(self):
        res = self.ceo.put(f'/api/v1/rbac/roles/{self.role_id}/', {'name': 'Senior Lead', 'description': 'New text', 'permissions': ids('view_billing')}, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        role = Role.objects.get(id=self.role_id)
        self.assertEqual((role.name, role.description), ('Senior Lead', 'New text'))
        self.assertEqual(list(role.permissions.values_list('codename', flat=True)), ['view_billing'])

    def test_editing_to_no_permission_is_allowed(self):
        res = self.ceo.patch(f'/api/v1/rbac/roles/{self.role_id}/', {'permissions': []}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Role.objects.get(id=self.role_id).permissions.count(), 0)

    def test_the_ceo_system_role_cannot_be_edited_or_deleted(self):
        ceo_role = Role.objects.get(company_id=self.ceo.company_id, is_system_default=True)
        self.assertEqual(self.ceo.put(f'/api/v1/rbac/roles/{ceo_role.id}/', {'name': 'X', 'permissions': []}, format='json').status_code, 400)
        self.assertEqual(self.ceo.delete(f'/api/v1/rbac/roles/{ceo_role.id}/').status_code, 400)
        self.assertTrue(Role.objects.filter(id=ceo_role.id).exists())

    def test_deleting_a_held_role_is_refused_with_role_in_use(self):
        self.assign(self.emp['id'])
        res = self.ceo.delete(f'/api/v1/rbac/roles/{self.role_id}/')
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.data['error']['code'], 'ROLE_IN_USE')
        self.assertIn('1 employee', res.data['error']['message'])
        self.assertTrue(Role.objects.filter(id=self.role_id).exists())

    def test_a_role_nobody_holds_can_be_deleted(self):
        self.assertEqual(self.ceo.delete(f'/api/v1/rbac/roles/{self.role_id}/').status_code, 204)
        self.assertFalse(Role.objects.filter(id=self.role_id).exists())

    def test_after_the_holder_is_removed_the_role_can_be_deleted(self):
        link = self.assign(self.emp['id']).data['id']
        self.ceo.delete(f'/api/v1/rbac/employee-roles/{link}/')
        self.assertEqual(self.ceo.delete(f'/api/v1/rbac/roles/{self.role_id}/').status_code, 204)

    def test_a_duplicate_name_is_a_400_not_a_500(self):
        res = self.ceo.post('/api/v1/rbac/roles/', {'name': 'lead'}, format='json')
        self.assertEqual(res.status_code, 400)
        other = self.ceo.post('/api/v1/rbac/roles/', {'name': 'Other'}, format='json').data['id']
        self.assertEqual(self.ceo.patch(f'/api/v1/rbac/roles/{other}/', {'name': 'Lead'}, format='json').status_code, 400)

    def test_saving_a_role_with_its_own_name_is_fine(self):
        res = self.ceo.put(f'/api/v1/rbac/roles/{self.role_id}/', {'name': 'Lead', 'description': 'x', 'permissions': []}, format='json')
        self.assertEqual(res.status_code, 200)

    def test_the_same_name_in_another_company_is_fine(self):
        other = register_company('Other Co', 'other-co', 'ceo@other.com')
        self.assertEqual(other.post('/api/v1/rbac/roles/', {'name': 'Lead'}, format='json').status_code, 201)

    def test_another_companys_role_is_a_404(self):
        other = register_company('Other Co', 'other-co', 'ceo@other.com')
        self.assertEqual(other.get(f'/api/v1/rbac/roles/{self.role_id}/').status_code, 404)
        self.assertEqual(other.put(f'/api/v1/rbac/roles/{self.role_id}/', {'name': 'Z', 'permissions': []}, format='json').status_code, 404)

    def test_an_employee_without_manage_roles_cannot_edit(self):
        res = login_as('a@role.com').put(f'/api/v1/rbac/roles/{self.role_id}/', {'name': 'Z', 'permissions': []}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_the_list_query_count_does_not_grow_with_roles(self):
        def count():
            with CaptureQueriesContext(connection) as q:
                self.ceo.get('/api/v1/rbac/roles/')
            return len(q)
        before = count()
        for n in range(5):
            self.ceo.post('/api/v1/rbac/roles/', {'name': f'R{n}', 'permissions': ids('view_billing')}, format='json')
        self.assertEqual(count(), before)
