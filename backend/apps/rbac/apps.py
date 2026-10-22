from django.apps import AppConfig
from django.db.models.signals import post_migrate


class RbacConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rbac'
    # The app used to be called "roles". Keeping the old label means the existing
    # migrations, tables (roles_*) and every developer's database keep working unchanged.
    label = 'roles'
    verbose_name = 'RBAC (Roles & Permissions)'

    def ready(self):
        from .services import sync_permission_catalog, sync_system_roles
        # The catalog first, so the CEO role below receives every Permission it lists.
        post_migrate.connect(sync_permission_catalog, sender=self, dispatch_uid="rbac_sync_permission_catalog")
        post_migrate.connect(sync_system_roles, dispatch_uid="rbac_sync_system_roles")
