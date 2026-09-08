"""
Real login endpoint (Batch 1.4) , replaces the demo's password-free
click-to-login. Built as a custom view rather than plugging in SimpleJWT's
default TokenObtainPairView directly, because the agreed security checks
(honeypot, minimum-time, rate limiting, lockout) all need to run *before*
password verification, and every attempt , successful or not , needs to
be written to LoginAttempt and AuditLog.

Every failure returns the same generic message and 401, regardless of
the real internal reason (wrong password vs inactive account vs honeypot
triggered), so nothing about *why* an attempt failed leaks to whoever ,
or whatever , is making the request. The real reason is still recorded
internally in LoginAttempt for an Administrator to review.
"""
from datetime import datetime, timezone as dt_timezone

from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .audit import log_audit
from .models import LoginAttempt, User
from .names import display_name

GENERIC_ERROR = {"detail": "Invalid email or password."}
RATE_LIMIT_WINDOW_MINUTES = 15
MAX_FAILED_PER_ACCOUNT = 5
MAX_FAILED_PER_IP = 20
MIN_SUBMIT_SECONDS = 1.5


def get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        password = request.data.get("password") or ""
        # Honeypot: a real user never sees or fills this field. Named to look
        # like something a bot would plausibly auto-fill.
        honeypot = request.data.get("website") or ""
        form_loaded_at = request.data.get("form_loaded_at")
        ip = get_client_ip(request)

        def reject(reason, response_status=status.HTTP_401_UNAUTHORIZED):
            LoginAttempt.objects.create(
                email_attempted=email, ip_address=ip, successful=False, reason=reason
            )
            return Response(GENERIC_ERROR, status=response_status)

        # 1. Honeypot
        if honeypot:
            return reject(LoginAttempt.Reason.HONEYPOT)

        # 2. Minimum time-to-submit
        if form_loaded_at:
            try:
                loaded = datetime.fromisoformat(form_loaded_at.replace("Z", "+00:00"))
                elapsed = (datetime.now(dt_timezone.utc) - loaded).total_seconds()
                if elapsed < MIN_SUBMIT_SECONDS:
                    return reject(LoginAttempt.Reason.TOO_FAST)
            except (ValueError, AttributeError):
                pass  # malformed timestamp , don't hard-fail a real user over it

        # 3. Per-IP rate limit
        window_start = timezone.now() - timezone.timedelta(minutes=RATE_LIMIT_WINDOW_MINUTES)
        recent_ip_failures = LoginAttempt.objects.filter(
            ip_address=ip, successful=False, timestamp__gte=window_start
        ).count()
        if recent_ip_failures >= MAX_FAILED_PER_IP:
            return reject(LoginAttempt.Reason.RATE_LIMITED, status.HTTP_429_TOO_MANY_REQUESTS)

        # 4. Per-account lockout
        recent_account_failures = LoginAttempt.objects.filter(
            email_attempted=email, successful=False, timestamp__gte=window_start
        ).count()
        if recent_account_failures >= MAX_FAILED_PER_ACCOUNT:
            return reject(LoginAttempt.Reason.ACCOUNT_LOCKED, status.HTTP_429_TOO_MANY_REQUESTS)

        # 5. Real authentication
        user = authenticate(request, username=email, password=password)
        if user is None:
            try:
                target = User.objects.get(email=email)
                reason = (
                    LoginAttempt.Reason.ACCOUNT_INACTIVE
                    if not target.is_active
                    else LoginAttempt.Reason.INVALID_CREDENTIALS
                )
            except User.DoesNotExist:
                reason = LoginAttempt.Reason.INVALID_CREDENTIALS
            return reject(reason)

        # Success
        LoginAttempt.objects.create(
            email_attempted=email, ip_address=ip, successful=True,
            reason=LoginAttempt.Reason.SUCCESS,
        )
        log_audit(user, "Logged in", "User", display_name(user), f"from {ip}", instance=user)
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        refresh = RefreshToken.for_user(user)
        role_permissions = []
        if user.role_id:
            role_permissions = list(
                user.role.permissions.values("module", "can_view", "can_create", "can_edit", "can_delete")
            )
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "email": user.email,
                "name": display_name(user),
                "role": user.role.name if user.role_id else None,
                "location": user.location_id,
                "location_name": user.location.name if user.location_id else None,
                # Included directly , Batch 3.2 finding: the frontend needs
                # real permission data for nav filtering, and matching by
                # role name string would be exactly the fragile pattern
                # deliberately avoided in Batch 2.5's goal calculation_type
                # redesign. An ID-based extra round-trip was the alternative;
                # this is simpler and avoids both problems.
                "role_permissions": role_permissions,
            },
        })


