from django.apps import AppConfig


class AuditLogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'audit_log'

    def ready(self):
        from . import signals  # noqa: F401  (connects the handlers)
