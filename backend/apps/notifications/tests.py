from datetime import timedelta

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from approvals.models import ApprovalChain, ApprovalInstance, DelegationRule
from approvals.services import decide, start_approval
from core.test_utils import add_employee, give_role, login_as, register_company, rows
from notifications.models import Notification
from organization.models import Employee
from tasks.models import Task

BASE = '/api/v1/notifications/'
INBOX = BASE + 'inbox/'
SUMMARY = BASE + 'inbox/summary/'
TASKS = '/api/v1/tasks/tasks/'


class Base(TestCase):
    def setUp(self):
        self.ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        self.cid = self.ceo.company_id
        self.emps, self.clients = {}, {}
        for key, email, code, perms in [
            ('dev', 'dev@acme.com', 'A-1', []), ('other', 'other@acme.com', 'A-2', []),
            ('mgr', 'mgr@acme.com', 'A-3', ['create_task']),
        ]:
            self.emps[key] = add_employee(self.ceo, email, code)
            if perms:
                give_role(self.cid, self.emps[key]['id'], perms, key)
            self.clients[key] = login_as(email)
        self.beta = register_company('Beta', 'beta', 'ceo@beta.com')

    def employee(self, key):
        return Employee.objects.get(id=self.emps[key]['id'])

    def notes(self, key, **filters):
        return Notification.objects.filter(recipient_id=self.emps[key]['id'], **filters)

    def chain(self, *role_names):
        """An approval chain with one step per role; returns (chain, [roles])."""
        chain = self.ceo.post('/api/v1/approvals/chains/', {'name': 'Leave', 'applies_to_module': 'leave'}, format='json').data['id']
        roles = []
        for name in role_names:
            holder = add_employee(self.ceo, f'{name}@acme.com', f'R-{name}')
            role = give_role(self.cid, holder['id'], [], name)
            self.ceo.post('/api/v1/approvals/steps/', {'approval_chain': chain, 'approver_role': str(role.id)}, format='json')
            roles.append((holder, role))
        return ApprovalChain.objects.get(id=chain), roles

    def quiet(self):
        """Forget notifications that building the test data created, so a test sees only what it is about."""
        Notification.objects.all().delete()

    def mk_task(self, key, status='not_started', **kw):
        return Task.objects.create(company_id=self.cid, title=kw.pop('title', 'T'), assigned_to_id=self.emps[key]['id'], status=status, **kw)


class TaskNotificationTests(Base):
    def test_assigning_a_task_notifies_the_assignee_only(self):
        res = self.clients['mgr'].post(TASKS, {'title': 'Build login', 'assigned_to': self.emps['dev']['id'], 'deadline': '2026-12-01'}, format='json')
        self.assertEqual(res.status_code, 201)
        note = self.notes('dev').get()
        self.assertEqual((note.kind, note.title, note.link), ('task_assigned', 'New task: Build login', '/tasks'))
        self.assertIn('assigned to you', note.message)
        self.assertIn('2026-12-01', note.message)
        self.assertEqual(str(note.company_id), str(self.cid))
        self.assertFalse(note.is_read)
        self.assertEqual(Notification.objects.exclude(recipient_id=self.emps['dev']['id']).count(), 0)

    def test_giving_a_task_to_yourself_sends_nothing(self):
        self.clients['mgr'].post(TASKS, {'title': 'Mine', 'assigned_to': self.emps['mgr']['id']}, format='json')
        self.assertEqual(Notification.objects.count(), 0)

    def test_reassigning_notifies_the_new_assignee_but_other_edits_do_not(self):
        tid = self.clients['mgr'].post(TASKS, {'title': 'X', 'assigned_to': self.emps['dev']['id']}, format='json').data['id']
        self.clients['mgr'].patch(f'{TASKS}{tid}/', {'title': 'X renamed'}, format='json')
        self.assertEqual(self.notes('dev').count(), 1)
        self.clients['mgr'].patch(f'{TASKS}{tid}/', {'assigned_to': self.emps['other']['id']}, format='json')
        self.assertEqual(self.notes('other').count(), 1)
        self.assertEqual(self.notes('dev').count(), 1)

    def test_a_task_for_someone_in_another_company_is_refused_and_notifies_nobody(self):
        res = self.clients['mgr'].post(TASKS, {'title': 'X', 'assigned_to': self.beta.employee_id}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Notification.objects.count(), 0)


    def test_the_listener_fires_for_any_way_a_task_is_saved(self):
        t = Task.objects.create(company_id=self.cid, title='via orm', assigned_to=self.employee('dev'), assigned_by=self.employee('mgr'))
        self.assertEqual(self.notes('dev').count(), 1)
        t.assigned_to = self.employee('other')
        t.save()
        self.assertEqual(self.notes('other').count(), 1)
        self.assertEqual(self.notes('dev').count(), 1)

    def test_status_changes_and_other_saves_send_nothing(self):
        t = Task.objects.create(company_id=self.cid, title='x', assigned_to=self.employee('dev'), assigned_by=self.employee('mgr'))
        self.quiet()
        t.status = 'in_progress'
        t.save(update_fields=['status', 'updated_at'])
        t.title = 'renamed'
        t.save()
        self.assertEqual(Notification.objects.count(), 0)

    def test_a_task_you_gave_yourself_and_bulk_imports_stay_quiet(self):
        mgr = self.employee('mgr')
        Task.objects.create(company_id=self.cid, title='mine', assigned_to=mgr, assigned_by=mgr)
        Task.objects.bulk_create([Task(company_id=self.cid, title='bulk', assigned_to=self.employee('dev'))])
        self.assertEqual(Notification.objects.count(), 0)


