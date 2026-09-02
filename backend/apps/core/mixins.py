from rest_framework.response import Response


class StandardResponseMixin:
    """
    Ensures every successful response follows the same envelope:
    { success, data, message }
    """

    def success_response(self, data=None, message="Success", status_code=200):
        return Response(
            {"success": True, "data": data, "message": message},
            status=status_code,
        )


class AuditLoggingMixin:
    """
    Mixin for DRF ViewSets: automatically logs create/update/destroy
    actions to AuditLog, tagged with the acting employee, the model
    name, and the affected object's id. Runs inside DRF's own request
    cycle, so request.user is correctly resolved via JWT.

    Add to any ViewSet:
        class TaskViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
            ...
    """

    def perform_create(self, serializer):
        instance = serializer.save()
        self._log('CREATE', instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self._log('UPDATE', instance)

    def perform_destroy(self, instance):
        self._log('DELETE', instance)
        instance.delete()

    def _log(self, action, instance):
        employee = getattr(self.request.user, 'employee', None)
        if not employee:
            return

        from audit_log.models import AuditLog
        AuditLog.objects.create(
            actor=employee,
            action=action,
            model_name=instance.__class__.__name__,
            object_id=getattr(instance, 'id', None),
            ip_address=self._get_client_ip(),
        )

    def _get_client_ip(self):
        forwarded = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return self.request.META.get('REMOTE_ADDR')