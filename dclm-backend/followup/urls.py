from django.urls import path

from . import views

urlpatterns = [
    path("followup/today/", views.TodayView.as_view(), name="followup-today"),
    path("followup/person/", views.PersonView.as_view(), name="followup-person"),
    path("followup/start/", views.StartView.as_view(), name="followup-start"),
    path("followup/enrolments/<int:pk>/record/", views.RecordView.as_view(), name="followup-record"),
    path("followup/enrolments/<int:pk>/<str:action>/", views.EnrolmentActionView.as_view(), name="followup-action"),
    path("followup/bank/", views.BankView.as_view(), name="followup-bank"),
    path("followup/bank/<int:pk>/", views.BankItemView.as_view(), name="followup-bank-item"),
    path("followup/saved/", views.SavedView.as_view(), name="followup-saved"),
    path("followup/saved/<int:pk>/", views.SavedView.as_view(), name="followup-saved-item"),
]
