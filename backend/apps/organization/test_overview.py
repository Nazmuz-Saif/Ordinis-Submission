"""ST-150: Department head, Department and Designation detail, and the in-use delete guard."""
import datetime

from django.test import TestCase

from core.test_utils import add_employee, give_role, login_as, register_company, rows
from organization.models import Department, Designation, Employee
from tasks.models import Task


def _task(company_id, assignee_id, assigner_id, title, status='in_progress', deadline=None):
    return Task.objects.create(
        company_id=company_id, title=title, assigned_to_id=assignee_id, assigned_by_id=assigner_id,
        status=status, deadline=deadline,
    )


class DepartmentHeadTests(TestCase):
    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.dept = self.ceo.post('/api/v1/organization/departments/', {'name': 'Sales'}, format='json').data
        self.emp = add_employee(self.ceo, 'a@acme.com', 'ACME-002', full_name='Anna Lee')

    def test_head_is_optional_and_can_be_set(self):
        self.assertIsNone(self.dept['head'])
        res = self.ceo.patch(f"/api/v1/organization/departments/{self.dept['id']}/", {'head': self.emp['id']}, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(str(res.data['head']), self.emp['id'])
        self.assertEqual(res.data['head_name'], 'Anna Lee')

    def test_head_of_another_company_is_refused(self):
        other = register_company('Beta', 'beta', 'ceo@beta.com')
        theirs = add_employee(other, 'b@beta.com', 'BETA-002')
        res = self.ceo.patch(f"/api/v1/organization/departments/{self.dept['id']}/", {'head': theirs['id']}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_head_can_be_cleared(self):
        self.ceo.patch(f"/api/v1/organization/departments/{self.dept['id']}/", {'head': self.emp['id']}, format='json')
        res = self.ceo.patch(f"/api/v1/organization/departments/{self.dept['id']}/", {'head': None}, format='json')
        self.assertIsNone(res.data['head'])

    def test_removing_the_head_employee_keeps_the_department(self):
        self.ceo.patch(f"/api/v1/organization/departments/{self.dept['id']}/", {'head': self.emp['id']}, format='json')
        self.assertEqual(self.ceo.delete(f"/api/v1/organization/employees/{self.emp['id']}/").status_code, 204)
        self.assertIsNone(Department.objects.get(id=self.dept['id']).head_id)

    def test_list_shows_member_count(self):
        Employee.objects.filter(id=self.emp['id']).update(department_id=self.dept['id'])
        listed = rows(self.ceo.get('/api/v1/organization/departments/'))
        self.assertEqual(listed[0]['member_count'], 1)


class DepartmentOverviewTests(TestCase):
    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.cid = self.ceo.company_id
        self.dept = Department.objects.create(company_id=self.cid, name='Dev')
        self.boss = add_employee(self.ceo, 'boss@acme.com', 'ACME-002', full_name='Boss', department=str(self.dept.id))
        self.dev = add_employee(
            self.ceo, 'dev@acme.com', 'ACME-003', full_name='Dev One', department=str(self.dept.id), reports_to=self.boss['id'],
        )
        self.peer = add_employee(self.ceo, 'peer@acme.com', 'ACME-004', full_name='Peer', department=str(self.dept.id))
        self.outsider = add_employee(self.ceo, 'out@acme.com', 'ACME-005', full_name='Outsider')
        today = datetime.date.today()
        self.t_run = _task(self.cid, self.dev['id'], self.ceo.employee_id, 'Build login', 'in_progress', today - datetime.timedelta(days=2))
        self.t_sub = _task(self.cid, self.peer['id'], self.ceo.employee_id, 'Peer secret', 'submitted')
        self.t_done = _task(self.cid, self.dev['id'], self.ceo.employee_id, 'Old', 'completed')
        self.t_todo = _task(self.cid, self.dev['id'], self.ceo.employee_id, 'Later', 'not_started')
        self.url = f'/api/v1/organization/departments/{self.dept.id}/overview/'

    def test_ceo_sees_members_counts_and_all_running_tasks(self):
        data = self.ceo.get(self.url).data
        self.assertEqual(data['member_count'], 3)
        self.assertEqual(data['task_summary'], {
            'not_started': 1, 'in_progress': 1, 'submitted': 1, 'completed': 1, 'overdue': 1, 'total': 4,
        })
        self.assertEqual(sorted(t['title'] for t in data['running_tasks']), ['Build login', 'Peer secret'])
        self.assertEqual(data['hidden_running_tasks'], 0)
        dev = next(m for m in data['members'] if m['employee_code'] == 'ACME-003')
        self.assertEqual(dev['manager']['full_name'], 'Boss')
        self.assertEqual(dev['open_tasks'], 2)

    def test_the_manager_sees_the_task_of_their_report_only(self):
        data = login_as('boss@acme.com').get(self.url).data
        self.assertEqual([t['title'] for t in data['running_tasks']], ['Build login'])
        self.assertEqual(data['hidden_running_tasks'], 1)
        self.assertEqual(data['task_summary']['total'], 4)   # counts are for everybody

    def test_an_outsider_sees_counts_but_no_task_titles(self):
        res = login_as('out@acme.com').get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['running_tasks'], [])
        self.assertEqual(res.data['hidden_running_tasks'], 2)
        self.assertNotIn('Build login', str(res.data))
        self.assertNotIn('Peer secret', str(res.data))

    def test_the_assignee_sees_their_own_task(self):
        data = login_as('dev@acme.com').get(self.url).data
        self.assertEqual([t['title'] for t in data['running_tasks']], ['Build login'])

    def test_another_company_gets_404(self):
        other = register_company('Beta', 'beta', 'ceo@beta.com')
        self.assertEqual(other.get(self.url).status_code, 404)

    def test_no_salary_in_the_overview(self):
        self.assertNotIn('salary', str(self.ceo.get(self.url).data).lower())

    def test_query_count_does_not_grow_with_members(self):
        with self.assertNumQueries(self._count()):
            self.ceo.get(self.url)
        for i in range(6, 10):
            e = add_employee(self.ceo, f'x{i}@acme.com', f'ACME-0{i}', department=str(self.dept.id))
            _task(self.cid, e['id'], self.ceo.employee_id, f'T{i}')
        with self.assertNumQueries(self._count()):
            self.ceo.get(self.url)

    def _count(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx:
            self.ceo.get(self.url)
        return len(ctx)


class DesignationOverviewTests(TestCase):
    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.desig = Designation.objects.create(company_id=self.ceo.company_id, title='Engineer')
        self.dept = Department.objects.create(company_id=self.ceo.company_id, name='Dev')
        self.emp = add_employee(self.ceo, 'e@acme.com', 'ACME-002', full_name='Eve', designation=str(self.desig.id), department=str(self.dept.id))

    def test_lists_holders_with_department(self):
        data = login_as('e@acme.com').get(f'/api/v1/organization/designations/{self.desig.id}/overview/').data
        self.assertEqual(data['employee_count'], 1)
        self.assertEqual(data['employees'][0]['department_name'], 'Dev')

    def test_another_company_gets_404(self):
        other = register_company('Beta', 'beta', 'ceo@beta.com')
        self.assertEqual(other.get(f'/api/v1/organization/designations/{self.desig.id}/overview/').status_code, 404)


class InUseDeleteTests(TestCase):
    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.dept = Department.objects.create(company_id=self.ceo.company_id, name='Sales')
        self.desig = Designation.objects.create(company_id=self.ceo.company_id, title='Rep')

    def test_department_with_employees_is_refused_with_names(self):
        add_employee(self.ceo, 'a@acme.com', 'ACME-002', full_name='Anna', department=str(self.dept.id))
        res = self.ceo.delete(f'/api/v1/organization/departments/{self.dept.id}/')
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.data['error']['code'], 'DEPARTMENT_IN_USE')
        self.assertIn('Anna', res.data['error']['message'])
        self.assertTrue(Department.objects.filter(id=self.dept.id).exists())

    def test_empty_department_can_be_deleted(self):
        self.assertEqual(self.ceo.delete(f'/api/v1/organization/departments/{self.dept.id}/').status_code, 204)

    def test_designation_with_employees_is_refused(self):
        add_employee(self.ceo, 'a@acme.com', 'ACME-002', full_name='Anna', designation=str(self.desig.id))
        res = self.ceo.delete(f'/api/v1/organization/designations/{self.desig.id}/')
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.data['error']['code'], 'DESIGNATION_IN_USE')
        self.assertTrue(Designation.objects.filter(id=self.desig.id).exists())

    def test_empty_designation_can_be_deleted(self):
        self.assertEqual(self.ceo.delete(f'/api/v1/organization/designations/{self.desig.id}/').status_code, 204)