class ApprovalNotificationTests(Base):
    def test_starting_an_approval_notifies_every_holder_of_the_first_role_but_not_the_requester(self):
        chain, [(head, role)] = self.chain('head')
        second = add_employee(self.ceo, 'head2@acme.com', 'R-h2')
        give_role(self.cid, second['id'], [], 'head-b')
        from rbac.models import EmployeeRole
        EmployeeRole.objects.create(company_id=self.cid, employee_id=second['id'], role=role)
        start_approval(self.employee('dev'), chain, self.employee('dev'))
        self.assertEqual(self.notes('dev').count(), 0)
        for emp in (head['id'], second['id']):
            note = Notification.objects.get(recipient_id=emp)
            self.assertEqual((note.kind, note.link), ('approval_requested', '/approvals/pending'))
            self.assertEqual(note.title, 'Approval needed: Leave')
            self.assertIn('dev@acme.com', note.message)
        self.assertEqual(Notification.objects.count(), 2)

    def test_a_requester_who_holds_the_role_is_not_told_about_their_own_request(self):
        chain, [(head, role)] = self.chain('head')
        start_approval(Employee.objects.get(id=head['id']), chain, Employee.objects.get(id=head['id']))
        self.assertEqual(Notification.objects.count(), 0)

    def test_an_active_delegate_is_notified_too(self):
        chain, [(head, role)] = self.chain('head')
        today = timezone.localdate()
        DelegationRule.objects.create(company_id=self.cid, delegator_id=head['id'], delegate=self.employee('other'),
                                      start_date=today - timedelta(days=1), end_date=today + timedelta(days=1))
        DelegationRule.objects.create(company_id=self.cid, delegator_id=head['id'], delegate=self.employee('mgr'),
                                      start_date=today + timedelta(days=5), end_date=today + timedelta(days=9))
        start_approval(self.employee('dev'), chain, self.employee('dev'))
        self.assertEqual(self.notes('other').count(), 1)
        self.assertEqual(self.notes('mgr').count(), 0, 'a delegation that has not started yet')

    def test_approving_moves_the_notice_to_the_next_step_and_finishing_tells_the_requester(self):
        chain, [(h1, r1), (h2, r2)] = self.chain('first', 'second')
        inst = start_approval(self.employee('dev'), chain, self.employee('dev'))
        self.assertEqual(Notification.objects.filter(recipient_id=h2['id']).count(), 0)
        decide(inst.id, Employee.objects.get(id=h1['id']), 'approved')
        self.assertEqual(Notification.objects.filter(recipient_id=h2['id'], kind='approval_requested').count(), 1)
        self.assertEqual(Notification.objects.filter(recipient_id=h1['id']).count(), 1, 'step 1 is not notified again')
        self.assertEqual(self.notes('dev').count(), 0, 'not finished yet')
        decide(inst.id, Employee.objects.get(id=h2['id']), 'approved')
        done = self.notes('dev').get()
        self.assertEqual((done.kind, done.title), ('approval_decided', 'Leave: approved'))

    def test_a_rejection_tells_the_requester_and_nobody_else(self):
        chain, [(h1, r1), (h2, r2)] = self.chain('first', 'second')
        inst = start_approval(self.employee('dev'), chain, self.employee('dev'))
        decide(inst.id, Employee.objects.get(id=h1['id']), 'rejected', 'No budget')
        self.assertEqual(self.notes('dev').get().title, 'Leave: rejected')
        self.assertEqual(Notification.objects.filter(recipient_id=h2['id']).count(), 0)


