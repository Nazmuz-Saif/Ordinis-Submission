"""
Moves EmployeeRole from the organization app to the rbac app (as the SDS specifies).

State only: the table `organization_employeerole` already exists (with its data and
constraints), so we only tell Django that the model now belongs to this app. No table
is created, copied, or dropped.
"""
import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organization", "0004_repoint_employeerole_role_fk"),
        ("roles", "0004_backfill_ceo_roles"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="EmployeeRole",
                    fields=[
                        ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        ("is_deleted", models.BooleanField(default=False)),
                        ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="employee_roles", to="tenants.company")),
                        ("employee", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="employee_roles", to="organization.employee")),
                        ("role", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="employee_roles", to="roles.role")),
                    ],
                    options={
                        "db_table": "organization_employeerole",
                        "constraints": [models.UniqueConstraint(fields=("employee", "role"), name="unique_employee_role_assignment")],
                    },
                ),
            ],
        ),
    ]
