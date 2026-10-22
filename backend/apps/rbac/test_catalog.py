"""ST-138: the Permission catalog in code, and the API that serves it."""
from django.test import TestCase
from rest_framework.test import APITestCase

from core.api_matrix import discover_routes
from core.test_utils import add_employee, give_role, login_as, register_company, rows
from rbac.catalog import CATALOG_CODENAMES, PERMISSION_CATALOG
from rbac.models import Permission, Role
from rbac.services import sync_permission_catalog


class CatalogShapeTests(TestCase):
    def test_every_entry_is_complete_and_unique(self):
        codenames = [e['codename'] for e in PERMISSION_CATALOG]
        self.assertEqual(len(codenames), len(set(codenames)), 'a codename is listed twice')
        for entry in PERMISSION_CATALOG:
            for key in ('codename', 'name', 'module', 'description'):
                self.assertTrue(entry.get(key), f"{entry.get('codename')} has no {key}")

    def test_every_view_permission_is_in_the_catalog(self):
        missing = []
        for route in discover_routes():
            for method in route.methods:
                codename = route.required_permission(method)
                if codename and codename not in CATALOG_CODENAMES:
                    missing.append(f'{route.label(method)} needs {codename}')
        self.assertEqual(missing, [], 'Add these codenames to rbac/catalog.py:\n' + '\n'.join(missing))

    def test_migrate_has_created_every_catalog_row(self):
        have = set(Permission.objects.values_list('codename', flat=True))
        self.assertTrue(CATALOG_CODENAMES <= have)


class CatalogSyncTests(TestCase):
    def test_a_missing_permission_is_added(self):
        Permission.objects.filter(codename='view_billing').delete()
        sync_permission_catalog()
        self.assertTrue(Permission.objects.filter(codename='view_billing').exists())

    def test_names_modules_and_descriptions_are_refreshed(self):
        Permission.objects.filter(codename='manage_roles').update(name='old', module='old', description='')
        sync_permission_catalog()
        perm = Permission.objects.get(codename='manage_roles')
        entry = next(e for e in PERMISSION_CATALOG if e['codename'] == 'manage_roles')
        self.assertEqual((perm.name, perm.module, perm.description), (entry['name'], entry['module'], entry['description']))

    def test_running_it_twice_changes_nothing(self):
        before = Permission.objects.count()
        sync_permission_catalog()
        sync_permission_catalog()
        self.assertEqual(Permission.objects.count(), before)

    def test_a_new_company_ceo_role_holds_every_catalog_permission(self):
        ceo = register_company('Cat Co', 'cat-co', 'ceo@cat.com')
        role = Role.objects.get(company_id=ceo.company_id, is_system_default=True)
        self.assertEqual(set(role.permissions.values_list('codename', flat=True)), CATALOG_CODENAMES)


class PermissionApiTests(APITestCase):
    def setUp(self):
        self.ceo = register_company('Perm Co', 'perm-co', 'ceo@perm.com')

    def test_the_api_returns_codename_name_module_and_description(self):
        res = self.ceo.get('/api/v1/rbac/permissions/?page_size=100')
        self.assertEqual(res.status_code, 200)
        items = rows(res)
        self.assertEqual({p['codename'] for p in items}, CATALOG_CODENAMES)
        for item in items:
            self.assertTrue(item['name'] and item['module'] and item['description'])

    def test_a_role_with_n_permissions_saves_exactly_n(self):
        ids = list(Permission.objects.filter(codename__in=['create_task', 'view_billing', 'manage_finance', 'view_analytics', 'assign_roles']).values_list('id', flat=True))
        res = self.ceo.post('/api/v1/rbac/roles/', {'name': 'Five', 'permissions': [str(i) for i in ids]}, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(len(res.data['permissions']), 5)
        self.assertEqual(Role.objects.get(name='Five', company_id=self.ceo.company_id).permissions.count(), 5)

    def test_a_role_with_one_and_with_no_permission(self):
        one = Permission.objects.get(codename='view_billing')
        res = self.ceo.post('/api/v1/rbac/roles/', {'name': 'One', 'permissions': [str(one.id)]}, format='json')
        self.assertEqual(len(res.data['permissions']), 1)
        res = self.ceo.post('/api/v1/rbac/roles/', {'name': 'Empty', 'permissions': []}, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['permissions'], [])

    def test_an_unknown_permission_id_is_refused_not_dropped(self):
        res = self.ceo.post('/api/v1/rbac/roles/', {'name': 'Bad', 'permissions': ['00000000-0000-4000-8000-000000000009']}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertFalse(Role.objects.filter(name='Bad').exists())
