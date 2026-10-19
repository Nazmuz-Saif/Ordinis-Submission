from rest_framework.routers import DefaultRouter

from .views import OverviewViewSet, SnapshotViewSet

router = DefaultRouter()
router.register('overview', OverviewViewSet, basename='analytics-overview')
router.register('snapshots', SnapshotViewSet, basename='analytics-snapshot')
urlpatterns = router.urls
