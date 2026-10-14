from django.apps import AppConfig


class AttendanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'attendance'

    def ready(self):
        # When the approval engine finishes a leave request, the leave must follow the decision.
        from approvals.services import register_finish_handler
        from .leave_models import LeaveRequest
        from .leave_services import on_approval_finished
        register_finish_handler(LeaveRequest, on_approval_finished)
