from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from attendance.services import local_today
from core.test_utils import add_employee, give_role, login_as, register_company, rows
from organization.models import Employee
from payroll.models import Payslip, SalaryStructure

PAYSLIPS = '/api/v1/payroll/payslips/'


class Base(TestCase):
    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.cid = self.ceo.company_id
        self.acc = add_employee(self.ceo, 'acc@acme.com', 'A-1')
        give_role(self.cid, self.acc['id'], ['manage_finance'], 'Accountant')
        self.acc_c = login_as('acc@acme.com')
        self.dev = add_employee(self.ceo, 'dev@acme.com', 'A-2')
        self.dev_c = login_as('dev@acme.com')
        self.mgr = add_employee(self.ceo, 'mgr@acme.com', 'A-3')
        give_role(self.cid, self.mgr['id'], ['create_task', 'manage_employees'], 'Manager')
        self.mgr_c = login_as('mgr@acme.com')
        Employee.objects.filter(id=self.dev['id']).update(reports_to_id=self.mgr['id'])   # mgr is dev's boss
        self.beta = register_company('Beta', 'beta', 'ceo@beta.com')
        self.today, _ = local_today(Employee.objects.get(id=self.dev['id']).company)
        self.this_month = f'{self.today.year}-{self.today.month:02d}'
        SalaryStructure.objects.create(company_id=self.cid, employee_id=self.dev['id'], base_salary=50000,
                                       allowances={'House Rent': 8000, 'Transport': 2000})

    def generate(self, client=None, employee=None, month=None, **extra):
        body = {'employee': (employee or self.dev)['id'] if isinstance(employee or self.dev, dict) else str(employee),
                'month': self.this_month if month is None else month}
        body.update(extra)
        return (client or self.acc_c).post(PAYSLIPS, body, format='json')


class GenerateTests(Base):
    def test_payslip_shows_gross_deductions_and_net_from_the_salary_structure(self):
        res = self.generate(deductions='3000.50', deduction_note='Advance')
        self.assertEqual(res.status_code, 201, res.content)
        d = res.data
        self.assertEqual((d['base_salary'], d['gross_amount'], d['deductions'], d['net_amount']),
                         ('50000.00', '60000.00', '3000.50', '56999.50'))
        self.assertEqual(d['allowances'], {'House Rent': 8000, 'Transport': 2000})
        self.assertEqual((d['month'], d['employee_email'], d['employee_code']), (self.this_month, 'dev@acme.com', 'A-2'))
        self.assertEqual((d['deduction_note'], d['generated_by_email']), ('Advance', 'acc@acme.com'))
        self.assertIn(str(self.today.year), d['month_label'])

    def test_deductions_default_to_zero(self):
        d = self.generate().data
        self.assertEqual((d['deductions'], d['net_amount']), ('0.00', '60000.00'))

    def test_a_past_month_is_fine(self):
        self.assertEqual(self.generate(month='2025-01').data['month_label'], 'January 2025')

    def test_a_future_month_is_refused(self):
        future = f'{self.today.year + 1}-01'
        res = self.generate(month=future)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data['error']['code'], 'PAYSLIP_FUTURE_MONTH')
        self.assertIn('has not started yet', res.content.decode())
        self.assertEqual(Payslip.objects.count(), 0)

    def test_bad_month_formats_are_refused(self):
        for bad in ('2026-13', '2026-00', '10-2026', '2026/10', 'October', '', '2026-1'):
            self.assertEqual(self.generate(month=bad).status_code, 400, bad)
        self.assertEqual(Payslip.objects.count(), 0)

    def test_employee_without_a_salary_structure_gets_a_clear_message(self):
        res = self.generate(employee=self.mgr)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data['error']['code'], 'PAYSLIP_NO_SALARY_STRUCTURE')
        self.assertIn('mgr@acme.com has no salary structure yet', res.content.decode())
        self.assertEqual(Payslip.objects.count(), 0)

    def test_deductions_must_be_between_zero_and_gross(self):
        for bad in ('-1', '60000.01', 'abc'):
            res = self.generate(deductions=bad)
            self.assertEqual(res.status_code, 400, bad)
        self.assertEqual(self.generate(deductions='60000.00').data['net_amount'], '0.00')

    def test_the_payslip_is_a_snapshot_later_salary_changes_do_not_touch_it(self):
        pid = self.generate().data['id']
        SalaryStructure.objects.filter(employee_id=self.dev['id']).update(base_salary=99999, allowances={})
        again = self.acc_c.get(f'{PAYSLIPS}{pid}/').data
        self.assertEqual((again['base_salary'], again['gross_amount'], again['net_amount']), ('50000.00', '60000.00', '60000.00'))

    def test_the_client_cannot_choose_the_amounts(self):
        d = self.generate(gross_amount='999999', net_amount='999999', base_salary='1', generated_by_email='x').data
        self.assertEqual((d['gross_amount'], d['net_amount']), ('60000.00', '60000.00'))


