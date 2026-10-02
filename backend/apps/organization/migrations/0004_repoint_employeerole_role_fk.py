"""
Fixes a stale foreign key left behind when Role moved from the organization app
to the roles app (0003 changed only Django's migration *state*, not the database).

On a fresh database, organization_employeerole.role_id still pointed at the old
organization_role table, so assigning any Role failed. We re-point the constraint
to roles_role (drop then re-add it) and remove the three orphaned old tables.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organization", "0003_remove_permission_unique_company_permission_codename_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="employeerole",
            name="role",
            field=models.ForeignKey(
                db_constraint=False,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="employee_roles",
                to="roles.role",
            ),
        ),
        migrations.AlterField(
            model_name="employeerole",
            name="role",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="employee_roles",
                to="roles.role",
            ),
        ),
        migrations.RunSQL(
            sql=[
                'DROP TABLE IF EXISTS "organization_role_permissions"',
                'DROP TABLE IF EXISTS "organization_role"',
                'DROP TABLE IF EXISTS "organization_permission"',
            ],
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