class ReadingTests(Base):
    def make(self, key, title='n', **kw):
        return Notification.objects.create(company_id=self.cid, recipient_id=self.emps[key]['id'], kind='task_assigned', title=title, **kw)

    def test_list_shows_only_my_notifications_newest_first(self):
        self.make('dev', 'old'); self.make('dev', 'new'); self.make('other', 'not mine')
        self.assertEqual([n['title'] for n in rows(self.clients['dev'].get(BASE))], ['new', 'old'])

    def test_unread_filter(self):
        a = self.make('dev', 'a'); self.make('dev', 'b')
        self.clients['dev'].post(f'{BASE}{a.id}/read/')
        self.assertEqual([n['title'] for n in rows(self.clients['dev'].get(BASE + '?unread=true'))], ['b'])
        self.assertEqual(len(rows(self.clients['dev'].get(BASE))), 2)

    def test_mark_read_sets_the_time_and_is_safe_to_repeat(self):
        n = self.make('dev')
        first = self.clients['dev'].post(f'{BASE}{n.id}/read/')
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.data['is_read'])
        stamp = Notification.objects.get(id=n.id).read_at
        self.assertIsNotNone(stamp)
        self.clients['dev'].post(f'{BASE}{n.id}/read/')
        self.assertEqual(Notification.objects.get(id=n.id).read_at, stamp)

    def test_nobody_can_read_or_mark_someone_elses_notification(self):
        n = self.make('dev')
        for client in (self.clients['other'], self.clients['mgr'], self.ceo, self.beta):
            self.assertEqual(client.get(f'{BASE}{n.id}/').status_code, 404)
            self.assertEqual(client.post(f'{BASE}{n.id}/read/').status_code, 404)
        self.assertFalse(Notification.objects.get(id=n.id).is_read)

    def test_read_all_marks_only_mine(self):
        self.make('dev'); self.make('dev'); self.make('other')
        res = self.clients['dev'].post(BASE + 'read-all/')
        self.assertEqual(res.data['marked'], 2)
        self.assertEqual(self.notes('dev', is_read=False).count(), 0)
        self.assertEqual(self.notes('other', is_read=False).count(), 1)

    def test_login_is_required(self):
        for url in (BASE, INBOX, SUMMARY):
            self.assertIn(APIClient().get(url).status_code, (401, 403), url)
        self.assertIn(APIClient().post(BASE + 'read-all/').status_code, (401, 403))

    def test_a_suspended_company_gets_nothing(self):
        from tenants.models import Company
        Company.objects.filter(id=self.cid).update(is_active=False)
        self.assertEqual(self.clients['dev'].get(INBOX).status_code, 403)


