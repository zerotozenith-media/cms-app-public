from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import monthly_spreadsheet, ServiceViewSet, DepartmentViewSet, TestimonyViewSet, WeeklyNoteViewSet, ReportViewSet

router = DefaultRouter()
router.register("services", ServiceViewSet, basename="service")
router.register("departments", DepartmentViewSet, basename="department")
router.register("testimonies", TestimonyViewSet, basename="testimony")
router.register("weekly-notes", WeeklyNoteViewSet, basename="weekly-note")
router.register("reports", ReportViewSet, basename="report")

urlpatterns = [
    # Declared before the router: its reports/<pk>/ route would otherwise
    # match "spreadsheet" as a report id and return 404.
    path("reports/spreadsheet/", monthly_spreadsheet, name="monthly-spreadsheet"),
] + router.urls
