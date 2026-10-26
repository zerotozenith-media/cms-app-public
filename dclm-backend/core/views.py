from django.db import connection
from django.db.models import ProtectedError
from rest_framework import serializers, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.audit import log_audit
from accounts.permissions import ModulePermission, user_can_view_module
from .models import Location, AppSetting, FollowUpRules
from .serializers import LocationSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    Simple health-check endpoint, deliberately unauthenticated so
    Azure App Service (and anyone deploying this) can verify the app
    is up and the database connection actually works.
    """
    db_ok = True
    db_error = None
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception as exc:  # noqa: BLE001 - intentionally broad for a health check
        db_ok = False
        db_error = str(exc)

    return Response({
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "unreachable",
        "database_error": db_error,
    })


class LocationViewSet(viewsets.ModelViewSet):
    # Affects every location, so only an administrator covering every
    # location may change it. See ModulePermission.
    church_wide = True
    module = "admin"
    permission_classes = [ModulePermission]
    queryset = Location.objects.all()
    serializer_class = LocationSerializer

    def get_permissions(self):
        # Every screen shows location names, so anyone signed in may read
        # the list. Without this, anybody outside Admin saw the code
        # "bahrain" instead of Bahrain. Changes still need Admin.
        from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
        if self.request.method in SAFE_METHODS:
            return [IsAuthenticated()]
        return super().get_permissions()

    def perform_create(self, serializer):
        # A meeting held at every location is held at the new one too, so a
        # new location gets its Friday Worship without anyone remembering to
        # tick it. A meeting with none ticked already means every location;
        # one with every location ticked gets the new one added. Meetings
        # held at only some locations are left as they are.
        from django.db.models import Count
        from attendance.models import MeetingType
        n = Location.objects.count()
        everywhere = list(MeetingType.objects.annotate(k=Count("held_at")).filter(k=n)) if n else []
        instance = serializer.save()
        for mt in everywhere:
            mt.held_at.add(instance)
        log_audit(self.request.user, "Created", "Location", instance.name, instance=instance)

    def destroy(self, request, *args, **kwargs):
        # Location.delete() raises ProtectedError for the core (Bahrain)
        # location , caught here and turned into a clean 400, not left to
        # bubble up as an unhandled 500. Verified this needed explicit
        # handling rather than assumed DRF does it automatically.
        instance = self.get_object()
        # A5 (26 October 2026): an account at this location would quietly
        # become an All locations account, and a fellowship would meet
        # nowhere, so both are moved first.
        from accounts.models import User
        from attendance.models import Fellowship
        from accounts.names import display_name
        groups = [("account", [display_name(u) for u in User.objects.filter(location=instance)]),
                  ("house fellowship", list(Fellowship.objects.filter(location=instance).values_list("name", flat=True))),
                  ("Follow-up Coordinator", [display_name(u) for u in User.objects.filter(coordinates_location=instance).exclude(location=instance)])]
        parts = []
        for word, names in groups:
            if names:
                shown = ", ".join(names[:3]) + (f" and {len(names) - 3} more" if len(names) > 3 else "")
                parts.append(f"{len(names)} {word}{'s' if len(names) != 1 else ''} ({shown})")
        if parts:
            return Response({"detail": f"{instance.name} still has {'; '.join(parts)}. Move these to "
                                       f"another location in Admin first, then remove {instance.name}."},
                            status=400)
        try:
            name = instance.name
            instance.delete()
        except ProtectedError as exc:
            # The core location raises this with its own plain message. Any
            # other in use would otherwise show Django's technical wording.
            if getattr(instance, "is_core", False):
                return Response({"detail": str(exc.args[0] if exc.args else exc)}, status=400)
            n = len(exc.protected_objects)
            return Response({"detail": f"{name} still has {n} record{'s' if n != 1 else ''} "
                                       f"such as members, sessions or giving, so it cannot be "
                                       f"removed."}, status=400)
        log_audit(request.user, "Deleted", "Location", name)
        return Response(status=204)


class AppSettingsView(APIView):
    """
    Church-wide switches an administrator controls from the UI.

    Exposed as a flat object rather than a list of key/value rows,
    because the frontend wants `settings.auto_assign_newcomers`, not to
    hunt through an array. Reading is open to any authenticated user
    (the assignment screen needs to know the current state to label
    itself correctly), but only the admin module can change anything.
    """
    # Affects every location, so only an administrator covering every
    # location may change it. See ModulePermission.
    church_wide = True
    permission_classes = [IsAuthenticated]

    BOOL_KEYS = {
        "auto_assign_newcomers": True,   # key -> default when unset
    }

    def get(self, request):
        return Response({
            k: AppSetting.get_bool(k, default) for k, default in self.BOOL_KEYS.items()
        })

    def patch(self, request):
        # Changing a church-wide switch needs Admin edit permission and an
        # account covering every location. It used to need only the right
        # to view Admin.
        from accounts.permissions import user_has
        user = request.user
        if not (user.is_superuser or (user_has(user, "admin", "can_edit") and not user.location_id)):
            return Response(
                {"detail": "Only administrators can change church settings."}, status=403,
            )

        unknown = set(request.data) - set(self.BOOL_KEYS)
        if unknown:
            return Response(
                {"detail": f"Unknown setting(s): {', '.join(sorted(unknown))}."}, status=400,
            )

        for key in request.data:
            value = request.data[key]
            if not isinstance(value, bool):
                return Response({key: "Must be true or false."}, status=400)
            AppSetting.set_bool(key, value)
            log_audit(
                request.user,
                "Enabled setting" if value else "Disabled setting",
                "Setting", key, "",
            )

        return Response({
            k: AppSetting.get_bool(k, default) for k, default in self.BOOL_KEYS.items()
        })


class FollowUpRulesSerializer(serializers.ModelSerializer):
    newcomer_stages = serializers.ListField(
        child=serializers.ChoiceField(choices=["new", "contacted", "attending"]), allow_empty=True)
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = FollowUpRules
        exclude = ["id", "updated_by"]
        read_only_fields = ["updated_at"]

    LIMITS = {
        "due_hours": (1, 168), "reason_hours": (1, 336), "review_days": (1, 30),
        "decide_days": (1, 60), "max_new_date_days": (1, 30), "alert_from_miss": (1, 10),
        "visit_task_at_miss": (1, 10), "attempts_before_coordinator": (1, 10),
        "falling_percent": (1, 100), "falling_window": (2, 52), "shepherd_limit": (1, 50),
        "check_hours_after_start": (1, 12), "target_on_time": (1, 100),
        "target_first_contact_hours": (1, 168), "target_reached": (1, 100),
    }

    def get_updated_by_name(self, obj):
        from accounts.audit import display_name
        return display_name(obj.updated_by) if obj.updated_by_id else ""

    def to_representation(self, obj):
        data = super().to_representation(obj)
        data["newcomer_stages"] = obj.stages
        return data

    def validate(self, attrs):
        errors = {}
        for f, (lo, hi) in self.LIMITS.items():
            if f in attrs and not (lo <= attrs[f] <= hi):
                errors[f] = f"Use a number from {lo} to {hi}."
        get = lambda f: attrs.get(f, getattr(self.instance, f))
        if "reason_hours" not in errors and get("reason_hours") <= get("due_hours"):
            errors["reason_hours"] = ("A reason is asked for once a task is late, so this must be "
                                      "more hours than Follow-up due after.")
        if "review_days" not in errors and get("review_days") * 24 < get("reason_hours"):
            errors["review_days"] = ("The Review list comes after the shepherd has had the chance "
                                     "to give a reason, so this must be at least as long as "
                                     "Reason required after.")
        if "decide_days" not in errors and get("decide_days") <= get("review_days"):
            errors["decide_days"] = ("The Follow-up Coordinator decides after a task reaches the "
                                     "Review list, so this must be more days than the Review list.")
        if errors:
            raise serializers.ValidationError(errors)
        if "newcomer_stages" in attrs:
            order = ["new", "contacted", "attending"]
            attrs["newcomer_stages"] = ",".join(s for s in order if s in attrs["newcomer_stages"])
        return attrs


class FollowUpRulesView(APIView):
    """
    Admin, Follow-up Rules (Kay, 26 October 2026). Everyone signed in can
    read the rules, because every follow-up screen shows times worked out
    from them. Only an administrator covering every location can change
    them, since they apply at every location; each change is logged.
    """
    permission_classes = [IsAuthenticated]

    def _can_change(self, user):
        from accounts.permissions import user_has
        return user.is_superuser or (user_has(user, "admin", "can_edit") and not user.location_id)

    def _refuse(self):
        return Response({"detail": "These rules apply at every location, so only an administrator "
                                   "covering All locations can change them."}, status=403)

    def get(self, request):
        from .models import FollowUpRules
        data = FollowUpRulesSerializer(FollowUpRules.get()).data
        data["can_change"] = self._can_change(request.user)
        return Response(data)

    def put(self, request):
        return self._save(request, partial=False)

    def patch(self, request):
        return self._save(request, partial=True)

    def _save(self, request, partial):
        from django.utils import timezone
        from .models import FollowUpRules
        if not self._can_change(request.user):
            return self._refuse()
        obj = FollowUpRules.get()
        before = FollowUpRulesSerializer(obj).data
        ser = FollowUpRulesSerializer(obj, data=request.data, partial=partial)
        ser.is_valid(raise_exception=True)
        obj = ser.save(updated_by=request.user, updated_at=timezone.now())
        after = FollowUpRulesSerializer(obj).data
        changed = [f"{k}: {before[k]} to {after[k]}" for k in after
                   if k not in ("updated_at", "updated_by_name") and before.get(k) != after[k]]
        if changed:
            log_audit(request.user, "Changed", "Follow-up Rules", "Follow-up Rules", "; ".join(changed))
        data = dict(after)
        data["can_change"] = True
        return Response(data)

    def post(self, request):
        """Put back the decided values (26 October 2026)."""
        from django.utils import timezone
        from .models import FollowUpRules
        if not self._can_change(request.user):
            return self._refuse()
        FollowUpRules.objects.filter(pk=1).delete()
        obj = FollowUpRules.get()
        obj.updated_by, obj.updated_at = request.user, timezone.now()
        obj.save()
        log_audit(request.user, "Put back decided values", "Follow-up Rules", "Follow-up Rules")
        data = dict(FollowUpRulesSerializer(obj).data)
        data["can_change"] = True
        return Response(data)
