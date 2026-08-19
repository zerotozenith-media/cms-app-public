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

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path("api/auth/logout/", LogoutView.as_view(), name="logout"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/", include("members.urls")),
    path("api/", include("attendance.urls")),
    path("api/", include("newcomers.urls")),
    path("api/", include("finance.urls")),
    path("api/", include("goals.urls")),
    path("api/", include("reports.urls")),
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
