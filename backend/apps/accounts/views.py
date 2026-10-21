from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import status
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsCompanyUserOrPlatformAdmin
from .serializers import CompanyRegisterSerializer, CustomTokenObtainPairSerializer, ProfileUpdateSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    

class CompanyRegisterView(APIView):
    """
    POST /api/v1/auth/register/
    Public endpoint (no auth required) -- this is how a brand new
    client onboards: one call creates their Company + CEO account,
    and immediately returns a JWT so they land logged-in.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CompanyRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        token_serializer = CustomTokenObtainPairSerializer()
        token = token_serializer.get_token(result["user"])

        return Response({
            "success": True,
            "data": {
                "company_id": str(result["company"].id),
                "employee_id": str(result["employee"].id),
                "access": str(token.access_token),
                "refresh": str(token),
            },
            "message": "Company registered successfully.",
        }, status=status.HTTP_201_CREATED)


class MeView(APIView):
    """
    GET /api/v1/auth/me/
    Returns the logged-in user's own identity: email, company,
    employee record, designation, and permission codenames —
    everything the frontend needs to render the right dashboard
    and show/hide the right menu items.
    """
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _plan_name(company):
        if company is None:
            return None
        from billing.services import get_subscription
        return get_subscription(company).plan.name

    def get(self, request):
        user = request.user
        company = user.company
        employee = getattr(user, 'employee', None)

        data = {
            "email": user.email,
            "full_name": user.full_name,
            "company_id": str(company.id) if company else None,
            "company_name": company.name if company else None,
            "plan_name": self._plan_name(company),
            "permissions": [],
            "is_platform_admin": user.is_platform_admin,
        }

        if employee:
            codenames = employee.employee_roles.values_list(
                'role__permissions__codename', flat=True
            ).distinct()
            data.update({
                "employee_id": str(employee.id),
                "employee_code": employee.employee_code,
                "designation_title": employee.designation.title if employee.designation_id else None,
                "department_name": employee.department.name if employee.department_id else None,
                "permissions": sorted(c for c in codenames if c),
            })

        return Response({"success": True, "data": data})


class ProfileView(APIView):
    """
    GET / PATCH /api/v1/auth/profile/
    The logged-in person's own details (the Platform Admin included). Only a short whitelist can be
    changed here: full name, phone, address and the emergency contact. The login email, department,
    designation, manager, Roles and salary can never be changed through this endpoint.
    """
    permission_classes = [IsAuthenticated, IsCompanyUserOrPlatformAdmin]

    @staticmethod
    def payload(user):
        employee = getattr(user, 'employee', None)
        data = {
            'email': user.email,
            'full_name': user.full_name,
            'is_platform_admin': user.is_platform_admin,
            'company_name': user.company.name if user.company_id else None,
            'employee_id': None, 'employee_code': None, 'designation_title': None, 'department_name': None,
            'manager_name': None, 'joined_on': None,
            'phone': None, 'address': None, 'emergency_contact_name': None, 'emergency_contact_phone': None,
        }
        if employee:
            manager = employee.reports_to
            data.update({
                'employee_id': str(employee.id),
                'employee_code': employee.employee_code,
                'designation_title': employee.designation.title if employee.designation_id else None,
                'department_name': employee.department.name if employee.department_id else None,
                'manager_name': (manager.user.display_name if manager else None),
                'joined_on': employee.joined_on,
                'phone': employee.phone,
                'address': employee.address,
                'emergency_contact_name': employee.emergency_contact_name,
                'emergency_contact_phone': employee.emergency_contact_phone,
            })
        return data

    def get(self, request):
        return Response({"success": True, "data": self.payload(request.user)})

    @transaction.atomic
    def patch(self, request):
        serializer = ProfileUpdateSerializer(data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        user = request.user
        if 'full_name' in values:
            user.full_name = values['full_name']
            user.save(update_fields=['full_name', 'updated_at'])
        employee = getattr(user, 'employee', None)
        if employee is not None:
            changed = [key for key in ProfileUpdateSerializer.EMPLOYEE_FIELDS if key in values]
            for key in changed:
                setattr(employee, key, values[key])
            if changed:
                employee.save(update_fields=changed + ['updated_at'])
        return Response({"success": True, "data": self.payload(user), "message": "Profile updated."})
