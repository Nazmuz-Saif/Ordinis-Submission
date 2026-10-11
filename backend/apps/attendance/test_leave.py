from datetime import date, timedelta

from django.test import TestCase
from rest_framework.test import APIClient

from attendance.leave_models import LeaveRequest, LeaveType
from attendance.services import local_today
from core.test_utils import add_employee, give_role, login_as, register_company, rows
from organization.models import Employee

TYPES = '/api/v1/attendance/leave-types/'
LEAVES = '/api/v1/attendance/leave-requests/'
BALANCE = LEAVES + 'balance/'


class Base(TestCase):
    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.cid = self.ceo.company_id
        self.dev = add_employee(self.ceo, 'dev@acme.com', 'A-1')
        self.dev_c = login_as('dev@acme.com')
        self.boss = add_employee(self.ceo, 'boss@acme.com', 'A-2')
        give_role(self.cid, self.boss['id'], ['manage_employees', 'create_task'], 'Boss')
        self.boss_c = login_as('boss@acme.com')
        Employee.objects.filter(id=self.dev['id']).update(reports_to_id=self.boss['id'])
        self.beta = register_company('Beta', 'beta', 'ceo@beta.com')
        self.year = local_today(Employee.objects.get(id=self.dev['id']).company)[0].year
        self.annual = LeaveType.objects.create(company_id=self.cid, name='Annual Leave', days_allowed_per_year=5)

    def d(self, month, day, year=None):
        return str(date(year or self.year, month, day))

    def apply(self, start, end, client=None, leave_type=None, reason='Family trip', **extra):
        body = {'leave_type': str((leave_type or self.annual).id), 'start_date': start, 'end_date': end, 'reason': reason}
        body.update(extra)
        return (client or self.dev_c).post(LEAVES, body, format='json')

    def remaining(self, client=None, name='Annual Leave', year=None):
        url = BALANCE + (f'?year={year}' if year else '')
        return {b['name']: b for b in (client or self.dev_c).get(url).data}[name]['remaining']


