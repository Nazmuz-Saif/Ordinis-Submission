from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from approvals.models import ApprovalChain
from approvals.services import start_approval
from attendance.models import Attendance
from attendance.services import local_today
from core.test_utils import add_employee, give_role, login_as, register_company
from organization.models import Department, Employee
from payroll.models import SalaryStructure
from tasks.models import Task

SUMMARY = '/api/v1/dashboard/summary/'


def make_task(company_id, assignee_id, status='not_started', priority='medium', deadline=None, title='T'):
    return Task.objects.create(
        company_id=company_id, title=title, assigned_to_id=assignee_id,
        status=status, priority=priority, deadline=deadline,
    )


class DashboardSectionsTests(APITestCase):
    """Which sections a user gets depends on Permissions only."""

    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.cid = self.ceo.company_id
        self.people = {}
        for key, email, code, perms in [
            ('emp', 'emp@acme.com', 'A-1', []),
            ('manager', 'mgr@acme.com', 'A-2', ['create_task']),
            ('hr', 'hr@acme.com', 'A-3', ['manage_employees']),
            ('acc', 'acc@acme.com', 'A-4', ['manage_finance']),
        ]:
            e = add_employee(self.ceo, email, code)
            if perms:
                give_role(self.cid, e['id'], perms, key)
            self.people[key] = (e, login_as(email))

    def sections(self, key):
        res = self.people[key][1].get(SUMMARY)
        self.assertEqual(res.status_code, 200)
        return set(res.data)

    def test_plain_employee_gets_only_the_me_section(self):
        self.assertEqual(self.sections('emp'), {'me'})

    def test_manager_gets_me_and_team(self):
        self.assertEqual(self.sections('manager'), {'me', 'team'})

    def test_hr_gets_me_and_people_never_finance(self):
        self.assertEqual(self.sections('hr'), {'me', 'people'})

    def test_accountant_gets_me_and_finance_never_task_numbers(self):
        self.assertEqual(self.sections('acc'), {'me', 'finance'})

    def test_ceo_gets_everything(self):
        res = self.ceo.get(SUMMARY)
        self.assertEqual(set(res.data), {'me', 'team', 'people', 'finance'})

    def test_employee_response_contains_no_salary_text_anywhere(self):
        SalaryStructure.objects.create(company_id=self.cid, employee_id=self.people['acc'][0]['id'], base_salary=55555)
        body = self.people['emp'][1].get(SUMMARY).content.decode()
        for word in ('salary', 'payroll', '55555', 'finance'):
            self.assertNotIn(word, body)

    def test_anonymous_user_is_rejected(self):
        self.assertIn(APIClient().get(SUMMARY).status_code, (401, 403))