class DuplicateTests(Base):
    def test_a_second_payslip_for_the_same_employee_and_month_is_refused(self):
        self.assertEqual(self.generate().status_code, 201)
        res = self.generate(deductions='100')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data['error']['code'], 'PAYSLIP_ALREADY_EXISTS')
        self.assertIn('already exists', res.content.decode())
        self.assertEqual(Payslip.objects.count(), 1)
        self.assertEqual(Payslip.objects.get().deductions, 0, 'the first payslip is untouched')

    def test_another_month_or_another_employee_is_not_a_duplicate(self):
        SalaryStructure.objects.create(company_id=self.cid, employee_id=self.mgr['id'], base_salary=70000)
        self.assertEqual(self.generate().status_code, 201)
        self.assertEqual(self.generate(month='2025-12').status_code, 201)
        self.assertEqual(self.generate(employee=self.mgr['id']).status_code, 201)

    def test_the_database_itself_refuses_a_duplicate(self):
        self.generate()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Payslip.objects.create(company_id=self.cid, employee_id=self.dev['id'], year=self.today.year, month=self.today.month,
                                   base_salary=1, gross_amount=1, deductions=0, net_amount=1)

    def test_the_database_refuses_nonsense_values(self):
        base = dict(company_id=self.cid, employee_id=self.dev['id'], base_salary=100, gross_amount=100)
        for extra in ({'year': 2020, 'month': 13, 'deductions': 0, 'net_amount': 100},
                      {'year': 2020, 'month': 0, 'deductions': 0, 'net_amount': 100},
                      {'year': 2020, 'month': 5, 'deductions': -1, 'net_amount': 101},
                      {'year': 2020, 'month': 5, 'deductions': 101, 'net_amount': -1}):
            with self.assertRaises(IntegrityError), transaction.atomic():
                Payslip.objects.create(**base, **extra)

    def test_a_race_that_slips_past_the_check_still_gives_the_clear_message(self):
        from payroll import services
        class Lying:
            def exists(self):
                return False

        original = services.Payslip.objects
        self.generate()                                    # the row exists now
        services.Payslip.objects = type('M', (), {
            'filter': staticmethod(lambda **kw: Lying() if 'year' in kw else original.filter(**kw)),
            'create': staticmethod(original.create)})()
        try:
            res = self.generate()
        finally:
            services.Payslip.objects = original
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data['error']['code'], 'PAYSLIP_ALREADY_EXISTS')

    def test_a_voided_payslip_lets_the_month_be_generated_again(self):
        pid = self.generate().data['id']
        self.assertEqual(self.acc_c.delete(f'{PAYSLIPS}{pid}/').status_code, 204)
        self.assertEqual(self.generate().status_code, 201)


class PermissionTests(Base):
    def test_generating_needs_the_finance_permission_whatever_the_hierarchy(self):
        for client in (self.dev_c, self.mgr_c):
            res = self.generate(client=client)
            self.assertEqual(res.status_code, 403)
        self.assertEqual(Payslip.objects.count(), 0)

    def test_the_ceo_admin_role_can_generate(self):
        self.assertEqual(self.generate(client=self.ceo).status_code, 201)

    def test_nobody_but_finance_can_void(self):
        pid = self.generate().data['id']
        self.assertEqual(self.mgr_c.delete(f'{PAYSLIPS}{pid}/').status_code, 403)    # no finance permission, whatever the id
        self.assertEqual(self.dev_c.delete(f'{PAYSLIPS}{pid}/').status_code, 403)    # their own payslip, still no permission
        self.assertEqual(Payslip.objects.count(), 1)

    def test_a_payslip_cannot_be_edited(self):
        pid = self.generate().data['id']
        for call in (self.acc_c.put, self.acc_c.patch):
            self.assertEqual(call(f'{PAYSLIPS}{pid}/', {'deductions': '0'}, format='json').status_code, 405)

    def test_login_is_required(self):
        self.assertIn(APIClient().get(PAYSLIPS).status_code, (401, 403))
        self.assertIn(APIClient().post(PAYSLIPS, {}, format='json').status_code, (401, 403))

    def test_a_suspended_company_cannot_generate(self):
        from tenants.models import Company
        Company.objects.filter(id=self.cid).update(is_active=False)
        self.assertEqual(self.generate().status_code, 403)


