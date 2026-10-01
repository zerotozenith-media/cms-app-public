"""
URL configuration for the DCLM Bahrain CMS backend.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView

from core.views import health_check
from accounts.views import LoginView, LogoutView
from accounts.password_reset import PasswordResetRequestView, PasswordResetConfirmView
from accounts.profile import MeView, MyPhotoView, MyPasswordView
from core.outstanding import NotificationSummaryView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path("api/auth/logout/", LogoutView.as_view(), name="logout"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/auth/password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("api/auth/password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("api/auth/me/", MeView.as_view(), name="me"),
    path("api/auth/me/photo/", MyPhotoView.as_view(), name="my-photo"),
    path("api/auth/me/password/", MyPasswordView.as_view(), name="my-password"),
    path("api/notifications/", NotificationSummaryView.as_view(), name="notifications"),
    path("api/", include("members.urls")),
    path("api/", include("attendance.urls")),
    path("api/", include("newcomers.urls")),
    path("api/", include("enquiries.urls")),
    path("api/", include("finance.urls")),
    path("api/", include("goals.urls")),
    path("api/", include("reports.urls")),
    path("api/", include("followup.urls")),
    path("api/", include("service.urls")),
    path("api/", include("accounts.urls")),
    path("api/", include("core.urls")),
]

# Serves uploaded files (receipts, report PDFs) back through the local
# dev server when using local filesystem storage. Guarded by DEBUG, so
# this is a genuine no-op in production , Azure Blob (Batch 2.8) serves
# files directly there, Django never needs to. Found this was missing
# while testing a real receipt upload in Batch 3.7: the file uploaded
# and saved correctly, but clicking "View" 404'd, since nothing was
# actually serving it back locally.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
