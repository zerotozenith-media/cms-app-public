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
LOCKED_ERROR = {"detail": f"Too many attempts. Try again in {RATE_LIMIT_WINDOW_MINUTES} minutes."}
MAX_FAILED_PER_ACCOUNT = 5
MAX_FAILED_PER_IP = 20
MIN_SUBMIT_SECONDS = 1.5


def get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR", "0.0.0.0")

    # Azure's proxy can pass "ip:port" for IPv4 clients rather than a bare
    # IP. ip_address is a Postgres inet column and rejects the port, so
    # strip it here. Only strip when there's exactly one colon — IPv6
    # addresses have several and must be left alone.
    if ip.count(":") == 1:
        ip = ip.split(":")[0]

    return ip


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
            # A locked account says so. Repeating "Invalid email or password"
            # even for the right password made people think they were
            # mistyping. The lock counts attempts per email typed, whether or
            # not an account exists, so this reveals nothing about which
            # addresses are real.
            if response_status == status.HTTP_429_TOO_MANY_REQUESTS:
                return Response(LOCKED_ERROR, status=response_status)
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
            response = reject(reason)
            # Warn on the attempt before the lock. The count is per email
            # typed, whether or not an account exists, so this reveals
            # nothing about which addresses are real.
            if recent_account_failures + 1 == MAX_FAILED_PER_ACCOUNT - 1:
                response.data = {
                    "detail": f"Invalid email or password. One more wrong attempt will lock sign-in "
                              f"for {RATE_LIMIT_WINDOW_MINUTES} minutes. Use Forgotten your password? "
                              f"if you need a new one.",
                    "warning": True,
                }
            # The attempt that locks sign-in says so at once, rather than on
            # the next try.
            elif recent_account_failures + 1 >= MAX_FAILED_PER_ACCOUNT:
                response.data = dict(LOCKED_ERROR)
            return response

        # Success
        LoginAttempt.objects.create(
            email_attempted=email, ip_address=ip, successful=True,
            reason=LoginAttempt.Reason.SUCCESS,
        )
        log_audit(user, "Logged in", "User", display_name(user), f"from {ip}", instance=user)
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        return Response(signed_in_payload(user))


def signed_in_payload(user):
    """What a successful sign-in returns. Shared with the password reset,
    which signs the person straight in once their new password is saved."""
    refresh = RefreshToken.for_user(user)
    role_permissions = []
    if user.role_id:
        role_permissions = list(
            user.role.permissions.values("module", "can_view", "can_create", "can_edit", "can_delete")
        )
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": {
            "id": user.id,
            "email": user.email,
            "name": display_name(user),
            "role": user.role.name if user.role_id else None,
            "location": user.location_id,
            "location_name": user.location.name if user.location_id else None,
            "photo": user.photo.url if user.photo else None,
            "role_permissions": role_permissions,
        },
    }


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
from rest_framework.decorators import action
from rest_framework.response import Response

from .permissions import ModulePermission
from .serializers import RoleSerializer, RolePermissionSerializer, UserSerializer, AuditLogSerializer, LoginAttemptSerializer
from .models import Role, RolePermission, AuditLog, LoginAttempt


class RoleViewSet(viewsets.ModelViewSet):
    # Affects every location, so only an administrator covering every
    # location may change it. See ModulePermission.
    church_wide = True
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
    # Affects every location, so only an administrator covering every
    # location may change it. See ModulePermission.
    church_wide = True
    module = "admin"
    permission_classes = [ModulePermission]
    queryset = RolePermission.objects.select_related("role")
    serializer_class = RolePermissionSerializer

    # Review item A2: unticking Admin on the Administrator role locked
    # everyone out of roles for good. A change that leaves no full
    # administrator is refused.
    def _guarded(self, fn):
        from rest_framework.exceptions import ValidationError
        with transaction.atomic():
            result = fn()
            if not any_full_administrator():
                raise ValidationError({"detail": "This would leave no active account that covers All locations "
                                                 "with full Admin rights, and nobody could undo it. Keep Admin "
                                                 "fully ticked for at least one such account's role."})
        return result

    def perform_update(self, serializer):
        self._guarded(serializer.save)
        log_audit(self.request.user, "Changed permissions", "Role", serializer.instance.role.name,
                  serializer.instance.module)

    def perform_create(self, serializer):
        self._guarded(serializer.save)

    def perform_destroy(self, instance):
        self._guarded(instance.delete)


