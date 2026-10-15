from django.test import TestCase

from approvals.models import ApprovalChain, ApprovalInstance, ApprovalStep
from attendance.leave_models import LeaveRequest, LeaveType
from attendance.services import local_today
from core.test_utils import add_employee, give_role, login_as, register_company, rows
from notifications.models import Notification
from organization.models import Employee

CHAINS = '/api/v1/approvals/chains/'
STEPS = '/api/v1/approvals/steps/'
INSTANCES = '/api/v1/approvals/instances/'
LEAVES = '/api/v1/attendance/leave-requests/'
INBOX = '/api/v1/notifications/inbox/'


class LeaveApprovalBase(TestCase):
    """Acme: CEO, a developer who applies, a Dept Head and an HR person (each with a role of their own)."""

    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.cid = self.ceo.company_id
        self.dev = add_employee(self.ceo, 'dev@acme.com', 'A-1')
        self.head = add_employee(self.ceo, 'head@acme.com', 'A-2')
        self.hr = add_employee(self.ceo, 'hr@acme.com', 'A-3')
        self.head_role = give_role(self.cid, self.head['id'], [], 'Dept Head')
        self.hr_role = give_role(self.cid, self.hr['id'], [], 'HR')
        self.dev_c, self.head_c, self.hr_c = login_as('dev@acme.com'), login_as('head@acme.com'), login_as('hr@acme.com')
        self.year = local_today(Employee.objects.get(id=self.dev['id']).company)[0].year
        self.annual = LeaveType.objects.create(company_id=self.cid, name='Annual Leave', days_allowed_per_year=5)

    def make_chain(self, roles, name='Leave'):
        chain = self.ceo.post(CHAINS, {'name': name, 'applies_to_module': 'leave'}, format='json').data['id']
        for role in roles:
            res = self.ceo.post(STEPS, {'approval_chain': chain, 'approver_role': str(role.id)}, format='json')
            self.assertEqual(res.status_code, 201, res.content)
        return chain

    def apply(self, client=None, start='03-10', end='03-12', reason='Family trip'):
        return (client or self.dev_c).post(LEAVES, {
            'leave_type': str(self.annual.id), 'start_date': f'{self.year}-{start}',
            'end_date': f'{self.year}-{end}', 'reason': reason,
        }, format='json')

    def instance_of(self, leave_id):
        return ApprovalInstance.objects.get(object_id=leave_id)

    def decide(self, client, leave_id, decision, comment=''):
        inst = self.instance_of(leave_id)
        return client.post(f'{INSTANCES}{inst.id}/{decision}/', {'comment': comment}, format='json')

    def remaining(self, client=None):
        data = (client or self.dev_c).get(LEAVES + 'balance/').data
        return {b['name']: b for b in data}['Annual Leave']['remaining']


