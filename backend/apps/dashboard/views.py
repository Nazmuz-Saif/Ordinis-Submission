from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsCompanyActive
from .services import build_summary


class DashboardSummaryView(APIView):
    """
    GET /api/v1/dashboard/summary/
    Returns only the sections the user's Permissions allow (see services.py).
    A section the user may not see is absent from the response, not just empty.
    """
    permission_classes = [IsCompanyActive]

    def get(self, request):
        return Response(build_summary(request.user.employee))
