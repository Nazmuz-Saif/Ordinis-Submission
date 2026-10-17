import csv
import io
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from audit_log import context
from audit_log.models import AuditLog, AuditLogError
from core import demo
from core.test_utils import add_employee, give_role, login_as, register_company, rows
from organization.models import Department, Employee
from payroll.models import SalaryStructure
from rest_framework.test import APIClient

DEPARTMENTS = '/api/v1/organization/departments/'
LOGS = '/api/v1/audit-log/logs/'


def mine(client):
    return rows(client.get(LOGS))


class LoggingTests(TestCase):
    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.cid = self.ceo.company_id

    def dept(self, name='Sales'):
        return self.ceo.post(DEPARTMENTS, {'name': name}, format='json')

    def test_create_update_delete_each_write_one_row_with_the_right_actor_and_action(self):
        made = self.dept().data['id']
        self.ceo.patch(f'{DEPARTMENTS}{made}/', {'name': 'Sales and Marketing'}, format='json')
        self.ceo.delete(f'{DEPARTMENTS}{made}/')
        log = list(AuditLog.objects.filter(model_name='Department').order_by('created_at', 'id'))
        self.assertEqual([r.action for r in log], ['create', 'update', 'delete'])
        self.assertEqual({r.actor_email for r in log}, {'ceo@acme.com'})
        self.assertEqual({r.module for r in log}, {'organization'})
        self.assertEqual({str(r.company_id) for r in log}, {str(self.cid)})
        self.assertEqual(log[1].changed_fields, ['name'])
        self.assertEqual({str(r.object_id) for r in log}, {str(made)})
        self.assertEqual([r.status for r in log], ['success', 'success', 'warning'])
        self.assertIsNotNone(log[0].ip_address)

    def test_one_action_writes_one_row_not_two(self):
        self.dept('Ops')
        self.assertEqual(AuditLog.objects.filter(model_name='Department', action='create').count(), 1)

    def test_a_save_that_changes_nothing_writes_no_row(self):
        made = self.dept().data['id']
        before = AuditLog.objects.count()
        self.ceo.patch(f'{DEPARTMENTS}{made}/', {'name': 'Sales'}, format='json')
        self.assertEqual(AuditLog.objects.count(), before)

    def test_only_field_names_are_stored_never_values(self):
        person = add_employee(self.ceo, 'a@acme.com', 'A-1')
        pay = self.ceo.post('/api/v1/payroll/salary-structures/', {'employee': person['id'], 'base_salary': '123456.00'}, format='json')
        self.assertEqual(pay.status_code, 201, pay.content)
        self.ceo.patch(f"/api/v1/payroll/salary-structures/{pay.data['id']}/", {'base_salary': '987654.00'}, format='json')
        row = AuditLog.objects.filter(model_name='SalaryStructure', action='update').get()
        self.assertEqual(row.changed_fields, ['base_salary'])
        dump = ' '.join(str(v) for r in AuditLog.objects.all() for v in (r.object_repr, r.changed_fields, r.actor_email))
        for secret in ('123456', '987654'):
            self.assertNotIn(secret, dump)

    def test_nothing_is_logged_outside_a_request(self):
        Department.objects.create(company_id=self.cid, name='Direct')   # a plain ORM save, no request
        self.assertFalse(AuditLog.objects.filter(object_repr__startswith='Direct').exists())

    def test_a_system_context_logs_as_the_system(self):
        company = Employee.objects.get(user__email='ceo@acme.com').company
        with context.audit_context('System (demo data)'):
            Department.objects.create(company=company, name='Loaded')
        row = AuditLog.objects.get(object_repr__startswith='Loaded')
        self.assertEqual((row.actor_email, row.actor_id, row.action), ('System (demo data)', None, 'create'))

    def test_a_logging_error_never_blocks_the_action(self):
        with mock.patch('audit_log.services.record', side_effect=RuntimeError('disk full')):
            self.assertEqual(self.dept('Safe').status_code, 201)
        self.assertTrue(Department.objects.filter(name='Safe').exists())

    def test_leave_decisions_payslips_and_break_glass_reads_are_logged(self):
        from attendance.leave_models import LeaveType
        emp = add_employee(self.ceo, 'e@acme.com', 'E-1')
        boss = add_employee(self.ceo, 'b@acme.com', 'B-1')
        LeaveType.objects.create(company_id=self.cid, name='Annual', days_allowed_per_year=10)
        applicant = login_as('e@acme.com')
        leave = applicant.post('/api/v1/attendance/leave-requests/', {
            'leave_type': str(LeaveType.objects.get().id), 'start_date': '2030-03-04', 'end_date': '2030-03-05', 'reason': 'trip'}, format='json')
        self.assertEqual(leave.status_code, 201, leave.content)
        pending = rows(self.ceo.get('/api/v1/approvals/instances/?mine=pending'))[0]['id']
        self.ceo.post(f'/api/v1/approvals/instances/{pending}/approve/', {}, format='json')
        names = set(AuditLog.objects.values_list('model_name', 'action'))
        self.assertIn(('LeaveRequest', 'create'), names)
        self.assertIn(('LeaveRequest', 'update'), names)       # the decision
        self.assertIn(('ApprovalAction', 'create'), names)
        self.ceo.post('/api/v1/payroll/salary-structures/', {'employee': emp['id'], 'base_salary': '1000.00'}, format='json')
        self.ceo.post('/api/v1/payroll/payslips/', {'employee': emp['id'], 'month': '2020-01'}, format='json')
        self.assertTrue(AuditLog.objects.filter(model_name='Payslip', action='create').exists())

    def test_a_refused_write_is_logged_as_failed(self):
        add_employee(self.ceo, 'plain@acme.com', 'P-1')
        plain = login_as('plain@acme.com')
        self.assertEqual(plain.post(DEPARTMENTS, {'name': 'Nope'}, format='json').status_code, 403)
        row = AuditLog.objects.get(action='denied')
        self.assertEqual((row.status, row.actor_email, row.module), ('failed', 'plain@acme.com', 'organization'))
        self.assertIn('POST /api/v1/organization/departments/', row.object_repr)
        self.assertEqual(AuditLog.objects.filter(model_name='Department', action='create').count(), 0)


