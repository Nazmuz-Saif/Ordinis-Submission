"""ST-154: every suspend, activate and resolve carries a note, and a company can read what became of its ticket."""
from core.test_utils import add_employee, login_as, rows
from platform_admin.models import PlatformActionLog, SupportAccessRequest, SupportTicket
from platform_admin.test_panel import COMPANIES, TICKETS, PanelBase

MY_TICKETS = '/api/v1/platform-admin/company/tickets/'
ACTIONS = '/api/v1/platform-admin/admin/actions/'
REQUESTS = '/api/v1/platform-admin/requests/'
ADMIN_REQUESTS = '/api/v1/platform-admin/admin/access-requests/'


class NoteRequiredTests(PanelBase):
    def post(self, action, note=None, company=None):
        data = {} if note is None else {'note': note}
        return self.admin.post(f'{COMPANIES}{company or self.beta_id}/{action}/', data, format='json')

    def test_missing_blank_and_short_notes_are_refused_and_change_nothing(self):
        for action in ('suspend', 'activate'):
            for note, code in ((None, 'NOTE_REQUIRED'), ('', 'NOTE_REQUIRED'), ('   ', 'NOTE_REQUIRED'), ('too short', 'NOTE_TOO_SHORT')):
                res = self.post(action, note)
                self.assertEqual(res.status_code, 400, (action, note))
                self.assertEqual(res.data['error']['code'], code)
                self.assertIn('note', res.data['error']['field_errors'])
        self.assertTrue(self.company_active(self.beta_id))
        self.assertFalse(PlatformActionLog.objects.exists())

    def company_active(self, cid):
        from tenants.models import Company
        return Company.objects.get(pk=cid).is_active

    def test_ten_characters_after_trimming_is_enough_and_is_saved_trimmed(self):
        self.assertEqual(self.post('suspend', '  1234567890  ').status_code, 200)
        self.assertFalse(self.company_active(self.beta_id))
        self.assertEqual(PlatformActionLog.objects.get(action='suspend').note, '1234567890')

    def test_too_long_note_is_refused(self):
        self.assertEqual(self.post('suspend', 'x' * 256).data['error']['code'], 'NOTE_TOO_LONG')

    def test_the_activity_list_returns_the_note(self):
        self.post('suspend', 'Unpaid invoice for two months')
        got = rows(self.admin.get(ACTIONS))
        self.assertEqual(got[0]['note'], 'Unpaid invoice for two months')
        self.assertEqual(got[0]['action'], 'suspend')

    def test_repeating_the_same_state_still_needs_a_note(self):
        self.assertEqual(self.post('activate').status_code, 400)       # already active, no note
        self.assertEqual(self.post('activate', 'Already active, checked').status_code, 200)
        self.assertFalse(PlatformActionLog.objects.exists())          # and nothing is logged for a no-op


class ResolutionNoteTests(PanelBase):
    def setUp(self):
        super().setUp()
        self.ticket_id = self.emp_c.post(MY_TICKETS, {'subject': 'Cannot see payslip', 'description': 'It is empty'}, format='json').data['id']

    def resolve(self, note=None, ticket=None):
        data = {} if note is None else {'note': note}
        return self.admin.post(f'{TICKETS}{ticket or self.ticket_id}/resolve/', data, format='json')

    def test_resolving_needs_a_note(self):
        for note, code in ((None, 'NOTE_REQUIRED'), ('short', 'NOTE_TOO_SHORT'), ('x' * 501, 'NOTE_TOO_LONG')):
            res = self.resolve(note)
            self.assertEqual((res.status_code, res.data['error']['code']), (400, code))
        self.assertEqual(SupportTicket.objects.get(pk=self.ticket_id).status, 'open')

    def test_the_note_is_saved_logged_and_read_by_the_company(self):
        res = self.resolve('Payslip regenerated, please check again')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.data['status'], 'resolved')
        self.assertEqual(res.data['resolution_note'], 'Payslip regenerated, please check again')
        mine = login_as('emp@acme.com').get(f'{MY_TICKETS}{self.ticket_id}/').data
        self.assertEqual((mine['status'], mine['resolution_note']), ('resolved', 'Payslip regenerated, please check again'))
        log = PlatformActionLog.objects.get(action='resolve_ticket')
        self.assertIn('Payslip regenerated', log.note)
        self.assertIn('Cannot see payslip', log.note)

    def test_reopening_needs_no_note_and_clears_it(self):
        self.resolve('Payslip regenerated, please check again')
        res = self.admin.post(f'{TICKETS}{self.ticket_id}/reopen/')
        self.assertEqual((res.status_code, res.data['status'], res.data['resolution_note']), (200, 'open', ''))


class CompanyTicketTests(PanelBase):
    def test_a_user_sees_only_their_own_tickets_and_another_company_gets_404(self):
        mine = self.emp_c.post(MY_TICKETS, {'subject': 'Mine', 'description': 'text here'}, format='json')
        self.assertEqual(mine.status_code, 201, mine.content)
        add_employee(self.ceo, 'second@acme.com', 'ACME-9')
        theirs = login_as('second@acme.com').post(MY_TICKETS, {'subject': 'Theirs', 'description': 'text'}, format='json').data['id']
        listed = [t['subject'] for t in rows(self.emp_c.get(MY_TICKETS))]
        self.assertEqual(listed, ['Mine'])
        self.assertEqual(self.emp_c.get(f'{MY_TICKETS}{theirs}/').status_code, 404)
        self.assertEqual(self.beta.get(f"{MY_TICKETS}{mine.data['id']}/").status_code, 404)

    def test_a_ticket_needs_a_subject(self):
        res = self.emp_c.post(MY_TICKETS, {'subject': ' ', 'description': 'x'}, format='json')
        self.assertEqual(res.status_code, 400)


class RequestAccessTests(PanelBase):
    def test_a_request_is_created_pending_and_listed_for_the_admin(self):
        res = self.admin.post(REQUESTS, {'company': str(self.beta_id), 'reason': 'Bug 12 needs a look'}, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        got = rows(self.admin.get(ADMIN_REQUESTS))
        self.assertEqual((got[0]['company_name'], got[0]['status'], got[0]['reason']), ('Beta', 'pending', 'Bug 12 needs a look'))

    def test_a_second_open_request_for_the_same_company_is_refused(self):
        self.admin.post(REQUESTS, {'company': str(self.beta_id), 'reason': 'First reason here'}, format='json')
        res = self.admin.post(REQUESTS, {'company': str(self.beta_id), 'reason': 'Second reason here'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(SupportAccessRequest.objects.filter(company_id=self.beta_id).count(), 1)

    def test_a_blank_reason_is_refused(self):
        self.assertEqual(self.admin.post(REQUESTS, {'company': str(self.beta_id), 'reason': ' '}, format='json').status_code, 400)
