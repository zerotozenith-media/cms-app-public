from django.urls import path

from . import views

urlpatterns = [
    path("service/me/", views.MeView.as_view(), name="service-me"),
    path("service/me/dismiss/", views.DismissNoteView.as_view(), name="service-dismiss"),
    path("service/team/", views.TeamView.as_view(), name="service-team"),
]
