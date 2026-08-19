from rest_framework.routers import DefaultRouter

from .views import RoleViewSet, RolePermissionViewSet, UserViewSet, AuditLogViewSet, LoginAttemptViewSet

router = DefaultRouter()
router.register("roles", RoleViewSet, basename="role")
router.register("role-permissions", RolePermissionViewSet, basename="role-permission")
router.register("users", UserViewSet, basename="user")
router.register("audit-log", AuditLogViewSet, basename="audit-log")
router.register("login-attempts", LoginAttemptViewSet, basename="login-attempt")

urlpatterns = router.urls
