from rest_framework.routers import DefaultRouter

from django.urls import path
from .views import (
    HouseholdViewSet, MemberViewSet, MemberCategoryHistoryViewSet, MemberFollowUpTaskViewSet,
    ShepherdAssignmentView, BulkAssignShepherdView, EligibleShepherdsView,
)

router = DefaultRouter()
router.register("households", HouseholdViewSet, basename="household")
router.register("members", MemberViewSet, basename="member")
router.register("member-category-history", MemberCategoryHistoryViewSet, basename="member-category-history")
router.register("member-followup-tasks", MemberFollowUpTaskViewSet, basename="member-followup-task")

# These must come BEFORE router.urls. The router registers
# members/<pk>/ , which would otherwise swallow "assign-shepherds" as a
# primary key and return 404/405 instead of reaching these views.
urlpatterns = [
    path("members/assign-shepherds/", ShepherdAssignmentView.as_view(), name="assign-shepherds"),
    path("members/bulk-assign-shepherd/", BulkAssignShepherdView.as_view(), name="bulk-assign-shepherd"),
    path("members/eligible-shepherds/", EligibleShepherdsView.as_view(), name="eligible-shepherds"),
] + router.urls
