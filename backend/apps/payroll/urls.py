from django.urls import path

from .views import SalaryStructureViewSet

urlpatterns = [
    path(
        'salary-structures/',
        SalaryStructureViewSet.as_view({
            'get': 'list',
            'post': 'create',
        }),
        name='salary-structure-list',
    ),
    path(
        'salary-structures/<int:pk>/',
        SalaryStructureViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy',
        }),
        name='salary-structure-detail',
    ),
]