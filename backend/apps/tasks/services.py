from .models import Task, TaskProgressLog

# Allowed status changes. Anything not listed here is rejected.
ALLOWED_TRANSITIONS = {
    Task.STATUS_NOT_STARTED: {Task.STATUS_IN_PROGRESS},
    Task.STATUS_IN_PROGRESS: {Task.STATUS_SUBMITTED},
    Task.STATUS_SUBMITTED: {Task.STATUS_COMPLETED, Task.STATUS_REJECTED},
    Task.STATUS_REJECTED: {Task.STATUS_IN_PROGRESS},
    Task.STATUS_COMPLETED: set(),
}

_LABELS = dict(Task.STATUS_CHOICES)


class TaskError(ValueError):
    """The requested status change is not allowed."""


class NotTheAssignee(PermissionError):
    """Only the person the task is assigned to may do this."""


def check_transition(current, new):
    if new not in ALLOWED_TRANSITIONS.get(current, set()):
        raise TaskError(f'A task cannot move from {_LABELS[current]} to {_LABELS[new]}.')


def _assignee_changes_status(task, actor, new_status):
    if task.assigned_to_id != actor.id:
        raise NotTheAssignee('Only the assignee can do this.')
    check_transition(task.status, new_status)
    task.status = new_status
    task.save(update_fields=['status', 'updated_at'])
    return task


def start_task(task, actor):
    """Assignee starts working: Not Started (or Rejected) -> In Progress."""
    return _assignee_changes_status(task, actor, Task.STATUS_IN_PROGRESS)


def submit_task(task, actor):
    """Assignee hands the work in: In Progress -> Submitted."""
    return _assignee_changes_status(task, actor, Task.STATUS_SUBMITTED)


# ---------- Kanban board (ST-125) ----------
# Four columns. Status -> column:  Not Started and Rejected -> To Do,  In Progress,  Submitted -> Review,  Completed -> Done
COLUMNS = [
    ('todo', 'To Do'),
    ('in_progress', 'In Progress'),
    ('review', 'Review'),
    ('done', 'Done'),
]
COLUMN_LABELS = dict(COLUMNS)
COLUMN_OF_STATUS = {
    Task.STATUS_NOT_STARTED: 'todo',
    Task.STATUS_REJECTED: 'todo',
    Task.STATUS_IN_PROGRESS: 'in_progress',
    Task.STATUS_SUBMITTED: 'review',
    Task.STATUS_COMPLETED: 'done',
}

ASSIGNEE = 'assignee'    # only the person the task is assigned to
REVIEWER = 'reviewer'    # only someone with the create_task permission

# (current status, target column) -> (new status, who may do it)
MOVES = {
    (Task.STATUS_NOT_STARTED, 'in_progress'): (Task.STATUS_IN_PROGRESS, ASSIGNEE),
    (Task.STATUS_REJECTED, 'in_progress'): (Task.STATUS_IN_PROGRESS, ASSIGNEE),
    (Task.STATUS_IN_PROGRESS, 'review'): (Task.STATUS_SUBMITTED, ASSIGNEE),
    (Task.STATUS_SUBMITTED, 'done'): (Task.STATUS_COMPLETED, REVIEWER),
    (Task.STATUS_SUBMITTED, 'todo'): (Task.STATUS_REJECTED, REVIEWER),
}

HINTS = {
    ('todo', 'review'): 'Start the task first. A task moves To Do, In Progress, Review, Done.',
    ('todo', 'done'): 'Start the task first. A task moves To Do, In Progress, Review, Done.',
    ('in_progress', 'done'): 'Submit the task for review first. A reviewer then moves it to Done.',
    ('in_progress', 'todo'): 'A task that is In Progress cannot go back to To Do.',
    ('review', 'in_progress'): 'A task in Review is decided by a reviewer: Done to approve, To Do to reject.',
    ('done', 'todo'): 'A completed task cannot be moved.',
    ('done', 'in_progress'): 'A completed task cannot be moved.',
    ('done', 'review'): 'A completed task cannot be moved.',
}


