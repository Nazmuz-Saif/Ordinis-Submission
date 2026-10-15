from datetime import timedelta

from notifications.services import notify_task_assigned
from .models import Task, TaskProgressLog

ORDER = 40

# title, assignee, assigned by, status, priority, deadline in days from today, progress notes (days ago, percent, text)
TASKS = [
    ('Design the new onboarding screens', 'designer', 'manager', 'not_started', 'medium', 9, []),
    ('Write API documentation for Payroll', 'dev2', 'manager', 'not_started', 'low', 14, []),
    ('Prepare the Q4 sales target sheet', 'sales1', 'sales_head', 'not_started', 'high', 6, []),
    ('Fix the date filter on the reports page', 'employee', 'manager', 'rejected', 'medium', 3, [
        (5, 80, 'Filter works for months, the year view still shows old data.'),
    ]),
    ('Build the employee directory search', 'employee', 'manager', 'in_progress', 'high', 5, [
        (4, 20, 'Search box and API call are in place.'),
        (2, 55, 'Results list and empty state done. Starting on paging.'),
        (1, 70, 'Paging works. Checking the slow query with 500 employees.'),
    ]),
    ('Migrate login to the new token flow', 'dev2', 'manager', 'in_progress', 'high', 2, [
        (3, 40, 'Refresh token rotation done on the backend.'),
        (1, 60, 'Frontend now retries once after a 401.'),
    ]),
    ('Redesign the leave request form', 'designer', 'manager', 'in_progress', 'medium', 8, [
        (2, 35, 'Two layout options ready for review.'),
    ]),
    ('Follow up with the three open client quotes', 'sales1', 'sales_head', 'in_progress', 'medium', -1, [
        (3, 50, 'Two clients replied, one needs a revised price.'),
    ]),
    ('Add unit tests for the approval engine', 'dev2', 'manager', 'submitted', 'medium', 4, [
        (3, 60, 'Happy path and rejection covered.'),
        (1, 100, 'Delegation and own-request cases covered. Ready for review.'),
    ]),
    ('Prepare the monthly sales report', 'sales1', 'sales_head', 'submitted', 'low', 3, [
        (2, 100, 'Report is ready in the shared folder.'),
    ]),
    ('Update the brand colours in the app', 'designer', 'manager', 'submitted', 'low', 5, [
        (1, 100, 'Palette and buttons updated on all screens.'),
    ]),
    ('Set up the staging server', 'employee', 'manager', 'completed', 'high', -4, [
        (9, 30, 'Server created.'),
        (6, 80, 'Deployment script works.'),
        (5, 100, 'Staging is live and checked.'),
    ]),
    ('Import last year employee records', 'dev2', 'manager', 'completed', 'medium', -6, [
        (10, 50, 'First 40 records imported.'),
        (8, 100, 'All records imported and checked.'),
    ]),
    ('Collect client feedback after the demo', 'sales_head', 'gm', 'completed', 'medium', -2, [
        (5, 100, 'Feedback from all six clients collected.'),
    ]),
    ('Plan the team offsite', 'hr', 'gm', 'in_progress', 'low', 12, [
        (2, 25, 'Three venues shortlisted.'),
    ]),
]


def seed(ctx):
    company = ctx.company
    for title, assignee, assigner, status, priority, due_in, notes in TASKS:
        task, created = Task.objects.get_or_create(
            company=company, title=title,
            defaults={
                'description': f'{title}. Part of the Acme product work for this quarter.',
                'assigned_to': ctx.emp(assignee), 'assigned_by': ctx.emp(assigner),
                'priority': priority, 'deadline': ctx.today + timedelta(days=due_in), 'status': status,
            },
        )
        ctx.note('tasks', created)
        if created:
            notify_task_assigned(task)
        for days_ago, percent, text in notes:
            _, made = TaskProgressLog.objects.get_or_create(
                task=task, employee=task.assigned_to, update_text=text,
                defaults={'date': ctx.today - timedelta(days=days_ago), 'progress_percent': percent},
            )
            ctx.note('progress notes', made)
