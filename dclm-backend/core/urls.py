from django.urls import path

from .tasks_api import run_scheduled_task
from rest_framework.routers import DefaultRouter

from .views import LocationViewSet, AppSettingsView
from .dashboard import DashboardSummaryView

router = DefaultRouter()
router.register("locations", LocationViewSet, basename="location")

urlpatterns = router.urls + [
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("settings/", AppSettingsView.as_view(), name="app-settings"),
]

urlpatterns = urlpatterns + [path("tasks/run/", run_scheduled_task, name="run-scheduled-task")]
