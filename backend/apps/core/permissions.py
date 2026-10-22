from rest_framework.permissions import BasePermission


def _password_change_required():
    # Imported here: core.exceptions imports DRF views, which import this module through the settings.
    from .exceptions import OrdinisException

    class PasswordChangeRequired(OrdinisException):
        code = "PASSWORD_CHANGE_REQUIRED"
        message = "You are using a temporary password. Set your own password before you continue."
        status_code = 403

    return PasswordChangeRequired()


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
        if not company.is_active:
            return False
        # The temporary-password gate. A view that every person needs in order to set a password
        # (profile, change-password) opts out with `allow_when_password_change_required = True`.
        if request.user.must_change_password and not getattr(view, 'allow_when_password_change_required', False):
            raise _password_change_required()
        return True


class IsPlatformAdmin(BasePermission):
    """Only Platform Admin accounts (company-less, set up with the create_platform_admin command)."""
    message = 'Platform Admin access only.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and user.is_platform_admin)


class IsCompanyUserOrPlatformAdmin(BasePermission):
    """For the few endpoints that belong to every person, the Platform Admin included (the profile)."""
    message = "This company's account is currently suspended."

    def has_permission(self, request, view):
        user = request.user
        if user and user.is_authenticated and user.is_platform_admin and user.is_active:
            return True
        return IsCompanyActive().has_permission(request, view)


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