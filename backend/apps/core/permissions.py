from rest_framework.permissions import BasePermission


class IsCompanyActive(BasePermission):
    """
    Blocks access if the authenticated user's company has been suspended.
    Required in every API view's permission_classes -- this is the JWT/API
    equivalent of TenantIsolationMiddleware (which only covers session auth).
    """
    message = "This company's account is currently suspended."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        company = getattr(request.user, 'company', None)
        if company is None:
            return False
        return company.is_active


class HasPermission(BasePermission):
    """
    Checks whether the logged-in user's Employee has a specific
    permission codename, via any of their assigned Roles.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        required_permission = None

        if hasattr(view, "get_required_permission"):
            required_permission = view.get_required_permission()
        else:
            required_permission = getattr(
                view,
                "required_permission",
                None,
            )

      
        if not required_permission:
            return True

        employee = getattr(request.user, "employee", None)

        if not employee:
            return False

        return employee.has_permission(required_permission)


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