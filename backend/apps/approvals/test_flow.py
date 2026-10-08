from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from core.test_utils import add_employee, give_role, login_as, register_company, rows
from organization.models import Employee
from rbac.models import EmployeeRole
from .models import ApprovalAction
from .services import ApprovalError, start_approval

CHAINS = '/api/v1/approvals/chains/'
STEPS = '/api/v1/approvals/steps/'
INSTANCES = '/api/v1/approvals/instances/'


def setup_world(test):
    """Company with a 2-step chain: step 1 = Dept Head role, step 2 = HR role."""
    test.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
    cid = test.ceo.company_id

    def person(email, code, role_name=None):
        e = add_employee(test.ceo, email, code)
        role = None
        if role_name:
            role = give_role(cid, e['id'], [], role_name)
        return e, role

    test.requester, _ = person('req@acme.com', 'R-1')
    test.head, head_role = person('head@acme.com', 'H-1', 'Dept Head')
    test.hr, hr_role = person('hr@acme.com', 'H-2', 'HR')
    test.other, _ = person('other@acme.com', 'O-1')

    chain = test.ceo.post(CHAINS, {'name': 'Leave', 'applies_to_module': 'leave'}, format='json').data['id']
    test.chain_id = chain
    for role in (head_role, hr_role):
        res = test.ceo.post(STEPS, {'approval_chain': chain, 'approver_role': str(role.id)}, format='json')
        assert res.status_code == 201, res.content

    test.req_c, test.head_c = login_as('req@acme.com'), login_as('head@acme.com')
    test.hr_c, test.other_c = login_as('hr@acme.com'), login_as('other@acme.com')


def start(test, requester_id=None):
    from .models import ApprovalChain
    requester = Employee.objects.get(id=requester_id or test.requester['id'])
    chain = ApprovalChain.objects.get(id=test.chain_id)
    return start_approval(requester, chain, requester)


