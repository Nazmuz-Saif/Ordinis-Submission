from rest_framework.test import APITestCase

from core.test_utils import add_employee, give_role, login_as, register_company

CHAINS = '/api/v1/approvals/chains/'
STEPS = '/api/v1/approvals/steps/'


def make_role(ceo, name):
    res = ceo.post('/api/v1/rbac/roles/', {'name': name}, format='json')
    assert res.status_code == 201, res.content
    return res.data['id']


def make_chain(ceo, name='Leave Approval'):
    res = ceo.post(CHAINS, {'name': name, 'applies_to_module': 'leave'}, format='json')
    assert res.status_code == 201, res.content
    return res.data['id']


def make_step(ceo, chain_id, role_id, **extra):
    return ceo.post(STEPS, {'approval_chain': chain_id, 'approver_role': role_id, **extra}, format='json')


class ApprovalChainTests(APITestCase):

    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.hr = make_role(self.ceo, 'HR')
        self.head = make_role(self.ceo, 'Dept Head')

    # --- permission -------------------------------------------------
    def test_employee_without_permission_cannot_write_but_can_read(self):
        add_employee(self.ceo, 'emp@acme.com', 'E-1')
        emp = login_as('emp@acme.com')
        self.assertEqual(emp.post(CHAINS, {'name': 'X', 'applies_to_module': 'leave'}, format='json').status_code, 403)
        make_chain(self.ceo)
        self.assertEqual(emp.get(CHAINS).status_code, 200)

    def test_employee_with_permission_can_create(self):
        e = add_employee(self.ceo, 'mgr@acme.com', 'E-2')
        give_role(self.ceo.company_id, e['id'], ['manage_approval_chains'], 'Chain Manager')
        mgr = login_as('mgr@acme.com')
        res = mgr.post(CHAINS, {'name': 'Leave', 'applies_to_module': 'leave'}, format='json')
        self.assertEqual(res.status_code, 201)

    # --- chain ------------------------------------------------------
    def test_invalid_module_rejected(self):
        res = self.ceo.post(CHAINS, {'name': 'X', 'applies_to_module': 'nonsense'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_chain_name_unique_per_company(self):
        make_chain(self.ceo, 'Leave')
        self.assertEqual(self.ceo.post(CHAINS, {'name': 'Leave', 'applies_to_module': 'leave'}, format='json').status_code, 400)
        other = register_company('Beta', 'beta', 'ceo@beta.com')
        self.assertEqual(other.post(CHAINS, {'name': 'Leave', 'applies_to_module': 'leave'}, format='json').status_code, 201)

    def test_other_company_chain_is_404(self):
        chain = make_chain(self.ceo)
        other = register_company('Beta', 'beta', 'ceo@beta.com')
        self.assertEqual(other.get(f'{CHAINS}{chain}/').status_code, 404)
        self.assertEqual(other.delete(f'{CHAINS}{chain}/').status_code, 404)
        self.assertEqual(len(other.get(CHAINS).data), 0)

    # --- steps ------------------------------------------------------
    def test_step_order_is_filled_automatically(self):
        chain = make_chain(self.ceo)
        a = make_step(self.ceo, chain, self.head)
        b = make_step(self.ceo, chain, self.hr)
        self.assertEqual((a.data['step_order'], b.data['step_order']), (1, 2))
        detail = self.ceo.get(f'{CHAINS}{chain}/').data
        self.assertEqual([s['approver_role_name'] for s in detail['steps']], ['Dept Head', 'HR'])

    def test_duplicate_step_order_rejected(self):
        chain = make_chain(self.ceo)
        make_step(self.ceo, chain, self.head, step_order=1)
        self.assertEqual(make_step(self.ceo, chain, self.hr, step_order=1).status_code, 400)

    def test_step_order_zero_rejected(self):
        chain = make_chain(self.ceo)
        self.assertEqual(make_step(self.ceo, chain, self.head, step_order=0).status_code, 400)

    def test_other_company_role_cannot_be_approver(self):
        other = register_company('Beta', 'beta', 'ceo@beta.com')
        foreign_role = make_role(other, 'Foreign')
        chain = make_chain(self.ceo)
        self.assertEqual(make_step(self.ceo, chain, foreign_role).status_code, 400)

    def test_cannot_add_step_to_other_company_chain(self):
        other = register_company('Beta', 'beta', 'ceo@beta.com')
        foreign_chain = make_chain(other, 'Beta Leave')
        self.assertEqual(make_step(self.ceo, foreign_chain, self.hr).status_code, 400)

    def test_step_cannot_move_to_another_chain(self):
        c1, c2 = make_chain(self.ceo, 'One'), make_chain(self.ceo, 'Two')
        step = make_step(self.ceo, c1, self.hr).data['id']
        res = self.ceo.patch(f'{STEPS}{step}/', {'approval_chain': c2}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_deleting_middle_step_compacts_orders(self):
        chain = make_chain(self.ceo)
        ids = [make_step(self.ceo, chain, r).data['id'] for r in (self.head, self.hr, self.head)]
        self.assertEqual(self.ceo.delete(f'{STEPS}{ids[1]}/').status_code, 204)
        steps = self.ceo.get(f'{CHAINS}{chain}/').data['steps']
        self.assertEqual([s['step_order'] for s in steps], [1, 2])
        self.assertEqual([s['id'] for s in steps], [ids[0], ids[2]])

    # --- reorder ----------------------------------------------------
    def test_reorder(self):
        chain = make_chain(self.ceo)
        ids = [make_step(self.ceo, chain, r).data['id'] for r in (self.head, self.hr)]
        res = self.ceo.post(f'{CHAINS}{chain}/reorder/', {'step_ids': [ids[1], ids[0]]}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual([s['id'] for s in res.data['steps']], [ids[1], ids[0]])
        self.assertEqual([s['step_order'] for s in res.data['steps']], [1, 2])

    def test_reorder_with_wrong_ids_rejected(self):
        chain = make_chain(self.ceo)
        ids = [make_step(self.ceo, chain, r).data['id'] for r in (self.head, self.hr)]
        self.assertEqual(self.ceo.post(f'{CHAINS}{chain}/reorder/', {'step_ids': [ids[0]]}, format='json').status_code, 400)
        self.assertEqual(self.ceo.post(f'{CHAINS}{chain}/reorder/', {'step_ids': [ids[0], ids[0]]}, format='json').status_code, 400)
        self.assertEqual(self.ceo.post(f'{CHAINS}{chain}/reorder/', {}, format='json').status_code, 400)

    def test_reorder_needs_permission(self):
        chain = make_chain(self.ceo)
        add_employee(self.ceo, 'emp@acme.com', 'E-1')
        emp = login_as('emp@acme.com')
        self.assertEqual(emp.post(f'{CHAINS}{chain}/reorder/', {'step_ids': []}, format='json').status_code, 403)

    # --- role in use ------------------------------------------------
    def test_role_used_by_a_step_cannot_be_deleted(self):
        chain = make_chain(self.ceo)
        make_step(self.ceo, chain, self.hr)
        self.assertEqual(self.ceo.delete(f'/api/v1/rbac/roles/{self.hr}/').status_code, 400)
        self.assertEqual(self.ceo.delete(f'/api/v1/rbac/roles/{self.head}/').status_code, 204)

    def test_deleting_chain_removes_its_steps(self):
        chain = make_chain(self.ceo)
        make_step(self.ceo, chain, self.hr)
        self.assertEqual(self.ceo.delete(f'{CHAINS}{chain}/').status_code, 204)
        self.assertEqual(len(self.ceo.get(STEPS).data), 0)
