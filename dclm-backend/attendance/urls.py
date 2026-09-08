from rest_framework.routers import DefaultRouter

from .views import FellowshipViewSet, MeetingTypeViewSet, AttendanceSessionViewSet

router = DefaultRouter()
router.register("meeting-types", MeetingTypeViewSet, basename="meeting-type")
router.register(r"fellowships", FellowshipViewSet, basename="fellowship")
router.register("attendance-sessions", AttendanceSessionViewSet, basename="attendance-session")

urlpatterns = router.urls
