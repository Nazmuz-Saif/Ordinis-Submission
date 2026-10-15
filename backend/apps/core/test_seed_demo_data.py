from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from approvals.models import ApprovalChain, ApprovalInstance
from attendance.leave_models import LeaveRequest
from attendance.models import Attendance
from core import demo
from core.test_utils import register_company
from notifications.models import Notification
from organization.models import Employee
from payroll.models import Payslip, SalaryStructure
from tasks.models import Task, TaskProgressLog
from tasks.services import COLUMN_OF_STATUS
from tenants.models import Company


def seed(*args):
    out = StringIO()
    call_command('seed_demo_data', *args, stdout=out)
    return out.getvalue()


def counts():
    return {
        'companies': Company.objects.count(), 'users': User.objects.count(), 'employees': Employee.objects.count(),
        'tasks': Task.objects.count(), 'progress': TaskProgressLog.objects.count(),
        'attendance': Attendance.objects.count(), 'leaves': LeaveRequest.objects.count(),
        'instances': ApprovalInstance.objects.count(), 'payslips': Payslip.objects.count(),
        'salaries': SalaryStructure.objects.count(), 'notifications': Notification.objects.count(),
    }


def login(local):
    client = APIClient()
    res = client.post('/api/v1/auth/login/', {'email': demo.email(local), 'password': demo.PASSWORD}, format='json')
    assert res.status_code == 200, res.content
    body = res.json()
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + (body.get('data') or body)['access'])
    return client


def login_status(email):
    return APIClient().post('/api/v1/auth/login/', {'email': email, 'password': demo.PASSWORD}, format='json').status_code


class SeedContentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def test_the_demo_company_has_a_ceo_and_a_multi_level_hierarchy(self):
        company = Company.objects.get(subdomain=demo.SUBDOMAIN)
        self.assertEqual(Employee.objects.filter(company=company).count(), len(demo.PEOPLE))
        depth = 0
        node = Employee.objects.get(company=company, user__email=demo.email('employee'))
        while node.reports_to_id:
            node, depth = node.reports_to, depth + 1
        self.assertEqual((node.user.email, depth), (demo.email('ceo'), 3), 'employee -> manager -> GM -> CEO')
        self.assertLessEqual(len(demo.PEOPLE), 10, 'the Basic plan limit is 10 employees')

    def test_every_dashboard_login_works_and_gets_its_own_sections(self):
        expected = {
            'ceo': {'me', 'team', 'people', 'finance'}, 'manager': {'me', 'team'}, 'hr': {'me', 'people'},
            'accountant': {'me', 'finance'}, 'employee': {'me'},
        }
        for _role, local in demo.LOGINS:
            res = login(local).get('/api/v1/dashboard/summary/')
            self.assertEqual(res.status_code, 200, local)
            self.assertEqual(set(res.json()), expected[local], local)

    def test_tasks_fill_all_four_kanban_columns_and_have_progress_notes(self):
        columns = {COLUMN_OF_STATUS[t.status] for t in Task.objects.all()}
        self.assertEqual(columns, {'todo', 'in_progress', 'review', 'done'})
        self.assertTrue(Task.objects.filter(status='in_progress', progress_logs__isnull=False).exists())
        self.assertTrue(Task.objects.exclude(deadline__isnull=True).filter(status='in_progress').exists())

    def test_the_employee_can_check_in_live(self):
        res = login('employee').get('/api/v1/attendance/attendance/today/')
        self.assertEqual(res.status_code, 200, res.content)

    def test_a_month_of_attendance_exists_for_everyone(self):
        per_person = Attendance.objects.filter(employee__user__email=demo.email('farhan.ahmed')).count()
        self.assertGreaterEqual(per_person, 15)

    def test_leave_requests_exist_in_every_status_and_pass_through_the_real_approval_chain(self):
        self.assertEqual(set(LeaveRequest.objects.values_list('status', flat=True)),
                         {'pending', 'approved', 'rejected', 'cancelled'})
        self.assertEqual(ApprovalChain.objects.get(name='Leave Approval').steps.count(), 2)
        self.assertFalse(ApprovalChain.objects.filter(name='Leave Approval (default)').exists())
        waiting = ApprovalInstance.objects.filter(status='pending')
        self.assertEqual({i.current_step for i in waiting}, {1, 2}, 'one waits for the Manager, one for HR')
        rejected = ApprovalInstance.objects.get(status='rejected')
        self.assertTrue(rejected.actions.get().comment)

    def test_the_manager_has_requests_waiting_in_the_inbox(self):
        res = login('manager').get('/api/v1/approvals/instances/?mine=pending')
        self.assertGreaterEqual(len(res.json()['results']) if 'results' in res.json() else len(res.json()), 1)

    def test_payroll_has_structures_and_three_months_of_payslips(self):
        self.assertEqual(SalaryStructure.objects.count(), len(demo.PEOPLE) )
        self.assertEqual(Payslip.objects.count(), len(demo.PEOPLE) * 3)
        self.assertTrue(Payslip.objects.filter(deductions__gt=0).exists())

    def test_the_platform_admin_and_break_glass_demo_exist(self):
        from platform_admin.models import SupportAccessRequest, SupportTicket
        admin = User.objects.get(email=demo.email('platform'))
        self.assertTrue(admin.is_platform_admin and admin.company_id is None)
        self.assertEqual(set(SupportAccessRequest.objects.values_list('status', flat=True)), {'pending', 'denied', 'revoked'})
        self.assertEqual(set(SupportTicket.objects.values_list('status', flat=True)), {'open', 'resolved'})
        self.assertEqual(login_status(demo.email('platform')), 200)

    def test_notifications_exist_some_read_some_unread(self):
        self.assertTrue(Notification.objects.filter(is_read=True).exists())
        self.assertTrue(Notification.objects.filter(is_read=False).exists())