class DashboardNumbersTests(APITestCase):

    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.cid = self.ceo.company_id
        self.dev = add_employee(self.ceo, 'dev@acme.com', 'A-1')
        self.dev_c = login_as('dev@acme.com')
        self.today, _ = local_today(Employee.objects.get(id=self.dev['id']).company)

    def test_me_task_numbers(self):
        yesterday = self.today - timedelta(days=1)
        make_task(self.cid, self.dev['id'], 'not_started', deadline=yesterday)       # overdue
        make_task(self.cid, self.dev['id'], 'in_progress')
        make_task(self.cid, self.dev['id'], 'completed', deadline=yesterday)         # done: not overdue
        make_task(self.cid, self.ceo.employee_id, 'in_progress')                      # someone else's
        me = self.dev_c.get(SUMMARY).data['me']
        self.assertEqual(me['open_tasks'], 2)
        self.assertEqual(me['overdue_tasks'], 1)
        self.assertEqual(me['tasks_by_status'], {
            'not_started': 1, 'in_progress': 1, 'submitted': 0, 'completed': 1, 'rejected': 0})

    def test_me_attendance_today(self):
        self.assertFalse(self.dev_c.get(SUMMARY).data['me']['checked_in_today'])
        now = timezone.now()
        Attendance.objects.create(company_id=self.cid, employee_id=self.dev['id'], date=self.today, check_in=now)
        me = self.dev_c.get(SUMMARY).data['me']
        self.assertTrue(me['checked_in_today'])
        self.assertFalse(me['checked_out_today'])
        Attendance.objects.filter(employee_id=self.dev['id']).update(check_out=now)
        self.assertTrue(self.dev_c.get(SUMMARY).data['me']['checked_out_today'])

    def test_empty_company_gives_zeros_not_errors(self):
        data = self.ceo.get(SUMMARY).data
        self.assertEqual(data['team']['total_tasks'], 0)
        self.assertEqual(data['team']['completion_rate'], 0.0)
        self.assertEqual(data['finance']['total_base_payroll'], 0.0)
        self.assertEqual(data['finance']['average_base_salary'], 0.0)
        self.assertEqual(data['finance']['payroll_by_department'], [])

    def test_team_numbers(self):
        yesterday = self.today - timedelta(days=1)
        make_task(self.cid, self.dev['id'], 'completed', 'high')
        make_task(self.cid, self.dev['id'], 'submitted', 'low')
        make_task(self.cid, self.ceo.employee_id, 'in_progress', 'high', deadline=yesterday)
        make_task(self.cid, self.ceo.employee_id, 'not_started', 'medium')
        team = self.ceo.get(SUMMARY).data['team']
        self.assertEqual(team['total_tasks'], 4)
        self.assertEqual(team['overdue_tasks'], 1)
        self.assertEqual(team['awaiting_review'], 1)
        self.assertEqual(team['completion_rate'], 25.0)
        self.assertEqual(team['tasks_by_priority'], {'low': 1, 'medium': 1, 'high': 2})

    def test_people_numbers(self):
        dept = Department.objects.create(company_id=self.cid, name='Engineering')
        Employee.objects.filter(id=self.dev['id']).update(department=dept)
        Attendance.objects.create(company_id=self.cid, employee_id=self.dev['id'], date=self.today, check_in=timezone.now())
        people = self.ceo.get(SUMMARY).data['people']
        self.assertEqual(people['total_employees'], 2)
        self.assertEqual(people['new_this_month'], 2)
        self.assertEqual(people['departments'], 1)
        self.assertEqual(people['present_today'], 1)
        self.assertEqual(people['attendance_rate'], 50.0)
        self.assertEqual(
            {d['name']: d['count'] for d in people['employees_by_department']},
            {'Engineering': 1, 'No department': 1})

    def test_finance_numbers(self):
        dept = Department.objects.create(company_id=self.cid, name='Engineering')
        Employee.objects.filter(id=self.dev['id']).update(department=dept)
        SalaryStructure.objects.create(company_id=self.cid, employee_id=self.dev['id'], base_salary=40000)
        SalaryStructure.objects.create(company_id=self.cid, employee_id=self.ceo.employee_id, base_salary=60000)
        fin = self.ceo.get(SUMMARY).data['finance']
        self.assertEqual(fin['currency'], 'BDT')
        self.assertEqual(fin['salary_structures'], 2)
        self.assertEqual(fin['employees_without_salary'], 0)
        self.assertEqual(fin['total_base_payroll'], 100000.0)
        self.assertEqual(fin['average_base_salary'], 50000.0)
        self.assertEqual(
            {d['name']: d['total'] for d in fin['payroll_by_department']},
            {'No department': 60000.0, 'Engineering': 40000.0})

    def test_other_company_data_is_never_counted(self):
        beta = register_company('Beta', 'beta', 'ceo@beta.com')
        make_task(beta.company_id, beta.employee_id, 'in_progress')
        SalaryStructure.objects.create(company_id=beta.company_id, employee_id=beta.employee_id, base_salary=999999)
        data = self.ceo.get(SUMMARY).data
        self.assertEqual(data['team']['total_tasks'], 0)
        self.assertEqual(data['people']['total_employees'], 2)
        self.assertEqual(data['finance']['total_base_payroll'], 0.0)

    def test_approvals_waiting_counts_only_the_approver(self):
        head = add_employee(self.ceo, 'head@acme.com', 'H-1')
        role = give_role(self.cid, head['id'], [], 'Dept Head')
        chain = self.ceo.post('/api/v1/approvals/chains/', {'name': 'Leave', 'applies_to_module': 'leave'}, format='json').data['id']
        self.ceo.post('/api/v1/approvals/steps/', {'approval_chain': chain, 'approver_role': str(role.id)}, format='json')
        requester = Employee.objects.get(id=self.dev['id'])
        start_approval(requester, ApprovalChain.objects.get(id=chain), requester)
        head_c = login_as('head@acme.com')
        self.assertEqual(head_c.get(SUMMARY).data['me']['approvals_waiting'], 1)
        self.assertEqual(self.dev_c.get(SUMMARY).data['me']['approvals_waiting'], 0)  # own request
        self.assertEqual(self.ceo.get(SUMMARY).data['me']['approvals_waiting'], 0)    # not in that role

    def test_query_count_does_not_grow_with_pending_approvals(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        head = add_employee(self.ceo, 'head2@acme.com', 'H-2')
        role = give_role(self.cid, head['id'], [], 'Dept Head')
        chain = self.ceo.post('/api/v1/approvals/chains/', {'name': 'Leave', 'applies_to_module': 'leave'}, format='json').data['id']
        self.ceo.post('/api/v1/approvals/steps/', {'approval_chain': chain, 'approver_role': str(role.id)}, format='json')
        requester = Employee.objects.get(id=self.dev['id'])
        head_c = login_as('head2@acme.com')

        def queries():
            with CaptureQueriesContext(connection) as ctx:
                head_c.get(SUMMARY)
            return len(ctx)

        start_approval(requester, ApprovalChain.objects.get(id=chain), requester)
        few = queries()
        for _ in range(10):
            start_approval(requester, ApprovalChain.objects.get(id=chain), requester)
        self.assertEqual(queries(), few)
