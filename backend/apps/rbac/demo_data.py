from core import demo
from .models import EmployeeRole, Permission, Role

ORDER = 20

ROLES = {
    'Manager': ('Creates and reviews tasks, and approves the first step of leave.', ['create_task']),
    'HR': ('People records, leave types, and the second step of leave.', [
        'manage_employees', 'manage_departments', 'manage_designations', 'manage_leave_types', 'assign_roles',
    ]),
    'Accountant': ('Salary structures and payslips only.', ['manage_finance']),
}


def seed(ctx):
    company = ctx.company
    roles = {}
    for name, (description, codenames) in ROLES.items():
        role, created = Role.objects.get_or_create(company=company, name=name, defaults={'description': description})
        ctx.note('roles', created)
        role.permissions.set(Permission.objects.filter(codename__in=codenames))
        roles[name] = role
    for key, _local, _title, _department, _boss, role_names in demo.PEOPLE:
        for name in role_names:
            _, created = EmployeeRole.objects.get_or_create(
                employee=ctx.emp(key), role=roles[name], defaults={'company': company},
            )
            ctx.note('role assignments', created)