class SeedSafetyTests(TestCase):
    def test_running_twice_creates_nothing_new(self):
        seed()
        before = counts()
        text = seed()
        self.assertEqual(counts(), before)
        self.assertIn('nothing new', text)

    def test_reset_rebuilds_the_demo_company_and_never_touches_another_company(self):
        other = register_company('Other Co', 'other-co', 'boss@other.com')
        other_company_id = other.company_id
        seed()
        keep = Employee.objects.filter(company_id=other_company_id).count()
        seed('--reset')
        self.assertEqual(Company.objects.filter(subdomain=demo.SUBDOMAIN).count(), 1)
        self.assertEqual(Employee.objects.filter(company_id=other_company_id).count(), keep)
        self.assertTrue(Company.objects.filter(pk=other_company_id).exists())
        self.assertEqual(Employee.objects.filter(company__subdomain=demo.SUBDOMAIN).count(), len(demo.PEOPLE))

    def test_delete_removes_only_the_demo_company(self):
        register_company('Other Co', 'other-co', 'boss@other.com')
        seed()
        seed('--delete')
        self.assertFalse(Company.objects.filter(subdomain=demo.SUBDOMAIN).exists())
        self.assertFalse(User.objects.filter(email__endswith='@' + demo.DOMAIN, company__isnull=False).exists())
        self.assertTrue(User.objects.filter(email=demo.email('platform'), is_platform_admin=True).exists(),
                        'the Platform Admin belongs to no company, so it stays')
        self.assertTrue(Company.objects.filter(subdomain='other-co').exists())
        self.assertIn('no demo company', seed('--delete'))

    def test_it_refuses_production_settings_and_creates_nothing(self):
        with override_settings(SETTINGS_MODULE='config.settings.production'):
            with self.assertRaises(CommandError):
                seed()
        self.assertFalse(Company.objects.exists())

    def test_reset_and_delete_together_are_refused(self):
        with self.assertRaises(CommandError):
            seed('--reset', '--delete')

    def test_a_missing_piece_is_filled_in_on_the_next_run(self):
        seed()
        Task.objects.filter(title='Set up the staging server').delete()
        Attendance.objects.filter(employee__user__email=demo.email('hr')).delete()
        before = counts()
        seed()
        after = counts()
        self.assertEqual(after['tasks'], before['tasks'] + 1)
        self.assertGreater(after['attendance'], before['attendance'])

    def test_a_new_app_only_has_to_add_a_demo_data_file(self):
        names = [name for _order, name, _fn in demo.discover_seeders()]
        self.assertEqual(names, ['organization', 'rbac', 'approvals', 'tasks', 'attendance', 'payroll', 'platform_admin', 'notifications'])
        orders = [order for order, _n, _f in demo.discover_seeders()]
        self.assertEqual(orders, sorted(orders))