class LeaveTypeTests(Base):
    def test_the_ceo_creates_a_leave_type_with_days_per_year(self):
        res = self.ceo.post(TYPES, {'name': 'Sick Leave', 'days_allowed_per_year': 10}, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual((res.data['name'], res.data['days_allowed_per_year']), ('Sick Leave', 10))
        self.assertEqual(str(LeaveType.objects.get(name='Sick Leave').company_id), str(self.cid))

    def test_everyone_can_read_the_types_but_not_change_them(self):
        self.assertEqual([t['name'] for t in rows(self.dev_c.get(TYPES))], ['Annual Leave'])
        tid = str(self.annual.id)
        self.assertEqual(self.dev_c.post(TYPES, {'name': 'X', 'days_allowed_per_year': 1}, format='json').status_code, 403)
        self.assertEqual(self.dev_c.patch(f'{TYPES}{tid}/', {'days_allowed_per_year': 99}, format='json').status_code, 403)
        self.assertEqual(self.dev_c.delete(f'{TYPES}{tid}/').status_code, 403)
        self.assertEqual(self.boss_c.post(TYPES, {'name': 'X', 'days_allowed_per_year': 1}, format='json').status_code, 403, 'a boss is not an HR')
        self.assertEqual(LeaveType.objects.get(id=tid).days_allowed_per_year, 5)

    def test_someone_given_the_permission_can_manage_types(self):
        give_role(self.cid, self.dev['id'], ['manage_leave_types'], 'HR')
        self.assertEqual(self.dev_c.post(TYPES, {'name': 'Casual', 'days_allowed_per_year': 7}, format='json').status_code, 201)
        tid = str(self.annual.id)
        self.assertEqual(self.dev_c.patch(f'{TYPES}{tid}/', {'days_allowed_per_year': 20}, format='json').status_code, 200)

    def test_names_must_be_filled_and_unique_inside_the_company_only(self):
        for bad in ({'name': '', 'days_allowed_per_year': 1}, {'name': '  ', 'days_allowed_per_year': 1},
                    {'name': 'annual leave', 'days_allowed_per_year': 1}, {'name': 'X', 'days_allowed_per_year': -1},
                    {'name': 'X', 'days_allowed_per_year': 367}, {'name': 'X', 'days_allowed_per_year': 'many'}):
            self.assertEqual(self.ceo.post(TYPES, bad, format='json').status_code, 400, bad)
        self.assertEqual(self.beta.post(TYPES, {'name': 'Annual Leave', 'days_allowed_per_year': 5}, format='json').status_code, 201)
        self.assertEqual(LeaveType.objects.count(), 2)

    def test_renaming_to_its_own_name_is_fine(self):
        res = self.ceo.patch(f'{TYPES}{self.annual.id}/', {'name': 'Annual Leave', 'days_allowed_per_year': 6}, format='json')
        self.assertEqual(res.status_code, 200)

    def test_another_companys_types_are_invisible_and_untouchable(self):
        self.assertEqual(rows(self.beta.get(TYPES)), [])
        self.assertEqual(self.beta.get(f'{TYPES}{self.annual.id}/').status_code, 404)
        self.assertEqual(self.beta.patch(f'{TYPES}{self.annual.id}/', {'days_allowed_per_year': 1}, format='json').status_code, 404)

    def test_the_client_cannot_choose_the_company(self):
        res = self.ceo.post(TYPES, {'name': 'Sneaky', 'days_allowed_per_year': 3, 'company': str(self.beta.company_id)}, format='json')
        self.assertEqual(str(LeaveType.objects.get(name='Sneaky').company_id), str(self.cid))

    def test_a_type_with_requests_cannot_be_deleted_an_unused_one_can(self):
        self.apply(self.d(3, 1), self.d(3, 2))
        res = self.ceo.delete(f'{TYPES}{self.annual.id}/')
        self.assertEqual(res.status_code, 400)
        self.assertIn('already has leave requests', res.content.decode())
        unused = self.ceo.post(TYPES, {'name': 'Unused', 'days_allowed_per_year': 1}, format='json').data['id']
        self.assertEqual(self.ceo.delete(f'{TYPES}{unused}/').status_code, 204)


class ApplyTests(Base):
    def test_a_request_inside_the_balance_starts_pending(self):
        res = self.apply(self.d(3, 10), self.d(3, 12))
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual((res.data['status'], res.data['days'], res.data['leave_type_name']), ('pending', 3, 'Annual Leave'))
        self.assertEqual((str(res.data['start_date']), str(res.data['end_date']), res.data['reason']), (self.d(3, 10), self.d(3, 12), 'Family trip'))

    def test_a_single_day_counts_as_one(self):
        self.assertEqual(self.apply(self.d(3, 10), self.d(3, 10)).data['days'], 1)

    def test_more_days_than_the_balance_is_refused_and_the_message_shows_what_is_left(self):
        self.apply(self.d(3, 1), self.d(3, 2))                      # 2 used, 3 left
        res = self.apply(self.d(4, 1), self.d(4, 5))                # asks 5
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data['error']['code'], 'LEAVE_INSUFFICIENT_BALANCE')
        self.assertEqual(res.data['error']['message'],
                         f'You asked for 5 days of Annual Leave, but your remaining balance for {self.year} is 3 days.')
        self.assertEqual(LeaveRequest.objects.count(), 1)

    def test_singular_wording_and_zero_left(self):
        self.apply(self.d(3, 1), self.d(3, 4))                      # 4 used, 1 left
        self.assertIn('is 1 day.', self.apply(self.d(4, 1), self.d(4, 2)).data['error']['message'])
        self.apply(self.d(5, 1), self.d(5, 1))                      # exactly the last day
        self.assertIn('is 0 days.', self.apply(self.d(6, 1), self.d(6, 1)).data['error']['message'])

    def test_using_exactly_the_remaining_days_is_allowed(self):
        self.assertEqual(self.apply(self.d(3, 1), self.d(3, 5)).status_code, 201)
        self.assertEqual(self.remaining(), 0)

    def test_a_type_with_zero_days_allows_nothing(self):
        none = LeaveType.objects.create(company_id=self.cid, name='Unpaid', days_allowed_per_year=0)
        res = self.apply(self.d(3, 1), self.d(3, 1), leave_type=none)
        self.assertEqual(res.status_code, 400)
        self.assertIn('is 0 days.', res.content.decode())

    def test_dates_in_the_wrong_order_are_refused(self):
        res = self.apply(self.d(3, 10), self.d(3, 9))
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data['error']['code'], 'LEAVE_END_BEFORE_START')
        self.assertEqual(res.data['error']['message'], 'The end date cannot be before the start date.')
        self.assertEqual(LeaveRequest.objects.count(), 0)

    def test_the_database_also_refuses_reversed_dates(self):
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError), transaction.atomic():
            LeaveRequest.objects.create(company_id=self.cid, employee_id=self.dev['id'], leave_type=self.annual,
                                        start_date=date(2026, 3, 10), end_date=date(2026, 3, 9), days=1, reason='x')

    def test_a_reason_and_all_fields_are_required(self):
        for reason in ('', '   '):
            res = self.apply(self.d(3, 1), self.d(3, 1), reason=reason)
            self.assertEqual(res.status_code, 400, reason)
        for missing in ('leave_type', 'start_date', 'end_date'):
            body = {'leave_type': str(self.annual.id), 'start_date': self.d(3, 1), 'end_date': self.d(3, 1), 'reason': 'x'}
            body.pop(missing)
            self.assertEqual(self.dev_c.post(LEAVES, body, format='json').status_code, 400, missing)
        self.assertEqual(self.apply('not-a-date', self.d(3, 1)).status_code, 400)
        self.assertEqual(LeaveRequest.objects.count(), 0)

    def test_another_companys_leave_type_is_refused(self):
        theirs = LeaveType.objects.create(company_id=self.beta.company_id, name='Theirs', days_allowed_per_year=99)
        self.assertEqual(self.apply(self.d(3, 1), self.d(3, 1), leave_type=theirs).status_code, 400)
        self.assertEqual(LeaveRequest.objects.count(), 0)

    def test_the_client_cannot_set_status_days_or_employee(self):
        res = self.apply(self.d(3, 1), self.d(3, 2), status='approved', days=99, employee=self.boss['id'])
        self.assertEqual((res.data['status'], res.data['days']), ('pending', 2))
        self.assertEqual(str(LeaveRequest.objects.get().employee_id), self.dev['id'])

    def test_past_dates_are_allowed_for_leave_already_taken(self):
        self.assertEqual(self.apply(self.d(1, 5, self.year - 1), self.d(1, 6, self.year - 1)).status_code, 201)

    def test_overlapping_your_own_leave_is_refused_adjacent_days_are_not(self):
        self.apply(self.d(3, 10), self.d(3, 12))
        for start, end in (('3-12', '3-14'), ('3-9', '3-10'), ('3-11', '3-11'), ('3-8', '3-15')):
            (m1, d1), (m2, d2) = (map(int, start.split('-')), map(int, end.split('-')))
            res = self.apply(self.d(m1, d1), self.d(m2, d2))
            self.assertEqual(res.data['error']['code'], 'LEAVE_OVERLAP', start)
        self.assertIn(f'{self.d(3, 10)} to {self.d(3, 12)}', self.apply(self.d(3, 11), self.d(3, 11)).content.decode())
        self.assertEqual(self.apply(self.d(3, 13), self.d(3, 13)).status_code, 201)

    def test_two_people_may_take_the_same_days(self):
        self.apply(self.d(3, 10), self.d(3, 12))
        self.assertEqual(self.apply(self.d(3, 10), self.d(3, 12), client=self.boss_c).status_code, 201)

    def test_login_is_required_and_a_suspended_company_cannot_apply(self):
        self.assertIn(APIClient().post(LEAVES, {}, format='json').status_code, (401, 403))
        from tenants.models import Company
        Company.objects.filter(id=self.cid).update(is_active=False)
        self.assertEqual(self.apply(self.d(3, 1), self.d(3, 1)).status_code, 403)


