from django.urls import path

from .tasks_api import run_scheduled_task
from rest_framework.routers import DefaultRouter

from .views import LocationViewSet, AppSettingsView, FollowUpRulesView
from .dashboard import DashboardSummaryView

router = DefaultRouter()
router.register("locations", LocationViewSet, basename="location")

urlpatterns = router.urls + [
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("settings/", AppSettingsView.as_view(), name="app-settings"),
    path("followup-rules/", FollowUpRulesView.as_view(), name="followup-rules"),
]

urlpatterns = urlpatterns + [path("tasks/run/", run_scheduled_task, name="run-scheduled-task")]

from .help_views import HelpContactsView, HelpImageView, ManualView  # noqa: E402
from .followup_views import (AccessView, EligibleView, ReasonsView, MyFollowUpView, ReviewDecideView, ReviewListView,  # noqa: E402
                             ReviewOverviewView, ShepherdPeopleView)

urlpatterns = urlpatterns + [
    path("followup/access/", AccessView.as_view(), name="followup-access"),
    path("help/manual/", ManualView.as_view(), name="help-manual"),
    path("help/img/<str:name>/", HelpImageView.as_view(), name="help-image"),
    path("help/contacts/", HelpContactsView.as_view(), name="help-contacts"),
    path("followup/my/", MyFollowUpView.as_view(), name="followup-my"),
    path("followup/reasons/", ReasonsView.as_view(), name="followup-reasons"),
    path("followup/review/", ReviewListView.as_view(), name="followup-review"),
    path("followup/review/decide/", ReviewDecideView.as_view(), name="followup-review-decide"),
    path("followup/review/overview/", ReviewOverviewView.as_view(), name="followup-review-overview"),
    path("followup/review/shepherd/<int:pk>/", ShepherdPeopleView.as_view(), name="followup-review-shepherd"),
    path("followup/review/eligible/", EligibleView.as_view(), name="followup-review-eligible"),
]
