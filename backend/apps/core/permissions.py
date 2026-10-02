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
            # A user with no company can never act on any tenant's data.
            return False
        if getattr(request.user, 'employee', None) is None:
            # A login with no employee record (e.g. the employee was removed) has no access.
            return False
        return company.is_active


class HasPermission(BasePermission):
    """
    Real permission check. The view names the Permission codename it needs
    (via PermissionRequiredMixin.get_required_permission or a plain
    `required_permission` attribute). The request passes only if the user's
    Employee holds that codename through one of their Roles.
    If the view names no permission for this action (e.g. list/retrieve),
    being authenticated is enough.
    """
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        get_required = getattr(view, "get_required_permission", None)
        required = get_required() if callable(get_required) else getattr(view, "required_permission", None)
        if not required:
            return True

        employee = getattr(request.user, "employee", None)
        if employee is None:
            return False
        return employee.has_permission(required)


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