class NotAReviewer(PermissionError):
    """Approving or rejecting needs the create_task permission."""


def column_of(task):
    return COLUMN_OF_STATUS[task.status]


def _may(task, actor, can_review, who):
    return task.assigned_to_id == actor.id if who == ASSIGNEE else bool(can_review)


def allowed_moves(task, actor, can_review):
    """The columns this user can move this task to right now."""
    return [
        column for column, _ in COLUMNS
        if (task.status, column) in MOVES and _may(task, actor, can_review, MOVES[(task.status, column)][1])
    ]


def move_task(task, actor, column, can_review):
    """Move a task to a column along the allowed path. Raises TaskError / NotTheAssignee / NotAReviewer."""
    if column not in COLUMN_LABELS:
        raise TaskError('Unknown column.')
    current = column_of(task)
    if column == current:
        raise TaskError(f'The task is already in {COLUMN_LABELS[column]}.')
    rule = MOVES.get((task.status, column))
    if rule is None:
        raise TaskError(
            HINTS.get((current, column))
            or f'A task cannot move from {COLUMN_LABELS[current]} to {COLUMN_LABELS[column]}.'
        )
    new_status, who = rule
    if not _may(task, actor, can_review, who):
        if who == ASSIGNEE:
            raise NotTheAssignee('Only the assignee can do this.')
        raise NotAReviewer('Only a task manager can approve or reject a task.')
    task.status = new_status
    task.save(update_fields=['status', 'updated_at'])
    return task


# ---------- Daily progress (ST-125) ----------

class TaskClosed(ValueError):
    """Progress cannot be added to a completed task."""


def add_progress(task, actor, data):
    """The assignee writes today's progress note. The date comes from the server, never from the client."""
    from attendance.services import local_today
    if task.assigned_to_id != actor.id:
        raise NotTheAssignee('Only the assignee can add progress.')
    if task.status == Task.STATUS_COMPLETED:
        raise TaskClosed('This task is completed, so progress can no longer be added.')
    today, _zone = local_today(task.company)
    return TaskProgressLog.objects.create(task=task, employee=actor, date=today, **data)


def build_board(queryset, actor, can_review, per_column=50):
    """The four Kanban columns for the tasks in `queryset` (already limited to what this user may see)."""
    from attendance.services import local_today
    from django.db.models import Case, F, IntegerField, OuterRef, Subquery, Value, When

    latest = TaskProgressLog.objects.filter(task=OuterRef('pk')).order_by('-date', '-created_at')
    queryset = queryset.annotate(
        latest_percent=Subquery(latest.values('progress_percent')[:1]),
        latest_blocker=Subquery(latest.values('blocker_text')[:1]),
    )
    rank = Case(
        When(priority='high', then=Value(0)), When(priority='medium', then=Value(1)),
        default=Value(2), output_field=IntegerField(),
    )
    today, _zone = local_today(actor.company)

    columns = []
    for key, label in COLUMNS:
        in_column = queryset.filter(status__in=[s for s, c in COLUMN_OF_STATUS.items() if c == key])
        count = in_column.count()
        ordered = in_column.order_by(rank, F('deadline').asc(nulls_last=True), '-created_at', 'id')[:per_column]
        cards = [{
            'id': t.id,
            'title': t.title,
            'priority': t.priority,
            'deadline': t.deadline,
            'status': t.status,
            'rejected': t.status == Task.STATUS_REJECTED,
            'assigned_to': t.assigned_to_id,
            'assigned_to_email': t.assigned_to.user.email,
            'overdue': bool(t.deadline and t.deadline < today and t.status != Task.STATUS_COMPLETED),
            'progress_percent': t.latest_percent or 0,
            'blocked': bool(t.latest_blocker),
            'allowed_moves': allowed_moves(t, actor, can_review),
            'can_add_progress': t.assigned_to_id == actor.id and t.status != Task.STATUS_COMPLETED,
        } for t in ordered]
        columns.append({'key': key, 'label': label, 'count': count, 'has_more': count > per_column, 'cards': cards})
    return {'columns': columns}
