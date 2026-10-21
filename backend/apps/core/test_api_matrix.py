"""
Every API endpoint, checked three ways. The endpoints are found by themselves (core/api_matrix.py), so a new app
is covered the moment its urls are wired in. Two things must be kept up to date by whoever adds an endpoint:
  * demo data for the new model (<app>/demo_data.py), so the "another company" test has an object to try
  * SELF_SERVICE below, only if a write endpoint is open to any logged-in employee on purpose
"""
import io

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from core import demo
from core.api_matrix import FAKE_ID, discover_routes
from core.test_utils import add_employee, give_role, login_as, register_company

WRITE = ('post', 'put', 'patch', 'delete')

# Open to every logged-in employee ON PURPOSE: each one checks inside the service that the person is allowed
# (the assignee, a holder of the approver Role, the owner of the record), not through a Permission codename.
SELF_SERVICE = {
    'POST /api/v1/approvals/delegations/', 'DELETE /api/v1/approvals/delegations/{pk}/',
    'POST /api/v1/approvals/instances/{pk}/approve/', 'POST /api/v1/approvals/instances/{pk}/reject/',
    'POST /api/v1/attendance/attendance/check_in/', 'POST /api/v1/attendance/attendance/check_out/',
    'POST /api/v1/attendance/leave-requests/', 'POST /api/v1/attendance/leave-requests/{pk}/cancel/',
    'PATCH /api/v1/auth/profile/',   # a person edits only their own whitelisted details
    'POST /api/v1/notifications/{pk}/read/', 'POST /api/v1/notifications/read-all/',
    'POST /api/v1/platform-admin/company/tickets/',
    'POST /api/v1/tasks/tasks/{pk}/move/', 'POST /api/v1/tasks/tasks/{pk}/progress/',
    'POST /api/v1/tasks/tasks/{pk}/start/', 'POST /api/v1/tasks/tasks/{pk}/submit/',
}

# Reachable without logging in, on purpose.
PUBLIC = {
    '/api/v1/auth/login/', '/api/v1/auth/refresh/', '/api/v1/auth/logout/', '/api/v1/auth/register/',
}
# The same for every company by design (a fixed list of what can be granted), so it is not "tenant data".
SHARED_CATALOGS = {'api/v1/rbac/permissions/', 'api/v1/billing/plans/'}


def _is_platform_admin_route(route):
    return 'IsPlatformAdmin' in route.permission_class_names()


def _is_public(route):
    return route.url() in PUBLIC


class MatrixBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo_data', stdout=io.StringIO())
        cls.routes = discover_routes()
        cls.demo_ceo = login_as(demo.email('ceo'), demo.PASSWORD)
        cls.other_ceo = register_company('Other Co', 'other-co', 'boss@other.com')

    def send(self, client, method, url, body=None):
        return getattr(client, method)(url, body or {}, format='json')


class DiscoveryTests(MatrixBase):
    def test_the_routes_are_really_found(self):
        self.assertGreater(len(self.routes), 60)
        names = {r.view_cls.__name__ for r in self.routes}
        for expected in ('TaskViewSet', 'PayslipViewSet', 'LeaveRequestViewSet', 'ApprovalInstanceViewSet', 'EmployeeViewSet'):
            self.assertIn(expected, names)
        self.assertTrue(any(r.has_pk for r in self.routes))


class LoginRequiredTests(MatrixBase):
    def test_every_endpoint_refuses_a_request_with_no_login(self):
        anonymous, failures = APIClient(), []
        for route in self.routes:
            if _is_public(route):
                continue
            for method in route.methods:
                status = self.send(anonymous, method, route.url()).status_code
                if status != 401:
                    failures.append(f'{route.label(method)} gave {status}, expected 401')
        self.assertEqual(failures, [], '\n' + '\n'.join(failures))

    def test_the_only_public_endpoints_are_the_four_login_family_ones(self):
        public = sorted({r.template for r in self.routes if _is_public(r)})
        self.assertEqual(public, ['api/v1/auth/login/', 'api/v1/auth/logout/', 'api/v1/auth/refresh/', 'api/v1/auth/register/'])

    def test_the_router_index_pages_need_a_login_too(self):
        roots = [r for r in self.routes if r.view_cls.__name__ == 'APIRootView']
        self.assertGreaterEqual(len(roots), 5)
        for route in roots:
            self.assertEqual(self.send(APIClient(), 'get', route.url()).status_code, 401, route.template)

    def test_a_view_that_forgets_permission_classes_is_closed_not_open(self):
        from django.conf import settings
        self.assertEqual(
            settings.REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'],
            ('rest_framework.permissions.IsAuthenticated', 'core.permissions.IsCompanyActive'),
        )


