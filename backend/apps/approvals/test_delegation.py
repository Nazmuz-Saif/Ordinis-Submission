from datetime import date, timedelta

from rest_framework.test import APITestCase

from core.test_utils import add_employee, give_role, login_as, register_company
from .models import DelegationRule
from .test_flow import CHAINS, INSTANCES, STEPS, setup_world, start

DELEGATIONS = '/api/v1/approvals/delegations/'


def day(offset):
    return (date.today() + timedelta(days=offset)).isoformat()


def delegate(client, delegate_id, start=0, end=3, **extra):
    return client.post(DELEGATIONS, {'delegate': delegate_id, 'start_date': day(start), 'end_date': day(end), **extra}, format='json')


class DelegationRuleTests(APITestCase):

    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.head = add_employee(self.ceo, 'head@acme.com', 'H-1')
        self.peer = add_employee(self.ceo, 'peer@acme.com', 'P-1')
        self.head_c, self.peer_c = login_as('head@acme.com'), login_as('peer@acme.com')

    def test_create_and_list(self):
        res = delegate(self.head_c, self.peer['id'], reason='On leave')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.data['delegator_email'], 'head@acme.com')  # set by the server
        self.assertEqual(res.data['delegate_email'], 'peer@acme.com')
        self.assertTrue(res.data['is_active'])
        self.assertEqual([d['id'] for d in self.head_c.get(DELEGATIONS).data], [res.data['id']])
        # the delegate sees it too
        self.assertEqual([d['id'] for d in self.peer_c.get(DELEGATIONS).data], [res.data['id']])

    def test_end_before_start_rejected(self):
        res = delegate(self.head_c, self.peer['id'], start=5, end=2)
        self.assertEqual(res.status_code, 400)
        self.assertIn('end date', str(res.content).lower())

    def test_same_day_is_valid(self):
        self.assertEqual(delegate(self.head_c, self.peer['id'], start=2, end=2).status_code, 201)

    def test_delegate_to_self_rejected(self):
        res = delegate(self.head_c, self.head['id'])
        self.assertEqual(res.status_code, 400)
        self.assertIn('yourself', str(res.content))

    def test_end_date_in_the_past_rejected(self):
        self.assertEqual(delegate(self.head_c, self.peer['id'], start=-5, end=-1).status_code, 400)

    def test_delegate_must_be_same_company(self):
        beta = register_company('Beta', 'beta', 'ceo@beta.com')
        foreign = add_employee(beta, 'x@beta.com', 'B-1')
        self.assertEqual(delegate(self.head_c, foreign['id']).status_code, 400)

    def test_delegator_cannot_be_forged(self):
        res = delegate(self.head_c, self.peer['id'], delegator=self.peer['id'])
        self.assertEqual(res.data['delegator_email'], 'head@acme.com')

    def test_only_delegator_can_delete(self):
        rule = delegate(self.head_c, self.peer['id']).data['id']
        self.assertEqual(self.peer_c.delete(f'{DELEGATIONS}{rule}/').status_code, 403)  # can see it, did not create it
        self.assertEqual(self.head_c.delete(f'{DELEGATIONS}{rule}/').status_code, 204)
        self.assertEqual(DelegationRule.objects.count(), 0)

    def test_uninvolved_employee_and_other_company_see_nothing(self):
        rule = delegate(self.head_c, self.peer['id']).data['id']
        add_employee(self.ceo, 'other@acme.com', 'O-1')
        other_c = login_as('other@acme.com')
        self.assertEqual(other_c.get(DELEGATIONS).data, [])
        self.assertEqual(other_c.delete(f'{DELEGATIONS}{rule}/').status_code, 404)
        beta = register_company('Beta', 'beta', 'ceo@beta.com')
        self.assertEqual(beta.get(f'{DELEGATIONS}{rule}/').status_code, 404)

    def test_no_edit_endpoint(self):
        rule = delegate(self.head_c, self.peer['id']).data['id']
        self.assertEqual(self.head_c.patch(f'{DELEGATIONS}{rule}/', {'reason': 'x'}, format='json').status_code, 405)


class DelegationEffectTests(APITestCase):
    """The reason delegation exists: the delegate can decide what waits for the delegator's role."""

    def setUp(self):
        from .test_flow import setup_world
        setup_world(self)   # head = step-1 role, hr = step-2 role, other = no role
        self.inst = start(self)
        self.url = f'{INSTANCES}{self.inst.id}/'

    def give(self, start=0, end=3, who=None):
        return delegate(self.head_c, (who or self.other)['id'], start=start, end=end)

    def test_delegate_can_decide_while_active(self):
        self.give()
        self.assertTrue(self.other_c.get(self.url).data['can_act'])
        self.assertEqual([i['id'] for i in self.other_c.get(INSTANCES + '?mine=pending').data], [str(self.inst.id)])
        res = self.other_c.post(self.url + 'approve/', {'comment': 'covering'}, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual((res.data['status'], res.data['current_step']), ('pending', 2))
        self.assertEqual(res.data['actions'][0]['actor_email'], 'other@acme.com')

    def test_without_delegation_the_same_person_is_blocked(self):
        self.assertEqual(self.other_c.post(self.url + 'approve/', {}, format='json').status_code, 404)

    def test_expired_delegation_gives_nothing(self):
        # created in the past through the database (the API refuses to create past rules)
        DelegationRule.objects.create(
            company_id=self.ceo.company_id, delegator_id=self.head['id'], delegate_id=self.other['id'],
            start_date=date.today() - timedelta(days=9), end_date=date.today() - timedelta(days=2),
        )
        self.assertEqual(self.other_c.post(self.url + 'approve/', {}, format='json').status_code, 404)

    def test_future_delegation_gives_nothing_yet(self):
        self.give(start=2, end=5)
        self.assertEqual(self.other_c.post(self.url + 'approve/', {}, format='json').status_code, 404)

    def test_deleting_the_delegation_takes_the_power_back(self):
        rule = self.give().data['id']
        self.head_c.delete(f'{DELEGATIONS}{rule}/')
        self.assertEqual(self.other_c.post(self.url + 'approve/', {}, format='json').status_code, 404)

    def test_delegate_only_gets_the_delegators_roles(self):
        self.give()   # delegator holds the step-1 role only
        self.other_c.post(self.url + 'approve/', {}, format='json')   # step 1: ok
        res = self.other_c.post(self.url + 'approve/', {}, format='json')   # step 2 needs the HR role
        self.assertEqual(res.status_code, 403)

    def test_original_holder_can_still_decide(self):
        self.give()
        self.assertEqual(self.head_c.post(self.url + 'approve/', {}, format='json').status_code, 200)

    def test_delegate_cannot_decide_own_request(self):
        # the requester receives the head's authority, but it is the requester's own request
        self.give(who=self.requester)
        self.assertEqual(self.req_c.post(self.url + 'approve/', {}, format='json').status_code, 400)
