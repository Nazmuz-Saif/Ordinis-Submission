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


def can_see_private_details(viewer: Employee, target: Employee) -> bool:
    """
    Who may see a person's phone, address, emergency contact and joining date (D4): the person,
    anyone above them in the reporting line, and holders of manage_employees.
    """
    return viewer.has_permission('manage_employees') or can_view_employee_data(viewer, target)


def can_see_access(viewer: Employee, target: Employee) -> bool:
    """Who may see a person's Roles and effective Permissions: the same people, plus holders of assign_roles."""
    return can_see_private_details(viewer, target) or viewer.has_permission('assign_roles')


def build_access(employee: Employee) -> dict:
    """
    The Roles a person holds and the Permissions they really have through them.
    `permissions` is the union over all Roles; each entry also says which Roles give it.
    """
    links = employee.employee_roles.select_related('role').prefetch_related('role__permissions').order_by('role__name')
    roles, effective = [], {}
    for link in links:
        role = link.role
        perms = sorted(role.permissions.all(), key=lambda p: (p.module, p.codename))
        roles.append({
            'id': str(role.id), 'name': role.name, 'is_system_default': role.is_system_default,
            'permissions': [_perm_dict(p) for p in perms],
        })
        for p in perms:
            entry = effective.setdefault(p.codename, {**_perm_dict(p), 'roles': []})
            entry['roles'].append(role.name)
    ordered = sorted(effective.values(), key=lambda e: (e['module'], e['codename']))
    return {'employee': str(employee.id), 'roles': roles, 'permissions': ordered}


def _perm_dict(p):
    return {'codename': p.codename, 'name': p.name, 'module': p.module, 'description': p.description}


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
