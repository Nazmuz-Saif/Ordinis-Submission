from datetime import timedelta

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from attendance.services import local_today
from core.test_utils import add_employee, give_role, login_as, register_company, rows
from organization.models import Employee
from tasks.models import Task, TaskProgressLog

TASKS = '/api/v1/tasks/tasks/'
BOARD = TASKS + 'board/'


def mk(company_id, assignee_id, title='T', status='not_started', priority='medium', deadline=None, by=None):
    return Task.objects.create(
        company_id=company_id, title=title, assigned_to_id=assignee_id, assigned_by_id=by,
        status=status, priority=priority, deadline=deadline,
    )


class BoardBase(TestCase):
    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.cid = self.ceo.company_id
        self.dev = add_employee(self.ceo, 'dev@acme.com', 'A-1')
        self.dev_c = login_as('dev@acme.com')
        self.other = add_employee(self.ceo, 'other@acme.com', 'A-2')
        self.other_c = login_as('other@acme.com')
        self.mgr = add_employee(self.ceo, 'mgr@acme.com', 'A-3')
        give_role(self.cid, self.mgr['id'], ['create_task'])
        self.mgr_c = login_as('mgr@acme.com')
        self.beta = register_company('Beta', 'beta', 'ceo@beta.com')
        self.today, _ = local_today(Employee.objects.get(id=self.dev['id']).company)

    def column(self, client, key):
        return {c['key']: c for c in client.get(BOARD).data['columns']}[key]

    def card(self, client, task):
        for col in client.get(BOARD).data['columns']:
            for card in col['cards']:
                if str(card['id']) == str(task.id):
                    return col['key'], card
        return None, None

    def move(self, client, task, column):
        return client.post(f'{TASKS}{task.id}/move/', {'column': column}, format='json')