class InboxTests(Base):
    def kinds(self, key):
        return [(i['kind'], i['title']) for i in rows(self.clients[key].get(INBOX))]

    def test_an_empty_inbox_is_empty(self):
        res = self.clients['dev'].get(INBOX)
        self.assertEqual((res.status_code, rows(res), res.data['pagination']['count']), (200, [], 0))
        self.assertEqual(self.clients['dev'].get(SUMMARY).data, {'total': 0, 'approvals': 0, 'tasks': 0, 'reviews': 0, 'unread': 0})

    def test_open_tasks_show_finished_and_waiting_ones_do_not(self):
        for status in ('not_started', 'in_progress', 'rejected', 'submitted', 'completed'):
            self.mk_task('dev', status, title=status)
        titles = {i['title'] for i in rows(self.clients['dev'].get(INBOX)) if i['kind'] == 'task'}
        self.assertEqual(titles, {'not_started', 'in_progress', 'rejected'})

    def test_other_peoples_tasks_never_appear(self):
        self.mk_task('other', title='theirs')
        self.quiet()
        self.assertEqual(self.kinds('dev'), [])
        self.assertEqual(self.kinds('other'), [('task', 'theirs')])

    def test_a_task_item_says_its_status_deadline_and_overdue(self):
        today = timezone.localdate()
        self.mk_task('dev', 'in_progress', title='late', deadline=today - timedelta(days=2))
        self.mk_task('dev', title='soon', deadline=today + timedelta(days=2))
        items = {i['title']: i for i in rows(self.clients['dev'].get(INBOX))}
        self.assertTrue(items['late']['overdue'])
        self.assertFalse(items['soon']['overdue'])
        self.assertIn('In Progress', items['late']['subtitle'])
        self.assertTrue(all(i['link'] == '/tasks' for i in items.values()))

    def test_the_person_who_assigned_a_task_sees_it_to_review_once_submitted(self):
        t = self.mk_task('dev', 'submitted', title='Please review')
        Task.objects.filter(id=t.id).update(assigned_by_id=self.emps['mgr']['id'])
        self.assertEqual(self.kinds('mgr'), [('task_review', 'Review: Please review')])
        self.assertEqual(self.kinds('other'), [])

    def test_approvals_waiting_for_me_show_only_for_the_approver(self):
        chain, [(head, role)] = self.chain('head')
        start_approval(self.employee('dev'), chain, self.employee('dev'))
        head_items = rows(login_as('head@acme.com').get(INBOX))
        approvals = [i for i in head_items if i['kind'] == 'approval']
        self.assertEqual(len(approvals), 1)
        self.assertEqual((approvals[0]['title'], approvals[0]['link']), ('Approval needed: Leave', '/approvals/pending'))
        self.assertEqual([i for i in rows(self.clients['dev'].get(INBOX)) if i['kind'] == 'approval'], [])
        self.assertEqual([i for i in rows(self.clients['other'].get(INBOX)) if i['kind'] == 'approval'], [])

    def test_unread_notifications_show_and_reading_one_removes_it_but_not_the_task(self):
        self.clients['mgr'].post(TASKS, {'title': 'New work', 'assigned_to': self.emps['dev']['id']}, format='json')
        before = rows(self.clients['dev'].get(INBOX))
        self.assertEqual([i['kind'] for i in before], ['task', 'notification'])
        note = [i for i in before if i['kind'] == 'notification'][0]
        self.clients['dev'].post(f'{BASE}{note["id"]}/read/')
        after = rows(self.clients['dev'].get(INBOX))
        self.assertEqual([i['kind'] for i in after], ['task'])
        self.assertEqual(self.clients['dev'].get(SUMMARY).data['unread'], 0)

    def test_order_approvals_then_reviews_then_tasks_then_notifications(self):
        chain, [(head, role)] = self.chain('head')
        h = Employee.objects.get(id=head['id'])
        Task.objects.create(company_id=self.cid, title='b-later', assigned_to=h, deadline=timezone.localdate() + timedelta(days=3))
        Task.objects.create(company_id=self.cid, title='a-late', assigned_to=h, deadline=timezone.localdate() - timedelta(days=3))
        Task.objects.create(company_id=self.cid, title='to-review', assigned_to=self.employee('dev'), status='submitted', assigned_by=h)
        self.quiet()
        start_approval(self.employee('dev'), chain, self.employee('dev'))                 # approval + one notification for head
        kinds = [(i['kind'], i['title']) for i in rows(login_as('head@acme.com').get(INBOX))]
        self.assertEqual(kinds, [
            ('approval', 'Approval needed: Leave'), ('task_review', 'Review: to-review'),
            ('task', 'a-late'), ('task', 'b-later'), ('notification', 'Approval needed: Leave')])

    def test_summary_counts_each_source(self):
        chain, [(head, role)] = self.chain('head')
        h = Employee.objects.get(id=head['id'])
        Task.objects.create(company_id=self.cid, title='t1', assigned_to=h)
        Task.objects.create(company_id=self.cid, title='t2', assigned_to=h, status='in_progress')
        Task.objects.create(company_id=self.cid, title='r', assigned_to=self.employee('dev'), status='submitted', assigned_by=h)
        self.quiet()
        start_approval(self.employee('dev'), chain, self.employee('dev'))
        self.assertEqual(login_as('head@acme.com').get(SUMMARY).data,
                         {'total': 5, 'approvals': 1, 'tasks': 2, 'reviews': 1, 'unread': 1})

    def test_another_companys_items_never_appear(self):
        Task.objects.create(company_id=self.beta.company_id, title='beta task', assigned_to_id=self.beta.employee_id)
        self.quiet()
        Notification.objects.create(company_id=self.beta.company_id, recipient_id=self.beta.employee_id, kind='task_assigned', title='beta note')
        body = ''.join(self.clients[k].get(INBOX).content.decode() for k in self.clients) + self.ceo.get(INBOX).content.decode()
        self.assertNotIn('beta', body)
        self.assertEqual(self.beta.get(SUMMARY).data['total'], 2)

    def test_the_inbox_is_paged(self):
        Task.objects.bulk_create([Task(company_id=self.cid, title=f'T{i}', assigned_to_id=self.emps['dev']['id']) for i in range(25)])
        res = self.clients['dev'].get(INBOX)
        self.assertEqual((len(rows(res)), res.data['pagination']['count']), (20, 25))
        self.assertEqual(len(rows(self.clients['dev'].get(INBOX + '?page=2'))), 5)

    def test_query_count_does_not_grow_with_the_number_of_items(self):
        chain, [(head, role)] = self.chain('head')
        dev = self.employee('dev')
        h = login_as('head@acme.com')

        def queries():
            with CaptureQueriesContext(connection) as ctx:
                h.get(INBOX)
            return len(ctx)
        start_approval(dev, chain, dev)
        few = queries()
        for _ in range(8):
            start_approval(dev, chain, dev)
        for i in range(10):
            Task.objects.create(company_id=self.cid, title=f'x{i}', assigned_to_id=head['id'])
        self.assertEqual(queries(), few, 'more approvals and tasks must not mean more queries')
