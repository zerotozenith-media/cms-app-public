from django.urls import path

from .views import AnnouncementView, KeyView, NoticesView, SettingsView, SubscribeView, TestView, UnsubscribeView

urlpatterns = [
    path("alerts/key/", KeyView.as_view(), name="alerts-key"),
    path("alerts/subscribe/", SubscribeView.as_view(), name="alerts-subscribe"),
    path("alerts/unsubscribe/", UnsubscribeView.as_view(), name="alerts-unsubscribe"),
    path("alerts/settings/", SettingsView.as_view(), name="alerts-settings"),
    path("alerts/test/", TestView.as_view(), name="alerts-test"),
    path("alerts/announcements/", AnnouncementView.as_view(), name="alerts-announcements"),
    path("alerts/notices/", NoticesView.as_view(), name="alerts-notices"),
]