class BoardTests(BoardBase):
    def test_four_columns_in_order_with_counts(self):
        mk(self.cid, self.dev['id'], status='not_started')
        mk(self.cid, self.dev['id'], status='rejected')
        mk(self.cid, self.dev['id'], status='in_progress')
        mk(self.cid, self.dev['id'], status='submitted')
        mk(self.cid, self.dev['id'], status='completed')
        mk(self.cid, self.dev['id'], status='completed')
        cols = self.mgr_c.get(BOARD).data['columns']
        self.assertEqual([(c['key'], c['label'], c['count']) for c in cols],
                         [('todo', 'To Do', 2), ('in_progress', 'In Progress', 1), ('review', 'Review', 1), ('done', 'Done', 2)])

    def test_card_has_title_priority_assignee_deadline(self):
        t = mk(self.cid, self.dev['id'], title='Build login', priority='high', deadline=self.today + timedelta(days=3))
        key, card = self.card(self.mgr_c, t)
        self.assertEqual(key, 'todo')
        self.assertEqual((card['title'], card['priority'], card['assigned_to_email']), ('Build login', 'high', 'dev@acme.com'))
        self.assertEqual(str(card['deadline']), str(self.today + timedelta(days=3)))
        self.assertFalse(card['overdue'])

    def test_rejected_task_sits_in_to_do_with_a_rejected_flag(self):
        t = mk(self.cid, self.dev['id'], status='rejected')
        key, card = self.card(self.mgr_c, t)
        self.assertEqual(key, 'todo')
        self.assertTrue(card['rejected'])

    def test_overdue_flag_ignores_completed_tasks(self):
        late = mk(self.cid, self.dev['id'], deadline=self.today - timedelta(days=1))
        done = mk(self.cid, self.dev['id'], status='completed', deadline=self.today - timedelta(days=1))
        self.assertTrue(self.card(self.mgr_c, late)[1]['overdue'])
        self.assertFalse(self.card(self.mgr_c, done)[1]['overdue'])

    def test_cards_are_ordered_high_priority_first_then_earliest_deadline(self):
        low = mk(self.cid, self.dev['id'], title='low', priority='low')
        soon = mk(self.cid, self.dev['id'], title='med-soon', deadline=self.today + timedelta(days=1))
        later = mk(self.cid, self.dev['id'], title='med-later', deadline=self.today + timedelta(days=9))
        nodate = mk(self.cid, self.dev['id'], title='med-none')
        high = mk(self.cid, self.dev['id'], title='high', priority='high')
        titles = [c['title'] for c in self.column(self.mgr_c, 'todo')['cards']]
        self.assertEqual(titles, ['high', 'med-soon', 'med-later', 'med-none', 'low'])

    def test_a_manager_sees_the_whole_company_an_employee_only_their_own(self):
        mine = mk(self.cid, self.dev['id'], title='mine')
        mk(self.cid, self.other['id'], title='theirs')
        self.assertEqual(self.column(self.mgr_c, 'todo')['count'], 2)
        todo = self.column(self.dev_c, 'todo')
        self.assertEqual((todo['count'], [c['title'] for c in todo['cards']]), (1, ['mine']))
        self.assertEqual(self.column(self.other_c, 'todo')['count'], 1)

    def test_another_companys_tasks_never_appear(self):
        mk(self.beta.company_id, self.beta.employee_id, title='beta secret')
        body = self.ceo.get(BOARD).content.decode() + self.mgr_c.get(BOARD).content.decode()
        self.assertNotIn('beta secret', body)
        self.assertEqual(self.column(self.beta, 'todo')['count'], 1)

    def test_progress_and_blocker_from_the_latest_entry(self):
        t = mk(self.cid, self.dev['id'], status='in_progress')
        self.assertEqual(self.card(self.mgr_c, t)[1]['progress_percent'], 0)
        TaskProgressLog.objects.create(task=t, employee_id=self.dev['id'], date=self.today - timedelta(days=1),
                                       update_text='a', progress_percent=30, blocker_text='waiting')
        TaskProgressLog.objects.create(task=t, employee_id=self.dev['id'], date=self.today,
                                       update_text='b', progress_percent=60)
        card = self.card(self.mgr_c, t)[1]
        self.assertEqual(card['progress_percent'], 60)
        self.assertFalse(card['blocked'])

    def test_a_column_caps_its_cards_but_still_counts_everything(self):
        Task.objects.bulk_create([Task(company_id=self.cid, title=f'T{i}', assigned_to_id=self.dev['id']) for i in range(55)])
        col = self.column(self.mgr_c, 'todo')
        self.assertEqual((col['count'], len(col['cards']), col['has_more']), (55, 50, True))

    def test_the_board_needs_login(self):
        self.assertIn(APIClient().get(BOARD).status_code, (401, 403))

    def test_query_count_does_not_grow_with_the_number_of_tasks(self):
        def queries():
            with CaptureQueriesContext(connection) as ctx:
                self.mgr_c.get(BOARD)
            return len(ctx)
        mk(self.cid, self.dev['id'])
        few = queries()
        for i in range(25):
            mk(self.cid, self.dev['id'], status=['not_started', 'in_progress', 'submitted', 'completed'][i % 4])
        self.assertEqual(queries(), few)

    def test_allowed_moves_depend_on_who_is_asking(self):
        todo = mk(self.cid, self.dev['id'], status='not_started')
        prog = mk(self.cid, self.dev['id'], status='in_progress')
        review = mk(self.cid, self.dev['id'], status='submitted')
        done = mk(self.cid, self.dev['id'], status='completed')
        self.assertEqual(self.card(self.dev_c, todo)[1]['allowed_moves'], ['in_progress'])
        self.assertEqual(self.card(self.dev_c, prog)[1]['allowed_moves'], ['review'])
        self.assertEqual(self.card(self.dev_c, review)[1]['allowed_moves'], [])
        self.assertEqual(self.card(self.dev_c, done)[1]['allowed_moves'], [])
        self.assertEqual(self.card(self.mgr_c, todo)[1]['allowed_moves'], [])      # reviewer is not the assignee
        self.assertEqual(self.card(self.mgr_c, review)[1]['allowed_moves'], ['todo', 'done'])
        self.assertEqual(self.card(self.mgr_c, done)[1]['allowed_moves'], [])