def any_full_administrator():
    """Whether at least one active account covers All locations with every
    Admin permission."""
    for u in User.objects.filter(is_active=True, location__isnull=True).select_related("role"):
        if u.is_superuser or is_full_administrator(u):
            return True
    return False


PERMISSION_FLAGS = ("can_view", "can_create", "can_edit", "can_delete")


def is_full_administrator(actor):
    """An all-locations account with every Admin permission. That is what an
    administrator is, and they may assign any role."""
    if actor.location_id or not actor.role_id:
        return False
    p = actor.role.permissions.filter(module="admin").first()
    return bool(p and all(getattr(p, f) for f in PERMISSION_FLAGS))


def role_within(actor, role):
    """Whether every permission the role grants, the actor also has."""
    if actor.is_superuser:
        return True
    if not actor.role_id:
        return False
    own = {p.module: p for p in actor.role.permissions.all()}
    for p in role.permissions.all():
        mine = own.get(p.module)
        for flag in PERMISSION_FLAGS:
            if getattr(p, flag) and not (mine and getattr(mine, flag)):
                return False
    return True


class UserViewSet(viewsets.ModelViewSet):
    module = "admin"
    permission_classes = [ModulePermission]
    queryset = User.objects.select_related("role", "location", "member")
    serializer_class = UserSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["email", "first_name", "last_name"]

    # Somebody limited to one location manages only that location's
    # accounts. Before this, a Bahrain coordinator could list every account
    # and create a new Administrator covering every location, then sign in
    # as it and see everything.
    def get_queryset(self):
        qs = super().get_queryset()
        actor = self.request.user
        if not actor.is_superuser and actor.location_id:
            qs = qs.filter(location_id=actor.location_id)
        return qs

    def _check_within_reach(self, data, instance=None):
        from rest_framework.exceptions import PermissionDenied
        actor = self.request.user
        if actor.is_superuser or is_full_administrator(actor):
            return
        if actor.location_id:
            location = data.get("location", getattr(instance, "location", None))
            location_id = getattr(location, "id", location)
            if location_id != actor.location_id:
                raise PermissionDenied(
                    "You can only manage accounts for your own location.")
        role = data.get("role")
        if role is not None and not role_within(actor, role):
            raise PermissionDenied(
                f"The {role.name} role can do things your own role cannot, so you "
                f"cannot give it to anyone.")

    def perform_create(self, serializer):
        self._check_within_reach(serializer.validated_data)
        instance = serializer.save()
        log_audit(self.request.user, "Created", "User", instance.email, instance=instance)

    WATCHED = {"first_name": "first name", "last_name": "last name", "email": "email", "role": "role",
               "location": "location", "is_active": "switched on", "can_shepherd": "shepherd",
               "gender": "gender", "is_followup_coordinator": "Follow-up Coordinator",
               "coordinates_location": "coordinates follow-up for"}

    def perform_update(self, serializer):
        from rest_framework.exceptions import ValidationError
        self._check_within_reach(serializer.validated_data, serializer.instance)
        inst = serializer.instance
        before = {f: getattr(inst, f) for f in self.WATCHED}
        before_member = inst.member_id
        if inst.pk == self.request.user.pk and serializer.validated_data.get("is_active") is False:
            raise ValidationError({"is_active": "You cannot switch off your own account while signed in to it."})
        with transaction.atomic():
            instance = serializer.save()
            # Review item A2: nobody may leave the church without an account
            # that can manage everything; there is no other way back in.
            if not any_full_administrator():
                raise ValidationError({"detail": "This would leave no active account that covers All locations "
                                                 "with full Admin rights, and nobody could then manage roles or "
                                                 "accounts. Give another account those rights first."})
        if "member" in serializer.validated_data and instance.member_id != before_member:
            log_audit(self.request.user, "Linked member record", "User", instance.email,
                      instance.member.full_name if instance.member_id else "Not a member")
        changes = []
        for f, label in self.WATCHED.items():
            a, b = before[f], getattr(instance, f)
            if a != b:
                show = lambda v: ("All locations" if f in ("location", "coordinates_location") and v is None
                                  else ("yes" if v is True else "no" if v is False else str(v)))
                changes.append(f"{label}: {show(a)} to {show(b)}")
        if changes:
            log_audit(self.request.user, "Changed account", "User", instance.email, "; ".join(changes),
                      instance=instance)
        # Someone switched off or no longer shepherding hands their open
        # tasks on, never leaving them with nobody (Kay, 26 October 2026).
        if (before["is_active"] and not instance.is_active) or (before["can_shepherd"] and not instance.can_shepherd):
            from core.task_actions import release_tasks
            release_tasks(instance)

    @action(detail=True, methods=["post"], url_path="send-reset")
    def send_reset(self, request, pk=None):
        """Send this person a link to choose a new password (item 12)."""
        from rest_framework.exceptions import ValidationError
        from .password_reset import _send
        from .permissions import require
        require(request.user, ("admin", "can_edit"))
        user = self.get_object()
        self._check_within_reach({}, user)
        if not user.is_active:
            raise ValidationError({"detail": "This account is switched off. Switch it on first, then send the link."})
        _send(user)
        log_audit(request.user, "Sent password reset link", "User", user.email)
        return Response({"detail": f"A link to choose a new password was sent to {user.email}. It works once, "
                                   f"for one hour."})

    @action(detail=True, methods=["post"], url_path="add-to-roll")
    def add_to_roll(self, request, pk=None):
        """
        Item 12: an account that is not on the member roll is added to it,
        using the account's name, gender and location, and linked.
        """
        from rest_framework.exceptions import ValidationError
        from core.models import Location
        from members.models import Member
        from .permissions import require
        require(request.user, ("admin", "can_edit"), ("members", "can_create"))
        user = self.get_object()
        self._check_within_reach({}, user)
        if user.member_id:
            raise ValidationError({"detail": f"{display_name(user)} is already linked to a member record."})
        if not (user.first_name and user.last_name):
            raise ValidationError({"detail": "Give the account a first and last name first, so the member record "
                                             "has a name."})
        loc = user.location or Location.objects.filter(is_core=True).first()
        category = request.data.get("category") or Member.Category.GENERAL
        if category not in Member.Category.values:
            raise ValidationError({"category": "Choose a member category."})
        from django.utils import timezone
        m = Member.objects.create(first_name=user.first_name, surname=user.last_name, gender=user.gender or "",
                                  email=user.email, location=loc, joined_date=timezone.localdate(), category=category)
        user.member = m
        user.save(update_fields=["member"])
        log_audit(request.user, "Added to member roll", "User", user.email, f"{m.full_name}, {loc.name}", instance=m)
        return Response({"member": m.id, "member_name": m.full_name})

    @action(detail=False, methods=["get"], url_path="member-choices")
    def member_choices(self, request):
        """
        Members an account can be linked to, for Member record in Admin,
        Users. Someone limited to one location sees that location's members.
        """
        from members.models import Member
        qs = Member.objects.select_related("location").order_by("surname", "first_name")
        actor = request.user
        if not actor.is_superuser and actor.location_id:
            qs = qs.filter(location_id=actor.location_id)
        linked = dict(User.objects.exclude(member=None).values_list("member_id", "id"))
        return Response([{"id": m.id, "name": m.full_name, "location": m.location_id,
                          "location_name": m.location.name if m.location_id else "",
                          "linked_to": linked.get(m.id)} for m in qs])

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
        from django.db.models import ProtectedError
        instance = self.get_object()
        email = instance.email
        try:
            with transaction.atomic():
                log_audit(request.user, "Deleted", "User", email)
                instance.delete()
        except DjangoValidationError as exc:
            return Response({"detail": "; ".join(exc.messages)}, status=400)
        except ProtectedError as exc:
            # Review item A4: say what holds it and what to do instead.
            n = len(exc.protected_objects)
            kinds = sorted({o._meta.verbose_name_plural for o in exc.protected_objects})
            return Response({"detail": f"{display_name(instance)} produced {n} record(s) that keep their name "
                                       f"({', '.join(kinds)}), so the account cannot be deleted. Switch it off "
                                       f"instead: they can no longer sign in, and the records stay correct."},
                            status=400)
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
        # A location-limited account sees what that location's people did,
        # not every location's names and actions.
        actor = self.request.user
        if not actor.is_superuser and actor.location_id:
            qs = qs.filter(user__location_id=actor.location_id)
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
        actor = self.request.user
        if not actor.is_superuser and actor.location_id:
            emails = User.objects.filter(location_id=actor.location_id).values_list("email", flat=True)
            qs = qs.filter(email_attempted__in=list(emails))
        successful = self.request.query_params.get("successful")
        if successful is not None:
            qs = qs.filter(successful=successful.lower() == "true")
        return qs