class LeaveFollowsTheChainTests(LeaveApprovalBase):
    def test_applying_starts_the_chain_and_the_approver_sees_it_in_pending_and_inbox(self):
        self.make_chain([self.head_role])
        res = self.apply()
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.data['status'], 'pending')
        self.assertEqual(res.data['approval']['chain_name'], 'Leave')
        self.assertEqual(res.data['approval']['current_step'], 1)
        self.assertEqual(res.data['approval']['current_step_role_name'], 'Dept Head')

        pending = rows(self.head_c.get(INSTANCES + '?mine=pending'))
        self.assertEqual(len(pending), 1)
        summary = pending[0]['target_summary']
        self.assertEqual((summary['leave_type'], summary['days'], summary['reason']), ('Annual Leave', 3, 'Family trip'))
        inbox = self.head_c.get(INBOX).data
        items = inbox['data'] if isinstance(inbox, dict) else inbox
        self.assertTrue(any(i['kind'] == 'approval' for i in items), inbox)

        self.assertEqual(rows(self.hr_c.get(INSTANCES + '?mine=pending')), [], 'HR is not on step 1')

    def test_the_last_approval_approves_the_leave_and_tells_the_applicant(self):
        self.make_chain([self.head_role])
        leave_id = self.apply().data['id']
        res = self.decide(self.head_c, leave_id, 'approve')
        self.assertEqual(res.status_code, 200, res.content)
        leave = LeaveRequest.objects.get(id=leave_id)
        self.assertEqual(leave.status, 'approved')
        self.assertTrue(Notification.objects.filter(
            recipient_id=self.dev['id'], kind=Notification.KIND_APPROVAL_DECIDED, title__icontains='approved').exists())
        self.assertEqual(self.remaining(), 2, '3 of 5 days are used')
        mine = rows(self.dev_c.get(LEAVES))[0]
        self.assertEqual(mine['approval']['status'], 'approved')
        self.assertEqual(mine['approval']['actions'][0]['actor_email'], 'head@acme.com')

    def test_two_steps_the_leave_stays_pending_until_the_last_one(self):
        self.make_chain([self.head_role, self.hr_role])
        leave_id = self.apply().data['id']
        self.assertEqual(self.decide(self.hr_c, leave_id, 'approve').status_code, 404, 'HR cannot skip step 1 (not even visible yet)')
        self.assertEqual(self.decide(self.head_c, leave_id, 'approve').status_code, 200)
        self.assertEqual(LeaveRequest.objects.get(id=leave_id).status, 'pending')
        progress = rows(self.dev_c.get(LEAVES))[0]['approval']
        self.assertEqual((progress['current_step'], progress['current_step_role_name']), (2, 'HR'))
        self.assertEqual(self.decide(self.hr_c, leave_id, 'approve').status_code, 200)
        self.assertEqual(LeaveRequest.objects.get(id=leave_id).status, 'approved')

    def test_rejecting_needs_a_comment_gives_the_days_back_and_shows_the_comment(self):
        self.make_chain([self.head_role])
        leave_id = self.apply().data['id']
        self.assertEqual(self.remaining(), 2)
        self.assertEqual(self.decide(self.head_c, leave_id, 'reject', '  ').status_code, 400)
        self.assertEqual(LeaveRequest.objects.get(id=leave_id).status, 'pending')
        self.assertEqual(self.decide(self.head_c, leave_id, 'reject', 'Busy week').status_code, 200)
        self.assertEqual(LeaveRequest.objects.get(id=leave_id).status, 'rejected')
        self.assertEqual(self.remaining(), 5, 'the days are back')
        action = rows(self.dev_c.get(LEAVES))[0]['approval']['actions'][0]
        self.assertEqual((action['decision'], action['comment']), ('rejected', 'Busy week'))
        self.assertTrue(Notification.objects.filter(
            recipient_id=self.dev['id'], title__icontains='rejected').exists())

    def test_a_decided_leave_cannot_be_decided_again(self):
        self.make_chain([self.head_role])
        leave_id = self.apply().data['id']
        self.decide(self.head_c, leave_id, 'approve')
        self.assertEqual(self.decide(self.head_c, leave_id, 'reject', 'Changed my mind').status_code, 400)
        self.assertEqual(LeaveRequest.objects.get(id=leave_id).status, 'approved')


class CeoFallbackTests(LeaveApprovalBase):
    def test_no_chain_goes_to_the_ceo_and_a_default_chain_is_created_once(self):
        self.assertFalse(ApprovalChain.objects.filter(company_id=self.cid).exists())
        first = self.apply(start='03-10', end='03-10')
        second = self.apply(start='04-10', end='04-10')
        self.assertEqual((first.status_code, second.status_code), (201, 201))
        chains = ApprovalChain.objects.filter(company_id=self.cid)
        self.assertEqual(chains.count(), 1)
        self.assertEqual(chains[0].applies_to_module, 'leave')
        self.assertEqual(chains[0].steps.count(), 1)
        self.assertEqual(len(rows(self.ceo.get(INSTANCES + '?mine=pending'))), 2)
        self.assertEqual(self.decide(self.ceo, first.data['id'], 'approve').status_code, 200)
        self.assertEqual(LeaveRequest.objects.get(id=first.data['id']).status, 'approved')

    def test_a_chain_with_no_steps_is_ignored(self):
        self.ceo.post(CHAINS, {'name': 'Empty', 'applies_to_module': 'leave'}, format='json')
        self.assertEqual(self.apply().status_code, 201)
        self.assertEqual(self.instance_of(LeaveRequest.objects.get().id).approval_chain.name, 'Leave Approval (default)')

    def test_a_chain_step_nobody_else_can_decide_falls_back_to_the_ceo(self):
        ghost = give_role(self.cid, self.hr['id'], [], 'Ghost')
        ghost.employee_roles.all().delete()   # the role exists but no one holds it
        self.make_chain([self.head_role, ghost])
        res = self.apply()
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.data['approval']['chain_name'], 'Leave Approval (default)')

    def test_the_applicant_holding_a_step_role_cannot_be_the_only_approver_of_it(self):
        # HR applies; the chain is Dept Head then HR, and HR is the only HR holder -> fall back to the CEO.
        self.make_chain([self.head_role, self.hr_role])
        res = self.apply(client=self.hr_c)
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.data['approval']['chain_name'], 'Leave Approval (default)')

    def test_the_only_ceo_cannot_apply_when_nobody_else_can_approve(self):
        res = self.apply(client=self.ceo)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data['error']['code'], 'LEAVE_NO_APPROVER')
        self.assertEqual(LeaveRequest.objects.count(), 0, 'nothing is saved')
        self.assertEqual(ApprovalInstance.objects.count(), 0)


