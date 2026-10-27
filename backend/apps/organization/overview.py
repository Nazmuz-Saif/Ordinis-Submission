"""
Detail pages for a Department and a Designation (ST-150).

Everybody in the company may open them and see the people and the task COUNTS.
A task's title, assignee, priority, deadline and progress are shown only to a viewer who may see that task:
holders of create_task (company-wide), the assignee, the person who assigned it, and every manager
above the assignee. Everybody else gets the count of hidden tasks only (D4).
"""
from django.db.models import Count, Q

from attendance.services import local_today
from tasks.models import Task

from .models import Employee

RUNNING_STATUSES = (Task.STATUS_IN_PROGRESS, Task.STATUS_SUBMITTED)
RUNNING_LIMIT = 50
MEMBER_LIMIT_IN_MESSAGE = 5


def _person(employee):
    if employee is None:
        return None
    return {
        'id': str(employee.id),
        'full_name': employee.user.full_name,
        'user_email': employee.user.email,
        'employee_code': employee.employee_code,
    }


def subordinate_ids(viewer):
    """Ids of everyone below `viewer` at any depth, from ONE query (not one per level)."""
    children = {}
    for emp_id, boss_id in Employee.objects.filter(company_id=viewer.company_id, reports_to__isnull=False).values_list('id', 'reports_to_id'):
        children.setdefault(boss_id, []).append(emp_id)
    found, stack = set(), [viewer.id]
    while stack:
        for child in children.get(stack.pop(), []):
            if child not in found:
                found.add(child)
                stack.append(child)
    return found


def _may_see_task(task, viewer, company_wide, below):
    return (
        company_wide
        or task.assigned_to_id == viewer.id
        or task.assigned_by_id == viewer.id
        or task.assigned_to_id in below
    )


def _task_summary(tasks, today):
    counts = {row['status']: row['n'] for row in tasks.values('status').annotate(n=Count('id'))}
    overdue = tasks.filter(deadline__lt=today).exclude(status=Task.STATUS_COMPLETED).count()
    return {
        'not_started': counts.get(Task.STATUS_NOT_STARTED, 0) + counts.get(Task.STATUS_REJECTED, 0),
        'in_progress': counts.get(Task.STATUS_IN_PROGRESS, 0),
        'submitted': counts.get(Task.STATUS_SUBMITTED, 0),
        'completed': counts.get(Task.STATUS_COMPLETED, 0),
        'overdue': overdue,
        'total': sum(counts.values()),
    }


def _running(tasks, viewer, company_wide):
    """(visible running tasks, how many running tasks the viewer may not see)."""
    running = tasks.filter(status__in=RUNNING_STATUSES).select_related('assigned_to__user').order_by('deadline', 'created_at', 'id')
    total = running.count()
    below = set() if company_wide else subordinate_ids(viewer)
    visible = []
    for task in running[:RUNNING_LIMIT * 4] if not company_wide else running[:RUNNING_LIMIT]:
        if _may_see_task(task, viewer, company_wide, below):
            visible.append(task)
        if len(visible) == RUNNING_LIMIT:
            break
    latest = {}
    if visible:
        from tasks.models import TaskProgressLog
        for log in TaskProgressLog.objects.filter(task__in=visible).order_by('date', 'created_at').values('task_id', 'progress_percent'):
            latest[log['task_id']] = log['progress_percent']
    rows = [{
        'id': str(t.id), 'title': t.title, 'priority': t.priority, 'status': t.status,
        'deadline': t.deadline.isoformat() if t.deadline else None,
        'progress_percent': 100 if t.status == Task.STATUS_COMPLETED else latest.get(t.id, 0),
        'assignee': _person(t.assigned_to),
    } for t in visible]
    return rows, max(total - len(visible), 0)


def _members(queryset):
    members = queryset.select_related('user', 'designation', 'department', 'reports_to__user').annotate(
        open_tasks=Count('assigned_tasks', filter=~Q(assigned_tasks__status=Task.STATUS_COMPLETED), distinct=True),
    ).order_by('user__full_name', 'employee_code')
    return members


def _member_row(employee):
    return {
        **_person(employee),
        'designation_title': employee.designation.title if employee.designation_id else None,
        'department_name': employee.department.name if employee.department_id else None,
        'manager': _person(employee.reports_to) if employee.reports_to_id else None,
        'open_tasks': employee.open_tasks,
    }


def department_overview(department, viewer):
    company_wide = viewer.has_permission('create_task')
    today, _ = local_today(department.company)
    members = list(_members(department.employees.all()))
    tasks = Task.objects.filter(company_id=department.company_id, assigned_to__department=department)
    running, hidden = _running(tasks, viewer, company_wide)
    head = department.head
    return {
        'id': str(department.id),
        'name': department.name,
        'head': _person(head),
        'member_count': len(members),
        'members': [_member_row(m) for m in members],
        'task_summary': _task_summary(tasks, today),
        'running_tasks': running,
        'hidden_running_tasks': hidden,
        'can_see_task_details': company_wide,
    }


def designation_overview(designation):
    members = list(_members(designation.employees.all()))
    return {
        'id': str(designation.id),
        'title': designation.title,
        'employee_count': len(members),
        'employees': [_member_row(m) for m in members],
    }


def in_use_message(label, employees):
    """'Sales still has 3 employees: Anna, Ben, Chris. Move them first, then delete it.'"""
    names = [e.user.full_name or e.user.email for e in employees[:MEMBER_LIMIT_IN_MESSAGE]]
    total = len(employees)
    more = f' and {total - len(names)} more' if total > len(names) else ''
    return (
        f"{label} still has {total} employee{'s' if total != 1 else ''}: {', '.join(names)}{more}. "
        "Move them to another one first, then delete it."
    )