class BalanceTests(Base):
    def test_pending_and_approved_use_days_rejected_and_cancelled_give_them_back(self):
        a = self.apply(self.d(3, 1), self.d(3, 2)).data['id']       # 2
        b = self.apply(self.d(4, 1), self.d(4, 1)).data['id']       # 1
        self.assertEqual(self.remaining(), 2)
        LeaveRequest.objects.filter(id=a).update(status='approved')
        self.assertEqual(self.remaining(), 2)
        LeaveRequest.objects.filter(id=b).update(status='rejected')
        self.assertEqual(self.remaining(), 3)
        LeaveRequest.objects.filter(id=a).update(status='cancelled')
        self.assertEqual(self.remaining(), 5)

    def test_balance_splits_approved_and_pending(self):
        a = self.apply(self.d(3, 1), self.d(3, 2)).data['id']
        self.apply(self.d(4, 1), self.d(4, 1))
        LeaveRequest.objects.filter(id=a).update(status='approved')
        row = {b['name']: b for b in self.dev_c.get(BALANCE).data}['Annual Leave']
        self.assertEqual((row['allowed'], row['approved'], row['pending'], row['remaining'], row['year']), (5, 2, 1, 2, self.year))

    def test_balance_is_per_person_per_year_per_type(self):
        sick = LeaveType.objects.create(company_id=self.cid, name='Sick Leave', days_allowed_per_year=10)
        self.apply(self.d(3, 1), self.d(3, 3))
        self.assertEqual(self.remaining(client=self.boss_c), 5, "someone else's leave does not use mine")
        self.assertEqual(self.remaining(name='Sick Leave'), 10, 'another type is separate')
        self.assertEqual(self.remaining(year=self.year + 1), 5, 'next year starts full')
        self.assertEqual([b['name'] for b in self.dev_c.get(BALANCE).data], ['Annual Leave', 'Sick Leave'])

    def test_a_request_over_new_year_is_checked_against_each_years_balance(self):
        res = self.apply(self.d(12, 30), self.d(1, 3, self.year + 1))      # 2 days this year, 3 next
        self.assertEqual((res.status_code, res.data['days']), (201, 5))
        self.assertEqual((self.remaining(), self.remaining(year=self.year + 1)), (3, 2))
        # next year has 3 left; ask for 3 more days in January next year: only 2 remain
        res = self.apply(self.d(1, 10, self.year + 1), self.d(1, 12, self.year + 1))
        self.assertEqual(res.status_code, 400)
        self.assertIn(f'balance for {self.year + 1} is 2 days', res.content.decode())

    def test_a_split_request_that_does_not_fit_the_second_year_names_that_year(self):
        self.apply(self.d(1, 5, self.year + 1), self.d(1, 8, self.year + 1))   # 4 of 5 used next year
        res = self.apply(self.d(12, 31), self.d(1, 2, self.year + 1))          # 1 day now, 2 next year
        self.assertEqual(res.status_code, 400)
        self.assertIn(f'balance for {self.year + 1} is 1 day.', res.content.decode())

    def test_changing_the_types_days_changes_the_balance_at_once(self):
        self.apply(self.d(3, 1), self.d(3, 5))
        self.assertEqual(self.apply(self.d(4, 1), self.d(4, 1)).status_code, 400)
        self.ceo.patch(f'{TYPES}{self.annual.id}/', {'days_allowed_per_year': 8}, format='json')
        self.assertEqual(self.remaining(), 3)
        self.assertEqual(self.apply(self.d(4, 1), self.d(4, 1)).status_code, 201)

    def test_year_parameter_is_checked(self):
        for bad in ('abc', '1999', '3000', '-1'):
            self.assertEqual(self.dev_c.get(BALANCE + f'?year={bad}').status_code, 400, bad)

    def test_another_companys_types_never_appear_in_my_balance(self):
        LeaveType.objects.create(company_id=self.beta.company_id, name='Beta only', days_allowed_per_year=3)
        self.assertEqual([b['name'] for b in self.dev_c.get(BALANCE).data], ['Annual Leave'])


