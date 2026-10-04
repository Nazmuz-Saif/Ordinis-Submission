from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from core.mixins import AuditLoggingMixin, PermissionRequiredMixin
from .models import Task
from .serializers import TaskSerializer
from .services import NotTheAssignee, TaskError, start_task, submit_task

MANAGE = 'create_task'


class TaskViewSet(PermissionRequiredMixin, AuditLoggingMixin, viewsets.ModelViewSet):
    """
    /api/v1/tasks/tasks/
      create / edit / delete        need create_task
      POST {id}/start/              assignee only: Not Started or Rejected -> In Progress
      POST {id}/submit/             assignee only: In Progress -> Submitted
    Who sees what: users with create_task see every task of the company; everyone else
    sees only tasks assigned to them or created by them.
    """
    serializer_class = TaskSerializer

    permission_required = {
        'create': MANAGE,
        'update': MANAGE,
        'partial_update': MANAGE,
        'destroy': MANAGE,
    }

    def get_queryset(self):
        employee = self.request.user.employee
        qs = Task.objects.filter(company=employee.company).select_related(
            'assigned_to__user', 'assigned_by__user'
        )
        if not employee.has_permission(MANAGE):
            qs = qs.filter(Q(assigned_to=employee) | Q(assigned_by=employee))
        return qs

    def perform_create(self, serializer):
        employee = self.request.user.employee
        instance = serializer.save(company=employee.company, assigned_by=employee)
        self._log('CREATE', instance)

    def _assignee_action(self, request, service):
        task = self.get_object()
        try:
            service(task, request.user.employee)
        except NotTheAssignee as exc:
            raise PermissionDenied(str(exc))
        except TaskError as exc:
            raise ValidationError(str(exc))
        self._log('UPDATE', task)
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        return self._assignee_action(request, start_task)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        return self._assignee_action(request, submit_task)