class PermissionTests(MatrixBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.perm_ceo = register_company('Perm Co', 'perm-co', 'boss@perm.com')
        from billing.services import change_plan
        from tenants.models import Company
        change_plan(Company.objects.get(subdomain='perm-co'), 'Enterprise')   # one employee per Permission: more than Basic allows
        cls.plain = add_employee(cls.perm_ceo, 'plain@perm.com', 'P-1')
        cls.plain_client = login_as('plain@perm.com')
        cls.holders = {}

    def holder(self, codename):
        if codename not in self.holders:
            n = len(self.holders) + 2
            person = add_employee(self.perm_ceo, f'p{n}@perm.com', f'P-{n}')
            give_role(self.perm_ceo.company_id, person['id'], [codename], f'only {codename}')
            self.holders[codename] = login_as(f'p{n}@perm.com')
        return self.holders[codename]

    def protected(self):
        for route in self.routes:
            if _is_public(route) or _is_platform_admin_route(route):
                continue
            for method in route.methods:
                codename = route.required_permission(method)
                if codename:
                    yield route, method, codename

    def test_there_are_protected_actions_to_check(self):
        self.assertGreater(len(list(self.protected())), 50)

    def test_without_the_permission_every_protected_action_is_refused_403(self):
        failures = []
        for route, method, codename in self.protected():
            status = self.send(self.plain_client, method, route.url()).status_code
            if status != 403:
                failures.append(f'{route.label(method)} needs {codename}: an employee with no Role got {status}, expected 403')
        self.assertEqual(failures, [], '\n' + '\n'.join(failures))

    def test_with_exactly_that_permission_the_request_gets_past_the_permission_check(self):
        failures = []
        for route, method, codename in self.protected():
            status = self.send(self.holder(codename), method, route.url()).status_code
            if status in (401, 403):
                failures.append(f'{route.label(method)}: holder of {codename} still got {status}')
        self.assertEqual(failures, [], '\n' + '\n'.join(failures))

    def test_every_company_write_endpoint_either_demands_a_permission_or_is_listed_as_self_service(self):
        unlisted = []
        for route in self.routes:
            if _is_public(route) or _is_platform_admin_route(route):
                continue
            for method in route.methods:
                if method in WRITE and not route.required_permission(method):
                    key = f'{method.upper()} /{route.template}'
                    if key not in SELF_SERVICE:
                        unlisted.append(key)
        self.assertEqual(unlisted, [], 'Add a permission_required to these, or list them in SELF_SERVICE with a reason:\n' + '\n'.join(unlisted))

    def test_the_self_service_list_has_no_stale_entries(self):
        real = {f'{m.upper()} /{r.template}' for r in self.routes for m in r.methods}
        self.assertEqual(sorted(SELF_SERVICE - real), [])

    def test_platform_admin_endpoints_refuse_a_company_ceo_403(self):
        failures = []
        for route in self.routes:
            if not _is_platform_admin_route(route):
                continue
            for method in route.methods:
                status = self.send(self.demo_ceo, method, route.url()).status_code
                if status != 403:
                    failures.append(f'{route.label(method)}: a company CEO got {status}, expected 403')
        self.assertTrue(any(_is_platform_admin_route(r) for r in self.routes))
        self.assertEqual(failures, [], '\n' + '\n'.join(failures))


class OtherCompanyTests(MatrixBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Some lists only show a person their OWN records (leave, notifications), so try everyone in the demo company.
        cls.demo_people = [cls.demo_ceo] + [login_as(demo.email(p[1]), demo.PASSWORD) for p in demo.PEOPLE[1:]]

    def sample_id(self, route):
        """Any object of the demo company behind this collection, fetched by whichever demo person can see one."""
        for person in self.demo_people:
            res = person.get('/' + route.list_template)
            if res.status_code == 200:
                items = self._items(res.json())
                if items:
                    return str(items[0]['id'])
        return None

    def test_another_company_gets_404_for_every_object_route(self):
        failures, checked, no_sample = [], 0, []
        for route in self.routes:
            if not route.has_pk or _is_platform_admin_route(route) or _is_public(route):
                continue
            pk = self.sample_id(route)
            if pk is None:
                no_sample.append(route.template)
                continue
            for method in route.methods:
                status = self.send(self.other_ceo, method, route.url(pk)).status_code
                checked += 1
                if status != 404:
                    failures.append(f'{route.label(method)} on a demo object: another company got {status}, expected 404')
        self.assertEqual(no_sample, [], 'No demo object to try. Add demo data (<app>/demo_data.py) for:\n' + '\n'.join(no_sample))
        self.assertGreater(checked, 40)
        self.assertEqual(failures, [], '\n' + '\n'.join(failures))

    def test_another_company_never_sees_demo_objects_in_a_list(self):
        failures = []
        for route in self.routes:
            if route.has_pk or 'get' not in route.methods or _is_platform_admin_route(route) or _is_public(route):
                continue
            if route.template in SHARED_CATALOGS:
                continue
            demo_res = self.demo_ceo.get(route.url())
            other_res = self.other_ceo.get(route.url())
            if demo_res.status_code != 200 or other_res.status_code != 200:
                continue
            if 'json' not in demo_res.get('Content-Type', ''):
                continue   # a file download such as the Audit Log CSV export
            seen = {str(i['id']) for i in self._items(demo_res.json()) if isinstance(i, dict) and 'id' in i}
            leaked = seen & {str(i['id']) for i in self._items(other_res.json()) if isinstance(i, dict) and 'id' in i}
            if leaked:
                failures.append(f'{route.label("get")} shows {len(leaked)} demo objects to another company')
        self.assertEqual(failures, [], '\n' + '\n'.join(failures))

    @staticmethod
    def _items(data):
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ('results', 'data', 'items'):
                if isinstance(data.get(key), list):
                    return data[key]
                if isinstance(data.get(key), dict) and isinstance(data[key].get('items'), list):
                    return data[key]['items']
        return []