class MoveTests(BoardBase):
    def test_the_whole_happy_path(self):
        t = mk(self.cid, self.dev['id'])
        self.assertEqual(self.move(self.dev_c, t, 'in_progress').data['status'], 'in_progress')
        self.assertEqual(self.move(self.dev_c, t, 'review').data['status'], 'submitted')
        self.assertEqual(self.move(self.mgr_c, t, 'done').data['status'], 'completed')
        self.assertEqual(self.card(self.mgr_c, t)[0], 'done')

    def test_reject_sends_it_back_to_to_do_and_it_can_be_restarted(self):
        t = mk(self.cid, self.dev['id'], status='submitted')
        self.assertEqual(self.move(self.mgr_c, t, 'todo').data['status'], 'rejected')
        key, card = self.card(self.mgr_c, t)
        self.assertEqual((key, card['rejected']), ('todo', True))
        self.assertEqual(self.move(self.dev_c, t, 'in_progress').data['status'], 'in_progress')

    def test_wrong_moves_are_rejected_with_a_clear_message(self):
        cases = [
            ('not_started', 'review', 'Start the task first'),
            ('not_started', 'done', 'Start the task first'),
            ('in_progress', 'done', 'Submit the task for review first'),
            ('in_progress', 'todo', 'cannot go back to To Do'),
            ('submitted', 'in_progress', 'Done to approve, To Do to reject'),
            ('completed', 'todo', 'completed task cannot be moved'),
            ('completed', 'in_progress', 'completed task cannot be moved'),
            ('completed', 'review', 'completed task cannot be moved'),
            ('not_started', 'todo', 'already in To Do'),
            ('in_progress', 'in_progress', 'already in In Progress'),
        ]
        for status, column, words in cases:
            t = mk(self.cid, self.dev['id'], status=status)
            res = self.move(self.dev_c, t, column)
            self.assertEqual(res.status_code, 400, (status, column))
            self.assertIn(words, res.content.decode(), (status, column))
            t.refresh_from_db()
            self.assertEqual(t.status, status, 'a refused move changes nothing')

    def test_unknown_or_missing_column_is_400(self):
        t = mk(self.cid, self.dev['id'])
        for column in ('banana', '', None):
            self.assertEqual(self.move(self.dev_c, t, column).status_code, 400, column)

    def test_only_the_assignee_starts_and_submits(self):
        t = mk(self.cid, self.dev['id'])
        self.assertEqual(self.move(self.mgr_c, t, 'in_progress').status_code, 403)
        self.assertEqual(self.move(self.ceo, t, 'in_progress').status_code, 403)
        self.move(self.dev_c, t, 'in_progress')
        self.assertEqual(self.move(self.mgr_c, t, 'review').status_code, 403)
        self.assertEqual(Task.objects.get(id=t.id).status, 'in_progress')

    def test_the_assignee_cannot_approve_without_the_manager_permission(self):
        t = mk(self.cid, self.dev['id'], status='submitted')
        for column in ('done', 'todo'):
            self.assertEqual(self.move(self.dev_c, t, column).status_code, 403, column)
        self.assertEqual(Task.objects.get(id=t.id).status, 'submitted')

    def test_a_task_that_is_not_visible_cannot_be_moved(self):
        t = mk(self.cid, self.dev['id'])
        self.assertEqual(self.move(self.other_c, t, 'in_progress').status_code, 404)
        self.assertEqual(self.move(self.beta, t, 'in_progress').status_code, 404)

    def test_move_needs_login(self):
        t = mk(self.cid, self.dev['id'])
        self.assertIn(APIClient().post(f'{TASKS}{t.id}/move/', {'column': 'in_progress'}, format='json').status_code, (401, 403))

    def test_the_older_start_and_submit_buttons_still_work(self):
        t = mk(self.cid, self.dev['id'])
        self.assertEqual(self.dev_c.post(f'{TASKS}{t.id}/start/').status_code, 200)
        self.assertEqual(self.dev_c.post(f'{TASKS}{t.id}/submit/').status_code, 200)


