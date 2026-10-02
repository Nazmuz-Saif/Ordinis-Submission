from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("organization", "0002_permission_role_employeerole_and_more"),
        ("roles", "0002_seed_permissions"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS "organization_employeerole" (
                "id" char(32) NOT NULL PRIMARY KEY,
                "created_at" datetime NOT NULL,
                "updated_at" datetime NOT NULL,
                "is_deleted" bool NOT NULL,
                "company_id" char(32) NOT NULL REFERENCES "tenants_company" ("id") DEFERRABLE INITIALLY DEFERRED,
                "employee_id" char(32) NOT NULL REFERENCES "organization_employee" ("id") DEFERRABLE INITIALLY DEFERRED,
                "role_id" char(32) NOT NULL REFERENCES "roles_role" ("id") DEFERRABLE INITIALLY DEFERRED,
                CONSTRAINT "unique_employee_role_assignment" UNIQUE ("employee_id", "role_id")
            );

            INSERT OR IGNORE INTO "organization_employeerole"
            (
                "id",
                "created_at",
                "updated_at",
                "is_deleted",
                "company_id",
                "employee_id",
                "role_id"
            )
            SELECT
                er."id",
                er."created_at",
                er."updated_at",
                er."is_deleted",
                r."company_id",
                er."employee_id",
                er."role_id"
            FROM "roles_employeerole" er
            INNER JOIN "roles_role" r
                ON r."id" = er."role_id";

            CREATE INDEX IF NOT EXISTS "organization_employeerole_company_id_idx"
            ON "organization_employeerole" ("company_id");

            CREATE INDEX IF NOT EXISTS "organization_employeerole_employee_id_idx"
            ON "organization_employeerole" ("employee_id");

            CREATE INDEX IF NOT EXISTS "organization_employeerole_role_id_idx"
            ON "organization_employeerole" ("role_id");
            """,
            reverse_sql="""
            INSERT OR IGNORE INTO "roles_employeerole"
            (
                "id",
                "created_at",
                "updated_at",
                "is_deleted",
                "assigned_at",
                "employee_id",
                "role_id"
            )
            SELECT
                er."id",
                er."created_at",
                er."updated_at",
                er."is_deleted",
                CURRENT_TIMESTAMP,
                er."employee_id",
                er."role_id"
            FROM "organization_employeerole" er;

            DROP TABLE IF EXISTS "organization_employeerole";
            """,
        ),
        migrations.DeleteModel(
            name="EmployeeRole",
        ),
    ]