class ApprovalFlowTests(APITestCase):

    def setUp(self):
        setup_world(self)

    def test_cannot_start_on_empty_chain(self):
        empty = self.ceo.post(CHAINS, {'name': 'Empty', 'applies_to_module': 'leave'}, format='json').data['id']
        from .models import ApprovalChain
        req = Employee.objects.get(id=self.requester['id'])
        with self.assertRaises(ApprovalError):
            start_approval(req, ApprovalChain.objects.get(id=empty), req)

    def test_full_two_step_approval(self):
        inst = start(self)
        url = f'{INSTANCES}{inst.id}/'
        res = self.head_c.post(url + 'approve/', {'comment': 'ok from head'}, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual((res.data['status'], res.data['current_step']), ('pending', 2))
        self.assertEqual(res.data['current_step_role_name'], 'HR')

        res = self.hr_c.post(url + 'approve/', {}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['status'], 'approved')
        self.assertEqual([a['step_order'] for a in res.data['actions']], [1, 2])
        self.assertEqual(res.data['actions'][0]['comment'], 'ok from head')

    def test_reject_ends_request_and_keeps_comment(self):
        inst = start(self)
        url = f'{INSTANCES}{inst.id}/'
        res = self.head_c.post(url + 'reject/', {'comment': 'Not enough cover'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['status'], 'rejected')
        self.assertEqual(res.data['actions'][0]['comment'], 'Not enough cover')
        # nothing more can happen: the one who decided still sees it, but it is closed
        self.assertEqual(self.head_c.post(url + 'approve/', {}, format='json').status_code, 400)
        self.assertEqual(ApprovalAction.objects.count(), 1)

    def test_reject_needs_a_comment(self):
        inst = start(self)
        res = self.head_c.post(f'{INSTANCES}{inst.id}/reject/', {'comment': '  '}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(ApprovalAction.objects.count(), 0)

    def test_wrong_role_is_blocked(self):
        inst = start(self)
        url = f'{INSTANCES}{inst.id}/'
        # HR (step-2 role) and an unrelated employee cannot even see a request that is at step 1
        self.assertEqual(self.hr_c.post(url + 'approve/', {}, format='json').status_code, 404)
        self.assertEqual(self.other_c.post(url + 'approve/', {}, format='json').status_code, 404)
        self.assertEqual(ApprovalAction.objects.count(), 0)
        # the step-1 holder decides, then tries again at step 2 without the step-2 role
        self.assertEqual(self.head_c.post(url + 'approve/', {}, format='json').status_code, 200)
        self.assertEqual(self.head_c.post(url + 'approve/', {}, format='json').status_code, 403)
        self.assertEqual(ApprovalAction.objects.count(), 1)

    def test_acting_twice_on_same_request_is_blocked(self):
        # single-step chain so the first approval finishes the request
        from .models import ApprovalChain, ApprovalStep
        chain = ApprovalChain.objects.get(id=self.chain_id)
        ApprovalStep.objects.filter(approval_chain=chain, step_order=2).delete()
        inst = start(self)
        url = f'{INSTANCES}{inst.id}/'
        self.assertEqual(self.head_c.post(url + 'approve/', {}, format='json').status_code, 200)
        self.assertEqual(self.head_c.post(url + 'approve/', {}, format='json').status_code, 400)
        self.assertEqual(ApprovalAction.objects.count(), 1)

    def test_database_blocks_two_decisions_on_one_step(self):
        inst = start(self)
        head = Employee.objects.get(id=self.head['id'])
        ApprovalAction.objects.create(instance=inst, step_order=1, actor=head, decision='approved')
        with self.assertRaises(IntegrityError), transaction.atomic():
            ApprovalAction.objects.create(instance=inst, step_order=1, actor=head, decision='approved')

    def test_requester_cannot_decide_own_request_even_with_role(self):
        # requester also gets the step-1 role
        role = give_role(self.ceo.company_id, self.requester['id'], [], 'Also Head')
        from .models import ApprovalChain, ApprovalStep
        step = ApprovalStep.objects.get(approval_chain_id=self.chain_id, step_order=1)
        step.approver_role = role
        step.save()
        inst = start(self)
        res = self.req_c.post(f'{INSTANCES}{inst.id}/approve/', {}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_visibility_and_mine_filter(self):
        inst = start(self)
        ids = lambda c, q='': [i['id'] for i in rows(c.get(INSTANCES + q))]
        self.assertIn(str(inst.id), ids(self.req_c))          # requester sees own
        self.assertIn(str(inst.id), ids(self.head_c))         # current approver sees it
        self.assertNotIn(str(inst.id), ids(self.hr_c))        # step-2 holder: not yet
        self.assertNotIn(str(inst.id), ids(self.other_c))     # unrelated: never
        self.assertIn(str(inst.id), ids(self.ceo))            # manage_approval_chains sees all

        self.assertEqual(ids(self.head_c, '?mine=pending'), [str(inst.id)])
        self.assertEqual(ids(self.req_c, '?mine=pending'), [])  # own request: cannot act

        self.head_c.post(f'{INSTANCES}{inst.id}/approve/', {}, format='json')
        self.assertEqual(ids(self.head_c, '?mine=pending'), [])
        self.assertIn(str(inst.id), ids(self.head_c))          # still sees what he decided
        self.assertEqual(ids(self.hr_c, '?mine=pending'), [str(inst.id)])

    def test_can_act_flag(self):
        inst = start(self)
        self.assertTrue(self.head_c.get(f'{INSTANCES}{inst.id}/').data['can_act'])
        self.assertFalse(self.ceo.get(f'{INSTANCES}{inst.id}/').data['can_act'])

    def test_other_company_cannot_touch_it(self):
        inst = start(self)
        beta = register_company('Beta', 'beta', 'ceo@beta.com')
        self.assertEqual(beta.get(f'{INSTANCES}{inst.id}/').status_code, 404)
        self.assertEqual(beta.post(f'{INSTANCES}{inst.id}/approve/', {}, format='json').status_code, 404)
        self.assertEqual(rows(beta.get(INSTANCES)), [])

    def test_instances_cannot_be_created_through_the_api(self):
        res = self.ceo.post(INSTANCES, {}, format='json')
        self.assertEqual(res.status_code, 405)

    # --- chain protection --------------------------------------------------
    def test_pending_chain_steps_are_locked(self):
        start(self)
        step_id = self.ceo.get(f'{CHAINS}{self.chain_id}/').data['steps'][0]['id']
        role = self.ceo.get(f'{CHAINS}{self.chain_id}/').data['steps'][0]['approver_role']
        self.assertEqual(self.ceo.delete(f'{STEPS}{step_id}/').status_code, 400)
        self.assertEqual(self.ceo.post(STEPS, {'approval_chain': self.chain_id, 'approver_role': role}, format='json').status_code, 400)
        self.assertEqual(self.ceo.post(f'{CHAINS}{self.chain_id}/reorder/', {'step_ids': []}, format='json').status_code, 400)

    def test_chain_with_history_cannot_be_deleted(self):
        inst = start(self)
        self.head_c.post(f'{INSTANCES}{inst.id}/reject/', {'comment': 'no'}, format='json')  # finished
        self.assertEqual(self.ceo.delete(f'{CHAINS}{self.chain_id}/').status_code, 400)
        # finished request: steps are editable again
        step_id = self.ceo.get(f'{CHAINS}{self.chain_id}/').data['steps'][1]['id']
        self.assertEqual(self.ceo.delete(f'{STEPS}{step_id}/').status_code, 204)
