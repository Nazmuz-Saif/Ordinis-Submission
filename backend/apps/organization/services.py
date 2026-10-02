from .models import Employee


def get_all_subordinates(employee: Employee):
    """
    Returns a flat list of ALL employees under the given employee,
    at any depth (direct reports, their reports, and so on).

    This is the recursive "who reports to me" query — the foundation
    of hierarchy-based visibility across the whole system.
    """
    subordinates = []
    direct_reports = employee.direct_reports.all()

    for report in direct_reports:
        subordinates.append(report)
        subordinates.extend(get_all_subordinates(report))

    return subordinates


def get_all_managers(employee: Employee):
    """
    Returns the full chain of command ABOVE the given employee,
    from their direct manager up to the CEO (or wherever the
    reports_to chain ends).
    """
    managers = []
    current = employee.reports_to

    while current is not None:
        managers.append(current)
        current = current.reports_to

    return managers


def can_view_employee_data(viewer: Employee, target: Employee) -> bool:
    """
    Core visibility rule: a viewer can see a target employee's data
    if the target is the viewer themself, OR the target is anywhere
    below the viewer in the hierarchy.
    """
    if viewer.id == target.id:
        return True

    subordinates = get_all_subordinates(viewer)
    return target in subordinates


def creates_reporting_cycle(employee: Employee, new_manager: Employee) -> bool:
    """
    True if making `new_manager` the manager of `employee` would make an
    employee report (directly or indirectly) to themselves.
    Walks UP from the new manager; if we meet `employee`, it is a cycle.
    """
    seen = set()
    current = new_manager
    while current is not None and current.id not in seen:
        if current.id == employee.id:
            return True
        seen.add(current.id)
        current = current.reports_to
    return False
