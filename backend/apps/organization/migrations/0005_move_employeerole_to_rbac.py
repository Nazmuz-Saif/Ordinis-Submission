"""
organization no longer owns EmployeeRole (it moved to rbac). State only — the table stays.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("organization", "0004_repoint_employeerole_role_fk"),
        ("roles", "0005_employeerole"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="EmployeeRole"),
            ],
        ),
    ]
