from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from .serializers import CompanyRegisterSerializer, CustomTokenObtainPairSerializer


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

    def get(self, request):
        user = request.user
        employee = getattr(user, 'employee', None)

        data = {
            "email": user.email,
            "company_id": str(user.company_id) if user.company_id else None,
            "company_name": user.company.name if user.company_id else None,
        }

        if employee:
            data.update({
                "employee_id": str(employee.id),
                "employee_code": employee.employee_code,
                "designation_title": employee.designation.title if employee.designation_id else None,
                "department_name": employee.department.name if employee.department_id else None,
                "permissions": [],  # RBAC not yet built for this scope — Sprint 2+ (ST-108/109/110)
            })

        return Response({"success": True, "data": data})