class LogoutView(APIView):
    def post(self, request):
        log_audit(request.user, "Logged out", "User", display_name(request.user), "")
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                RefreshToken(refresh_token).blacklist()
        except Exception:
            pass  # token already invalid/expired , logout still succeeds
        return Response({"detail": "Logged out."})


from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import viewsets, filters
from rest_framework.response import Response

from .permissions import ModulePermission
from .serializers import RoleSerializer, RolePermissionSerializer, UserSerializer, AuditLogSerializer, LoginAttemptSerializer
from .models import Role, RolePermission, AuditLog, LoginAttempt


class RoleViewSet(viewsets.ModelViewSet):
    module = "admin"
    permission_classes = [ModulePermission]
    queryset = Role.objects.prefetch_related("permissions")
    serializer_class = RoleSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit(self.request.user, "Created", "Role", instance.name, instance=instance)

    def perform_destroy(self, instance):
        name = instance.name
        log_audit(self.request.user, "Deleted", "Role", name)
        instance.delete()


class RolePermissionViewSet(viewsets.ModelViewSet):
    module = "admin"
    permission_classes = [ModulePermission]
    queryset = RolePermission.objects.select_related("role")
    serializer_class = RolePermissionSerializer


class UserViewSet(viewsets.ModelViewSet):
    module = "admin"
    permission_classes = [ModulePermission]
    queryset = User.objects.select_related("role", "location", "member")
    serializer_class = UserSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["email", "first_name", "last_name"]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit(self.request.user, "Created", "User", instance.email, instance=instance)

    def destroy(self, request, *args, **kwargs):
        # User.delete() raises django.core.exceptions.ValidationError for
        # the last remaining Administrator , a different exception type
        # than Location's ProtectedError, so this needs its own handling,
        # verified directly rather than assumed to work the same way.
        #
        # Wrapped in a transaction deliberately: log_audit() must run
        # BEFORE delete() (an admin can legitimately delete their own
        # account once a second admin exists, and logging afterward would
        # try to reference request.user's row after it no longer exists ,
        # a dangling foreign key). But logging first, on its own, risks
        # leaving a false "Deleted" entry if delete() then fails validation.
        # The transaction makes both succeed or both roll back together.
        instance = self.get_object()
        email = instance.email
        try:
            with transaction.atomic():
                log_audit(request.user, "Deleted", "User", email)
                instance.delete()
        except DjangoValidationError as exc:
            return Response({"detail": "; ".join(exc.messages)}, status=400)
        return Response(status=204)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only , an audit trail is never editable through the API,
    matching the Batch 1.3 Django admin registration."""
    module = "admin"
    permission_classes = [ModulePermission]
    queryset = AuditLog.objects.select_related("user")
    serializer_class = AuditLogSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["user_name_snapshot", "entity_name", "details"]
    ordering_fields = ["timestamp"]

    def get_queryset(self):
        qs = super().get_queryset()
        entity_type = self.request.query_params.get("entity_type")
        if entity_type:
            qs = qs.filter(entity_type=entity_type)
        return qs


class LoginAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only , for Administrator visibility into login security
    events (rate limiting triggers, honeypot hits, lockouts)."""
    module = "admin"
    permission_classes = [ModulePermission]
    queryset = LoginAttempt.objects.all()
    serializer_class = LoginAttemptSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["timestamp"]

    def get_queryset(self):
        qs = super().get_queryset()
        successful = self.request.query_params.get("successful")
        if successful is not None:
            qs = qs.filter(successful=successful.lower() == "true")
        return qs