class MyRequestsOnlyTests(Base):
    def setUp(self):
        super().setUp()
        self.dev_leave = self.apply(self.d(3, 1), self.d(3, 2)).data['id']
        self.boss_leave = self.apply(self.d(4, 1), self.d(4, 2), client=self.boss_c).data['id']

    def test_each_person_sees_only_their_own_requests(self):
        self.assertEqual([r['id'] for r in rows(self.dev_c.get(LEAVES))], [self.dev_leave])
        self.assertEqual([r['id'] for r in rows(self.boss_c.get(LEAVES))], [self.boss_leave])
        self.assertEqual(rows(self.ceo.get(LEAVES)), [], 'not even the CEO sees other people here')

    def test_a_boss_cannot_open_a_subordinates_request(self):
        self.assertEqual(self.boss_c.get(f'{LEAVES}{self.dev_leave}/').status_code, 404)
        self.assertEqual(self.dev_c.get(f'{LEAVES}{self.dev_leave}/').status_code, 200)
        self.assertEqual(self.dev_c.get(f'{LEAVES}{self.boss_leave}/').status_code, 404)

    def test_another_company_sees_nothing(self):
        self.assertEqual(rows(self.beta.get(LEAVES)), [])
        self.assertEqual(self.beta.get(f'{LEAVES}{self.dev_leave}/').status_code, 404)

    def test_newest_first_and_status_filter(self):
        later = self.apply(self.d(8, 1), self.d(8, 1), leave_type=LeaveType.objects.create(company_id=self.cid, name='Sick', days_allowed_per_year=3)).data['id']
        self.assertEqual([r['id'] for r in rows(self.dev_c.get(LEAVES))], [later, self.dev_leave])
        LeaveRequest.objects.filter(id=later).update(status='approved')
        self.assertEqual([r['id'] for r in rows(self.dev_c.get(LEAVES + '?status=approved'))], [later])
        self.assertEqual(len(rows(self.dev_c.get(LEAVES + '?status=banana'))), 2, 'unknown filter is ignored')

    def test_requests_cannot_be_edited_or_deleted_through_the_api(self):
        for call in (self.dev_c.put, self.dev_c.patch, self.dev_c.delete):
            self.assertEqual(call(f'{LEAVES}{self.dev_leave}/', {'reason': 'x'}, format='json').status_code, 405)