class OwnPayslipOnlyTests(Base):
    def setUp(self):
        super().setUp()
        SalaryStructure.objects.create(company_id=self.cid, employee_id=self.mgr['id'], base_salary=70000)
        self.dev_slip = self.generate().data['id']
        self.mgr_slip = self.generate(employee=self.mgr['id']).data['id']

    def test_an_employee_sees_only_their_own_payslips(self):
        self.assertEqual([p['id'] for p in rows(self.dev_c.get(PAYSLIPS))], [self.dev_slip])
        self.assertEqual(self.dev_c.get(f'{PAYSLIPS}{self.dev_slip}/').status_code, 200)
        self.assertEqual(self.dev_c.get(f'{PAYSLIPS}{self.mgr_slip}/').status_code, 404)

    def test_a_boss_does_not_see_a_subordinates_payslip(self):
        self.assertEqual([p['id'] for p in rows(self.mgr_c.get(PAYSLIPS))], [self.mgr_slip])
        self.assertEqual(self.mgr_c.get(f'{PAYSLIPS}{self.dev_slip}/').status_code, 404)

    def test_finance_sees_the_whole_company_or_just_their_own_with_mine(self):
        self.assertEqual({p['id'] for p in rows(self.acc_c.get(PAYSLIPS))}, {self.dev_slip, self.mgr_slip})
        SalaryStructure.objects.create(company_id=self.cid, employee_id=self.acc['id'], base_salary=40000)
        own = self.generate(employee=self.acc['id']).data['id']
        self.assertEqual([p['id'] for p in rows(self.acc_c.get(PAYSLIPS + '?mine=true'))], [own])

    def test_finance_can_filter_by_employee_and_month(self):
        self.generate(month='2025-12')
        by_month = rows(self.acc_c.get(PAYSLIPS + '?month=2025-12'))
        self.assertEqual([p['month'] for p in by_month], ['2025-12'])
        by_emp = rows(self.acc_c.get(f'{PAYSLIPS}?employee={self.dev["id"]}'))
        self.assertEqual({p['employee_email'] for p in by_emp}, {'dev@acme.com'})
        self.assertEqual(len(rows(self.acc_c.get(PAYSLIPS + '?month=garbage'))), 3, 'a bad filter is ignored')

    def test_the_employee_filter_does_not_open_other_peoples_payslips(self):
        res = self.dev_c.get(f'{PAYSLIPS}?employee={self.mgr["id"]}')
        self.assertEqual([p['id'] for p in rows(res)], [self.dev_slip])

    def test_another_company_sees_and_touches_nothing(self):
        self.assertEqual(rows(self.beta.get(PAYSLIPS)), [])
        self.assertEqual(self.beta.get(f'{PAYSLIPS}{self.dev_slip}/').status_code, 404)
        self.assertEqual(self.beta.delete(f'{PAYSLIPS}{self.dev_slip}/').status_code, 404)

    def test_finance_of_another_company_cannot_generate_for_this_employee(self):
        res = self.beta.post(PAYSLIPS, {'employee': self.dev['id'], 'month': self.this_month}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Payslip.objects.filter(company_id=self.beta.company_id).count(), 0)

    def test_list_is_newest_month_first_and_paged(self):
        for m in range(1, 11):
            self.generate(month=f'2024-{m:02d}')
        res = self.acc_c.get(PAYSLIPS)
        months = [p['month'] for p in rows(res)]
        self.assertEqual(months, sorted(months, reverse=True))
        self.assertEqual(res.data['pagination']['count'], 12)