class LeaveApprovalSafetyTests(LeaveApprovalBase):
    def test_the_applicant_cannot_decide_their_own_leave(self):
        # the applicant holds the step role too, and so does someone else, so the chain is accepted
        extra = add_employee(self.ceo, 'head2@acme.com', 'A-4')
        from rbac.models import EmployeeRole
        EmployeeRole.objects.create(employee_id=extra['id'], role=self.head_role, company_id=self.cid)
        EmployeeRole.objects.create(employee_id=self.dev['id'], role=self.head_role, company_id=self.cid)
        self.make_chain([self.head_role])
        leave_id = self.apply().data['id']
        res = self.decide(self.dev_c, leave_id, 'approve')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(LeaveRequest.objects.get(id=leave_id).status, 'pending')
        self.assertEqual(self.decide(self.head_c, leave_id, 'approve').status_code, 200)

    def test_another_company_cannot_see_or_decide_the_leave(self):
        self.make_chain([self.head_role])
        leave_id = self.apply().data['id']
        beta = register_company('Beta', 'beta', 'ceo@beta.com')
        inst = self.instance_of(leave_id)
        self.assertEqual(beta.post(f'{INSTANCES}{inst.id}/approve/', {}, format='json').status_code, 404)
        self.assertEqual(rows(beta.get(INSTANCES)), [])
        self.assertEqual(LeaveRequest.objects.get(id=leave_id).status, 'pending')

    def test_someone_without_the_step_role_cannot_decide(self):
        self.make_chain([self.head_role])
        leave_id = self.apply().data['id']
        self.assertEqual(self.decide(self.hr_c, leave_id, 'approve').status_code, 404, 'hidden from non-approvers')
        self.assertEqual(self.decide(self.dev_c, leave_id, 'approve').status_code, 400, 'the applicant sees it, but cannot decide')

    def test_cancelling_closes_the_approval_so_nobody_can_decide_it(self):
        self.make_chain([self.head_role])
        leave_id = self.apply().data['id']
        self.assertEqual(self.dev_c.post(f'{LEAVES}{leave_id}/cancel/').status_code, 200)
        self.assertEqual(self.instance_of(leave_id).status, 'cancelled')
        self.assertEqual(rows(self.head_c.get(INSTANCES + '?mine=pending')), [])
        self.assertEqual(self.decide(self.head_c, leave_id, 'approve').status_code, 404, 'no longer visible to the approver')
        self.assertEqual(LeaveRequest.objects.get(id=leave_id).status, 'cancelled')
        self.assertEqual(self.remaining(), 5)

    def test_a_failed_application_leaves_no_approval_behind(self):
        self.make_chain([self.head_role])
        res = self.apply(start='03-10', end='03-20')   # 11 days, balance is 5
        self.assertEqual(res.status_code, 400)
        self.assertEqual(ApprovalInstance.objects.count(), 0)

    def test_the_chain_cannot_be_edited_while_a_leave_waits_on_it(self):
        chain = self.make_chain([self.head_role])
        self.apply()
        step = ApprovalStep.objects.get(approval_chain_id=chain)
        self.assertEqual(self.ceo.delete(f'{STEPS}{step.id}/').status_code, 400)
