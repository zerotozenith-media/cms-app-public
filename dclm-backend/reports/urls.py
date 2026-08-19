from rest_framework.routers import DefaultRouter

from .views import ServiceViewSet, DepartmentViewSet, TestimonyViewSet, WeeklyNoteViewSet, ReportViewSet

router = DefaultRouter()
router.register("services", ServiceViewSet, basename="service")
router.register("departments", DepartmentViewSet, basename="department")
router.register("testimonies", TestimonyViewSet, basename="testimony")
router.register("weekly-notes", WeeklyNoteViewSet, basename="weekly-note")
router.register("reports", ReportViewSet, basename="report")

urlpatterns = router.urls
