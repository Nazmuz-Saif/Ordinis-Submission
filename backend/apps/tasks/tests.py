from rest_framework.test import APITestCase

from core.test_utils import add_employee, give_role, login_as, register_company, rows

TASKS = '/api/v1/tasks/tasks/'


def make_task(client, assignee_id, **extra):
    data = {'title': 'Write report', 'assigned_to': assignee_id, 'priority': 'high', 'deadline': '2026-12-31', **extra}
    return client.post(TASKS, data, format='json')


class TaskTests(APITestCase):

    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        cid = self.ceo.company_id
        self.alice = add_employee(self.ceo, 'alice@acme.com', 'E-1')
        self.bob = add_employee(self.ceo, 'bob@acme.com', 'E-2')
        manager = add_employee(self.ceo, 'mgr@acme.com', 'E-3')
        give_role(cid, manager['id'], ['create_task'], 'Task Manager')
        self.alice_c, self.bob_c = login_as('alice@acme.com'), login_as('bob@acme.com')
        self.mgr_c = login_as('mgr@acme.com')

    # --- create ---------------------------------------------------------
    def test_create_with_permission(self):
        res = make_task(self.mgr_c, self.alice['id'])
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.data['status'], 'not_started')
        self.assertEqual(res.data['priority'], 'high')
        self.assertEqual(res.data['deadline'], '2026-12-31')
        self.assertEqual(res.data['assigned_by_email'], 'mgr@acme.com')  # set by the server
        self.assertIn(res.data['id'], [t['id'] for t in rows(self.mgr_c.get(TASKS))])

    def test_create_without_permission_is_403(self):
        self.assertEqual(make_task(self.alice_c, self.bob['id']).status_code, 403)

    def test_assigned_by_cannot_be_forged(self):
        res = make_task(self.mgr_c, self.alice['id'], assigned_by=self.bob['id'])
        self.assertEqual(res.data['assigned_by_email'], 'mgr@acme.com')

    def test_new_task_cannot_start_as_completed(self):
        self.assertEqual(make_task(self.mgr_c, self.alice['id'], status='completed').status_code, 400)

    def test_blank_title_rejected(self):
        self.assertEqual(make_task(self.mgr_c, self.alice['id'], title='   ').status_code, 400)

    def test_default_priority_is_medium(self):
        res = self.mgr_c.post(TASKS, {'title': 'x', 'assigned_to': self.alice['id']}, format='json')
        self.assertEqual(res.data['priority'], 'medium')

    # --- tenant isolation -----------------------------------------------
    def test_cannot_assign_to_employee_of_another_company(self):
        beta = register_company('Beta', 'beta', 'ceo@beta.com')
        foreign = add_employee(beta, 'x@beta.com', 'B-1')
        self.assertEqual(make_task(self.mgr_c, foreign['id']).status_code, 400)

    def test_other_company_task_is_404(self):
        task = make_task(self.mgr_c, self.alice['id']).data['id']
        beta = register_company('Beta', 'beta', 'ceo@beta.com')
        self.assertEqual(beta.get(f'{TASKS}{task}/').status_code, 404)
        self.assertEqual(beta.delete(f'{TASKS}{task}/').status_code, 404)
        self.assertEqual(rows(beta.get(TASKS)), [])

    # --- edit / delete ---------------------------------------------------
    def test_edit_and_delete_need_permission(self):
        task = make_task(self.mgr_c, self.alice['id']).data['id']
        self.assertEqual(self.alice_c.patch(f'{TASKS}{task}/', {'title': 'hack'}, format='json').status_code, 403)
        self.assertEqual(self.alice_c.delete(f'{TASKS}{task}/').status_code, 403)
        self.assertEqual(self.mgr_c.patch(f'{TASKS}{task}/', {'title': 'Renamed', 'priority': 'low'}, format='json').status_code, 200)
        self.assertEqual(self.mgr_c.get(f'{TASKS}{task}/').data['title'], 'Renamed')
        self.assertEqual(self.mgr_c.delete(f'{TASKS}{task}/').status_code, 204)
        self.assertEqual(self.mgr_c.get(f'{TASKS}{task}/').status_code, 404)

    def test_reassign_to_other_company_blocked_on_edit(self):
        task = make_task(self.mgr_c, self.alice['id']).data['id']
        beta = register_company('Beta', 'beta', 'ceo@beta.com')
        foreign = add_employee(beta, 'x@beta.com', 'B-1')
        res = self.mgr_c.patch(f'{TASKS}{task}/', {'assigned_to': foreign['id']}, format='json')
        self.assertEqual(res.status_code, 400)

    # --- who sees what ---------------------------------------------------
    def test_visibility(self):
        t1 = make_task(self.mgr_c, self.alice['id']).data['id']
        ids = lambda c: [t['id'] for t in rows(c.get(TASKS))]
        self.assertIn(t1, ids(self.alice_c))      # the assignee
        self.assertIn(t1, ids(self.mgr_c))        # the creator / create_task holder
        self.assertIn(t1, ids(self.ceo))          # CEO holds create_task
        self.assertNotIn(t1, ids(self.bob_c))     # unrelated employee
        self.assertEqual(self.bob_c.get(f'{TASKS}{t1}/').status_code, 404)

    # --- status: start / submit -----------------------------------------
    def test_start_then_submit_by_assignee(self):
        task = make_task(self.mgr_c, self.alice['id']).data['id']
        res = self.alice_c.post(f'{TASKS}{task}/start/')
        self.assertEqual((res.status_code, res.data['status']), (200, 'in_progress'))
        res = self.alice_c.post(f'{TASKS}{task}/submit/')
        self.assertEqual((res.status_code, res.data['status']), (200, 'submitted'))

    def test_cannot_submit_before_starting(self):
        task = make_task(self.mgr_c, self.alice['id']).data['id']
        res = self.alice_c.post(f'{TASKS}{task}/submit/')
        self.assertEqual(res.status_code, 400)
        self.assertIn('Not Started to Submitted', str(res.content))

    def test_non_assignee_cannot_submit(self):
        task = make_task(self.mgr_c, self.alice['id']).data['id']
        self.alice_c.post(f'{TASKS}{task}/start/')
        self.assertEqual(self.bob_c.post(f'{TASKS}{task}/submit/').status_code, 404)  # cannot even see it
        self.assertEqual(self.mgr_c.post(f'{TASKS}{task}/submit/').status_code, 403)   # sees it, still not the assignee
        self.assertEqual(self.mgr_c.get(f'{TASKS}{task}/').data['status'], 'in_progress')

    def test_submit_twice_is_blocked(self):
        task = make_task(self.mgr_c, self.alice['id']).data['id']
        self.alice_c.post(f'{TASKS}{task}/start/')
        self.alice_c.post(f'{TASKS}{task}/submit/')
        self.assertEqual(self.alice_c.post(f'{TASKS}{task}/submit/').status_code, 400)

    # --- status: manual changes through edit -----------------------------
    def test_review_flow_through_edit(self):
        task = make_task(self.mgr_c, self.alice['id']).data['id']
        self.alice_c.post(f'{TASKS}{task}/start/')
        self.alice_c.post(f'{TASKS}{task}/submit/')
        res = self.mgr_c.patch(f'{TASKS}{task}/', {'status': 'completed'}, format='json')
        self.assertEqual((res.status_code, res.data['status']), (200, 'completed'))

    def test_rejected_task_can_be_restarted(self):
        task = make_task(self.mgr_c, self.alice['id']).data['id']
        self.alice_c.post(f'{TASKS}{task}/start/')
        self.alice_c.post(f'{TASKS}{task}/submit/')
        self.mgr_c.patch(f'{TASKS}{task}/', {'status': 'rejected'}, format='json')
        res = self.alice_c.post(f'{TASKS}{task}/start/')
        self.assertEqual(res.data['status'], 'in_progress')

    def test_completed_cannot_go_back_to_not_started(self):
        task = make_task(self.mgr_c, self.alice['id']).data['id']
        self.alice_c.post(f'{TASKS}{task}/start/')
        self.alice_c.post(f'{TASKS}{task}/submit/')
        self.mgr_c.patch(f'{TASKS}{task}/', {'status': 'completed'}, format='json')
        res = self.mgr_c.patch(f'{TASKS}{task}/', {'status': 'not_started'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('Completed to Not Started', str(res.content))
        self.assertEqual(self.mgr_c.get(f'{TASKS}{task}/').data['status'], 'completed')

    def test_cannot_skip_steps_through_edit(self):
        task = make_task(self.mgr_c, self.alice['id']).data['id']
        res = self.mgr_c.patch(f'{TASKS}{task}/', {'status': 'completed'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_saving_same_status_is_fine(self):
        task = make_task(self.mgr_c, self.alice['id']).data['id']
        res = self.mgr_c.patch(f'{TASKS}{task}/', {'status': 'not_started', 'title': 'New'}, format='json')
        self.assertEqual(res.status_code, 200)
