from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    NewcomerSourceViewSet, MilestoneTypeViewSet, FollowUpUrgencySettingViewSet,
    NewcomerViewSet, NewcomerTaskViewSet, NewcomerStatusHistoryViewSet,
    public_newcomer_registration,
)

router = DefaultRouter()
router.register("newcomer-sources", NewcomerSourceViewSet, basename="newcomer-source")
router.register("milestone-types", MilestoneTypeViewSet, basename="milestone-type")
router.register("follow-up-urgency-settings", FollowUpUrgencySettingViewSet, basename="follow-up-urgency-setting")
router.register("newcomers", NewcomerViewSet, basename="newcomer")
router.register("newcomer-tasks", NewcomerTaskViewSet, basename="newcomer-task")
router.register("newcomer-status-history", NewcomerStatusHistoryViewSet, basename="newcomer-status-history")

urlpatterns = router.urls + [
    path("public/newcomer-registration/", public_newcomer_registration, name="public-newcomer-registration"),
]
