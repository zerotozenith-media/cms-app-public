from rest_framework.routers import DefaultRouter

from .views import (
    EnquirySourceViewSet, CampaignViewSet, EnquiryViewSet, EnquiryTaskViewSet,
    EnquiryStatusHistoryViewSet,
)

router = DefaultRouter()
router.register("enquiry-sources", EnquirySourceViewSet, basename="enquiry-source")
router.register("campaigns", CampaignViewSet, basename="campaign")
router.register("enquiries", EnquiryViewSet, basename="enquiry")
router.register("enquiry-tasks", EnquiryTaskViewSet, basename="enquiry-task")
router.register("enquiry-status-history", EnquiryStatusHistoryViewSet, basename="enquiry-status-history")

urlpatterns = router.urls