class CancelTests(Base):
    def test_cancelling_a_pending_request_returns_the_days(self):
        rid = self.apply(self.d(3, 1), self.d(3, 4)).data['id']
        self.assertEqual(self.remaining(), 1)
        res = self.dev_c.post(f'{LEAVES}{rid}/cancel/')
        self.assertEqual((res.status_code, res.data['status']), (200, 'cancelled'))
        self.assertEqual(self.remaining(), 5)

    def test_only_pending_requests_can_be_cancelled(self):
        rid = self.apply(self.d(3, 1), self.d(3, 1)).data['id']
        self.dev_c.post(f'{LEAVES}{rid}/cancel/')
        again = self.dev_c.post(f'{LEAVES}{rid}/cancel/')
        self.assertEqual((again.status_code, again.data['error']['code']), (400, 'LEAVE_NOT_PENDING'))
        approved = self.apply(self.d(4, 1), self.d(4, 1)).data['id']
        LeaveRequest.objects.filter(id=approved).update(status='approved')
        self.assertEqual(self.dev_c.post(f'{LEAVES}{approved}/cancel/').status_code, 400)

    def test_nobody_can_cancel_someone_elses_request(self):
        rid = self.apply(self.d(3, 1), self.d(3, 1)).data['id']
        for client in (self.boss_c, self.ceo, self.beta):
            self.assertEqual(client.post(f'{LEAVES}{rid}/cancel/').status_code, 404)
        self.assertEqual(LeaveRequest.objects.get(id=rid).status, 'pending')

    def test_a_cancelled_period_can_be_requested_again(self):
        rid = self.apply(self.d(3, 1), self.d(3, 3)).data['id']
        self.dev_c.post(f'{LEAVES}{rid}/cancel/')
        self.assertEqual(self.apply(self.d(3, 1), self.d(3, 3)).status_code, 201)
