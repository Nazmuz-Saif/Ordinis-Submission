"""
Backfill: companies registered BEFORE real permission checks existed have no CEO role,
so their CEO would be locked out the moment HasPermission started enforcing.
For every company without a system-default role, create a full-access "CEO" role and
give it to the company's CEO (the employee whose designation is "CEO"; if none, the
earliest-created employee).
"""
from django.db import migrations


def backfill(apps, schema_editor):
    Company = apps.get_model("tenants", "Company")
    Role = apps.get_model("roles", "Role")
    Permission = apps.get_model("roles", "Permission")
    Employee = apps.get_model("organization", "Employee")
    EmployeeRole = apps.get_model("organization", "EmployeeRole")

    all_permissions = list(Permission.objects.all())

    for company in Company.objects.all():
        if Role.objects.filter(company=company, is_system_default=True).exists():
            continue

        ceos = list(Employee.objects.filter(company=company, designation__title__iexact="CEO"))
        if not ceos:
            first = Employee.objects.filter(company=company).order_by("created_at").first()
            ceos = [first] if first else []
        if not ceos:
            continue

        name = "CEO"
        if Role.objects.filter(company=company, name=name).exists():
            name = "CEO (System)"
        role = Role.objects.create(
            company=company,
            name=name,
            description="Full access. Created automatically for the company founder.",
            is_system_default=True,
        )
        role.permissions.set(all_permissions)
        for employee in ceos:
            EmployeeRole.objects.get_or_create(employee=employee, role=role, company=company)


class Migration(migrations.Migration):

    dependencies = [
        ("roles", "0003_delete_employeerole"),
        ("organization", "0004_repoint_employeerole_role_fk"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
