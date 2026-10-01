from django.urls import path
from . import views
from rest_framework.routers import DefaultRouter

from .roster import AttendanceRosterView, FinanceRosterView

from .views import FellowshipViewSet, MeetingTypeViewSet, AttendanceSessionViewSet

router = DefaultRouter()
router.register("meeting-types", MeetingTypeViewSet, basename="meeting-type")
router.register(r"fellowships", FellowshipViewSet, basename="fellowship")
router.register("attendance-sessions", AttendanceSessionViewSet, basename="attendance-session")

urlpatterns = router.urls + [
    path("public/meetings/", views.public_meetings, name="public-meetings"),
    path("attendance-roster/", AttendanceRosterView.as_view(), name="attendance-roster"),
    path("finance-roster/", FinanceRosterView.as_view(), name="finance-roster"),
]
