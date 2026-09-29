from rest_framework.permissions import BasePermission


class IsCompanyActive(BasePermission):
    """
    Blocks access if the authenticated user's company has been suspended.
    """
    message = "This company's account is currently suspended."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        company = getattr(request.user, 'company', None)
        if company is None:
            return True
        return company.is_active


class HasPermission(BasePermission):
    """
    Permission check: Allows authenticated users/CEO full access.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True


class IsHierarchySuperior(BasePermission):
    """
    Object-level permission: allows access to an object only if the
    requesting employee is the object's own employee, OR is somewhere
    above them in the reporting hierarchy (organization.services logic).
    """

    def has_object_permission(self, request, view, obj):
        from organization.services import can_view_employee_data

        requester_employee = getattr(request.user, "employee", None)
        target_employee = getattr(obj, "employee", None)
        if target_employee is None and hasattr(obj, "reports_to"):
            target_employee = obj

        if not requester_employee or not target_employee:
            return False

        return can_view_employee_data(requester_employee, target_employee)