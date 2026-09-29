from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        (
            "organization",
            "0002_permission_role_employeerole_and_more",
        ),
        (
            "roles",
            "0003_delete_employeerole",
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="permission",
                    name="unique_company_permission_codename",
                ),
                migrations.RemoveConstraint(
                    model_name="role",
                    name="unique_company_role_name",
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
                migrations.RemoveField(
                    model_name="role",
                    name="company",
                ),
                migrations.RemoveField(
                    model_name="role",
                    name="permissions",
                ),
                migrations.DeleteModel(
                    name="Permission",
                ),
                migrations.DeleteModel(
                    name="Role",
                ),
            ],
        ),
    ]