class ProgressTests(BoardBase):
    def setUp(self):
        super().setUp()
        self.task = mk(self.cid, self.dev['id'], status='in_progress', by=self.mgr['id'])
        self.url = f'{TASKS}{self.task.id}/progress/'

    def add(self, client=None, **fields):
        body = {'update_text': 'Built the login form', 'progress_percent': 40}
        body.update(fields)
        return (client or self.dev_c).post(self.url, body, format='json')

    def test_the_assignee_adds_an_entry_dated_by_the_server(self):
        res = self.add(date='2000-01-01', employee_email='ceo@acme.com')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['date'], str(self.today))
        self.assertEqual(res.data['employee_email'], 'dev@acme.com')
        self.assertEqual((res.data['update_text'], res.data['progress_percent']), ('Built the login form', 40))

    def test_blocker_and_link_are_optional_and_kept(self):
        res = self.add(blocker_text='Waiting for API keys', external_reference_url='https://github.com/acme/app/commit/abc123')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['blocker_text'], 'Waiting for API keys')
        self.assertEqual(res.data['external_reference_url'], 'https://github.com/acme/app/commit/abc123')
        self.assertEqual(self.add().data['blocker_text'], '')

    def test_text_and_percent_are_required_and_checked(self):
        for bad in ({'update_text': ''}, {'update_text': '   '}, {'progress_percent': 101}, {'progress_percent': -1}, {'progress_percent': 'x'}):
            self.assertEqual(self.add(**bad).status_code, 400, bad)
        self.assertEqual(self.dev_c.post(self.url, {'update_text': 'x'}, format='json').status_code, 400)
        self.assertEqual(self.dev_c.post(self.url, {'progress_percent': 5}, format='json').status_code, 400)
        self.assertEqual(TaskProgressLog.objects.count(), 0)

    def test_the_link_must_be_http_or_https(self):
        for url in ('javascript:alert(1)', 'ftp://x.com/f', 'not a url', 'file:///etc/passwd'):
            self.assertEqual(self.add(external_reference_url=url).status_code, 400, url)
        self.assertEqual(self.add(external_reference_url='http://example.com/x').status_code, 201)

    def test_no_file_or_code_can_be_uploaded(self):
        res = self.add(file='data:text/plain;base64,aGk=', attachment='x.zip', code='print(1)')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(set(res.data), {'id', 'date', 'employee_email', 'update_text', 'progress_percent',
                                         'blocker_text', 'external_reference_url', 'created_at'})

    def test_only_the_assignee_can_add(self):
        res = self.add(client=self.mgr_c)                          # sees the task (created it) but is not the assignee
        self.assertEqual(res.status_code, 403)
        self.assertIn('Only the assignee', res.content.decode())
        self.assertEqual(self.add(client=self.ceo).status_code, 403)
        self.assertEqual(TaskProgressLog.objects.count(), 0)

    def test_someone_who_cannot_see_the_task_gets_404(self):
        self.assertEqual(self.add(client=self.other_c).status_code, 404)
        self.assertEqual(self.other_c.get(self.url).status_code, 404)
        self.assertEqual(self.add(client=self.beta).status_code, 404)
        self.assertEqual(self.beta.get(self.url).status_code, 404)

    def test_a_completed_task_is_closed(self):
        Task.objects.filter(id=self.task.id).update(status='completed')
        res = self.add()
        self.assertEqual(res.status_code, 400)
        self.assertIn('completed', res.content.decode())

    def test_entries_can_be_added_before_the_task_is_started(self):
        Task.objects.filter(id=self.task.id).update(status='not_started')
        self.assertEqual(self.add().status_code, 201)

    def test_timeline_is_newest_first_and_visible_to_assignee_and_manager(self):
        for day, text, pct in [(3, 'first', 10), (2, 'second', 20), (1, 'third', 30)]:
            TaskProgressLog.objects.create(task=self.task, employee_id=self.dev['id'], date=self.today - timedelta(days=day),
                                           update_text=text, progress_percent=pct)
        self.add(update_text='today', progress_percent=40)
        for client in (self.dev_c, self.mgr_c, self.ceo):
            res = client.get(self.url)
            self.assertEqual(res.status_code, 200)
            self.assertEqual([e['update_text'] for e in rows(res)], ['today', 'third', 'second', 'first'])
        self.assertEqual(self.dev_c.get(self.url).data['pagination']['count'], 4)

    def test_entries_cannot_be_edited_or_deleted(self):
        entry = self.add().data['id']
        for call in (self.dev_c.put, self.dev_c.patch, self.dev_c.delete):
            self.assertEqual(call(f'{self.url}{entry}/', {'update_text': 'x'}, format='json').status_code, 404)
        for call in (self.dev_c.put, self.dev_c.patch, self.dev_c.delete):
            self.assertEqual(call(self.url, {}, format='json').status_code, 405)
        self.assertEqual(TaskProgressLog.objects.count(), 1)

    def test_board_shows_the_new_progress_and_blocker(self):
        self.add(progress_percent=55, blocker_text='stuck')
        card = self.card(self.mgr_c, self.task)[1]
        self.assertEqual((card['progress_percent'], card['blocked']), (55, True))