class AppendOnlyTests(TestCase):
    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.ceo.post(DEPARTMENTS, {'name': 'Sales'}, format='json')
        self.row = AuditLog.objects.filter(model_name='Department').first()

    def test_the_model_refuses_change_and_removal(self):
        self.row.action = 'delete'
        with self.assertRaises(AuditLogError):
            self.row.save()
        with self.assertRaises(AuditLogError):
            self.row.delete()
        with self.assertRaises(AuditLogError):
            AuditLog.objects.filter(pk=self.row.pk).update(action='delete')
        with self.assertRaises(AuditLogError):
            AuditLog.objects.all().delete()
        with self.assertRaises(AuditLogError):
            AuditLog.objects.bulk_update([self.row], ['action'])
        self.row.refresh_from_db()
        self.assertEqual(self.row.action, 'create')

    def test_the_api_has_no_way_to_write_a_row(self):
        for method in ('post', 'put', 'patch', 'delete'):
            for url in (LOGS, f'{LOGS}{self.row.id}/'):
                self.assertEqual(getattr(self.ceo, method)(url, {}, format='json').status_code, 405, f'{method} {url}')

    def test_the_rows_outlive_a_deleted_company(self):
        from tenants.models import Company
        company = Company.objects.get(subdomain='acme')
        total = AuditLog.objects.count()
        company.delete()
        self.assertEqual(AuditLog.objects.count(), total)
        kept = AuditLog.objects.filter(model_name='Department').first()
        self.assertEqual((kept.company_id, kept.company_name), (None, 'Acme'))


class AccessTests(TestCase):
    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.other = register_company('Beta', 'beta', 'ceo@beta.com')
        self.ceo.post(DEPARTMENTS, {'name': 'Sales'}, format='json')
        self.other.post(DEPARTMENTS, {'name': 'Secret'}, format='json')

    def test_the_ceo_sees_only_their_own_company(self):
        texts = ' | '.join(r['object_repr'] for r in mine(self.ceo))
        self.assertIn('Sales', texts)
        self.assertNotIn('Secret', texts)
        other = ' | '.join(r['object_repr'] for r in mine(self.other))
        self.assertIn('Secret', other)
        self.assertNotIn('Sales', other)

    def test_another_company_gets_404_for_a_row(self):
        row = AuditLog.objects.filter(object_repr__startswith='Sales').first()
        self.assertEqual(self.other.get(f'{LOGS}{row.id}/').status_code, 404)
        self.assertEqual(self.ceo.get(f'{LOGS}{row.id}/').status_code, 200)

    def test_someone_without_the_permission_is_blocked_but_gets_it_when_given(self):
        add_employee(self.ceo, 'plain@acme.com', 'P-1')
        plain = login_as('plain@acme.com')
        self.assertEqual(plain.get(LOGS).status_code, 403)
        self.assertEqual(plain.get(LOGS + 'export/').status_code, 403)
        person = Employee.objects.get(user__email='plain@acme.com')
        give_role(self.ceo.company_id, str(person.id), ['view_audit_log'], 'Auditor')
        self.assertEqual(login_as('plain@acme.com').get(LOGS).status_code, 200)

    def test_it_needs_a_login(self):
        self.assertEqual(APIClient().get(LOGS).status_code, 401)

    def test_a_platform_admin_has_no_access_to_a_companys_log(self):
        from accounts.models import User
        User.objects.create_user(email='root@x.com', password='StrongPass123', is_platform_admin=True)
        admin = login_as('root@x.com')
        self.assertEqual(admin.get(LOGS).status_code, 403)


