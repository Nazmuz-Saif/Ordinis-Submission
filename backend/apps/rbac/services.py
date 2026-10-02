from .models import EmployeeRole, Permission, Role

CEO_ROLE_NAME = "CEO"


def create_ceo_role(company, employee):
    """
    Gives a newly registered company its full-access "CEO" Role and assigns it
    to the founding employee. Without this the first user would hold no
    Permission at all and the real permission check would lock them out.
    """
    role = Role.objects.create(
        company=company,
        name=CEO_ROLE_NAME,
        description="Full access. Created automatically for the company founder.",
        is_system_default=True,
    )
    role.permissions.set(Permission.objects.all())
    EmployeeRole.objects.create(employee=employee, role=role, company=company)
    return role


def sync_system_roles(**kwargs):
    """
    Keeps every system-default Role holding ALL Permissions, so a Permission
    added in a later migration is never missing from a company's CEO role.
    Runs after every migrate.
    """
    from django.db.utils import OperationalError, ProgrammingError

    try:
        all_permissions = list(Permission.objects.all())
        for role in Role.objects.filter(is_system_default=True):
            role.permissions.set(all_permissions)
    except (OperationalError, ProgrammingError):
        # Tables do not exist yet (e.g. migrating to an early migration).
        return