class FilterAndExportTests(TestCase):
    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        for n in range(3):
            self.ceo.post(DEPARTMENTS, {'name': f'D{n}'}, format='json')
        add_employee(self.ceo, 'a@acme.com', 'A-1')

    def test_filter_by_module_action_status_and_text(self):
        self.assertTrue(all(r['module'] == 'organization' for r in mine_filtered(self.ceo, 'module=organization')))
        self.assertEqual({r['action'] for r in mine_filtered(self.ceo, 'action=create')}, {'create'})
        self.assertEqual(len(mine_filtered(self.ceo, 'q=D1')), 1)
        self.assertEqual(mine_filtered(self.ceo, 'module=nothing'), [])
        self.assertEqual(mine_filtered(self.ceo, 'status=failed'), [])
        self.assertEqual(len(mine_filtered(self.ceo, 'date_from=2000-01-01&date_to=2999-01-01&model_name=Department')), 3)
        self.assertEqual(mine_filtered(self.ceo, 'date_from=2999-01-01'), [])

    def test_the_modules_list_has_only_modules_that_appear(self):
        found = self.ceo.get(LOGS + 'modules/').json()
        data = found.get('data', found) if isinstance(found, dict) else found
        self.assertIn('organization', data)
        self.assertNotIn('payroll', data)

    def test_the_list_is_paged_newest_first(self):
        page = rows(self.ceo.get(LOGS + '?page_size=2'))
        self.assertEqual(len(page), 2)
        everything = rows(self.ceo.get(LOGS + '?page_size=100'))
        self.assertGreater(len(everything), 2)
        times = [r['created_at'] for r in everything]
        self.assertEqual(times, sorted(times, reverse=True))

    def test_export_has_the_same_rows_as_the_filtered_page(self):
        res = self.ceo.get(LOGS + 'export/?module=organization&model_name=Department')
        self.assertEqual(res.status_code, 200)
        self.assertIn('text/csv', res['Content-Type'])
        self.assertIn('attachment', res['Content-Disposition'])
        table = list(csv.reader(io.StringIO(res.content.decode())))
        self.assertEqual(table[0][:4], ['Date and time', 'User', 'Action', 'Module'])
        self.assertEqual(len(table) - 1, len(mine_filtered(self.ceo, 'module=organization&model_name=Department', page=False)))
        self.assertTrue(all(r[3] == 'organization' for r in table[1:]))

    def test_an_export_is_itself_logged_and_not_in_its_own_file(self):
        res = self.ceo.get(LOGS + 'export/')
        file_rows = list(csv.reader(io.StringIO(res.content.decode())))[1:]
        self.assertFalse(any(r[2] == 'Exported' for r in file_rows))
        logged = AuditLog.objects.get(action='export')
        self.assertEqual((logged.status, logged.actor_email), ('warning', 'ceo@acme.com'))
        self.assertIn('rows', logged.object_repr)

    def test_a_cell_that_could_run_as_a_formula_is_defused(self):
        from audit_log.views import _csv_safe
        for danger in ('=SUM(A1:A9)', '+1', '-1', '@cmd'):
            self.assertEqual(_csv_safe(danger), "'" + danger)
        self.assertEqual(_csv_safe('plain'), 'plain')
        self.assertEqual(_csv_safe(None), '')


def mine_filtered(client, query, page=True):
    res = client.get(LOGS + '?' + query + ('&page_size=100' if page else '&page_size=100'))
    return rows(res)


class DemoDataTests(TestCase):
    def test_loading_the_demo_company_is_logged_as_the_system_in_its_own_company(self):
        call_command('seed_demo_data', stdout=io.StringIO())
        ceo = login_as(demo.email('ceo'), demo.PASSWORD)
        company = Employee.objects.get(user__email=demo.email('ceo')).company
        stored = AuditLog.objects.filter(company=company)
        self.assertGreater(stored.count(), 50)
        self.assertEqual(set(stored.values_list('actor_email', flat=True)), {'System (demo data)'})
        self.assertGreaterEqual(len(set(stored.values_list('module', flat=True))), 5)
        shown = mine(ceo)
        self.assertEqual({r['actor_email'] for r in shown}, {'System (demo data)'})

    def test_running_the_loader_again_adds_no_noise(self):
        call_command('seed_demo_data', stdout=io.StringIO())
        before = AuditLog.objects.count()
        call_command('seed_demo_data', stdout=io.StringIO())
        self.assertEqual(AuditLog.objects.count(), before)
