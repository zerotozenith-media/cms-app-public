from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.audit import log_audit
from accounts.names import display_name
from accounts.permissions import user_has, user_can_view_module

from .models import AlertSettings, Announcement, PushSubscription
from .push import keys, send

KIND_LABELS = {
    "morning": ("Morning summary", "At 7 am, what is waiting for you today. Only sent when something is."),
    "assigned": ("Someone given to me", "When a member, newcomer or contact becomes yours to follow up."),
    "arrivals": ("New contacts and newcomers", "When someone contacts the church online or registers as a newcomer."),
    "weekly": ("Weekly summary", "Monday morning, how follow-up went last week. For leaders."),
    "announcements": ("Church announcements", "Messages sent by an administrator."),
    "followup": ("Follow-up accountability", "Late tasks and reasons, the Review list, repeated absences, "
                 "and reminders to tick names after a service."),
}


def _is_admin(user):
    from core.followup_access import is_administrator
    return is_administrator(user)


def kinds_for(user):
    """Only the kinds this person can actually receive."""
    out = ["morning", "assigned"]
    if user_has(user, "newcomers", "can_edit") and user_has(user, "admin", "can_view"):
        out.append("arrivals")
    if user_can_view_module(user, "admin"):
        out.append("weekly")
    out.append("announcements")
    if (getattr(user, "can_shepherd", False) or getattr(user, "is_followup_coordinator", False)
            or user_has(user, "followup-review", "can_view") or _is_admin(user)):
        out.append("followup")
    return out


class KeyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"public_key": keys()[0]})


class SubscribeSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=1000)
    keys = serializers.DictField(child=serializers.CharField(max_length=255))
    device = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")

    def validate_endpoint(self, v):
        if not v.startswith("https://"):
            raise serializers.ValidationError("Alerts need a secure address.")
        return v

    def validate_keys(self, v):
        if not v.get("p256dh") or not v.get("auth"):
            raise serializers.ValidationError("This device sent incomplete keys.")
        return v


class SubscribeView(APIView):
    """Turn alerts on for this device. A device used by somebody else before
    now belongs to whoever turned it on last."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        s = SubscribeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        PushSubscription.objects.update_or_create(endpoint=d["endpoint"], defaults=dict(
            user=request.user, p256dh=d["keys"]["p256dh"], auth=d["keys"]["auth"], device=d["device"][:255]))
        AlertSettings.for_user(request.user)
        return Response({"devices": request.user.push_subscriptions.count()}, status=status.HTTP_201_CREATED)


class UnsubscribeView(APIView):
    """Turn alerts off for this device. Only your own devices."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        endpoint = request.data.get("endpoint") or ""
        n, _ = PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
        return Response({"removed": n})


class SettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def _out(self, request, st):
        endpoint = request.query_params.get("endpoint") or ""
        return {
            "kinds": [{"key": k, "label": KIND_LABELS[k][0], "help": KIND_LABELS[k][1], "on": st.wants(k)} for k in kinds_for(request.user)],
            "devices": request.user.push_subscriptions.count(),
            "this_device": bool(endpoint) and request.user.push_subscriptions.filter(endpoint=endpoint).exists(),
        }

    def get(self, request):
        return Response(self._out(request, AlertSettings.for_user(request.user)))

    def patch(self, request):
        st = AlertSettings.for_user(request.user)
        changed = []
        for k in AlertSettings.KINDS:
            if k in request.data:
                v = request.data[k]
                if not isinstance(v, bool):
                    return Response({"detail": f"{k} must be true or false."}, status=400)
                setattr(st, k, v); changed.append(k)
        if changed:
            st.save(update_fields=changed)
        return Response(self._out(request, st))


class TestView(APIView):
    """Send a test alert to every device of the person asking."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        subs = list(request.user.push_subscriptions.all())
        if not subs:
            return Response({"detail": "Turn alerts on for this device first."}, status=400)
        from .push import _deliver
        payload = {"title": "Alerts are working", "body": "This is how alerts from DCLM Bahrain will look.", "url": "/profile", "tag": "test"}
        n = sum(1 for s in subs if _deliver(s, payload))
        if not n:
            return Response({"detail": "The alert could not be delivered. Turn alerts off and on again on this device."}, status=502)
        return Response({"devices": n})


class AnnouncementSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=80)
    body = serializers.CharField(max_length=300)
    audience = serializers.CharField(max_length=40)          # everyone | shepherds | role-<id>
    location = serializers.CharField(required=False, allow_blank=True, default="")


def audience_users(user, audience, location):
    """Who an announcement reaches. Someone limited to one location reaches
    only that location."""
    from accounts.models import Role, User
    qs = User.objects.filter(is_active=True)
    label = "Everyone"
    if audience == "shepherds":
        qs = qs.filter(can_shepherd=True); label = "Shepherds and follow-up people"
    elif audience.startswith("role-"):
        try:
            role = Role.objects.get(pk=int(audience[5:]))
        except (ValueError, Role.DoesNotExist):
            raise serializers.ValidationError({"audience": "Choose who to send it to."})
        qs = qs.filter(role=role); label = role.name
    elif audience != "everyone":
        raise serializers.ValidationError({"audience": "Choose who to send it to."})
    loc = user.location_id if (user.location_id and not user.is_superuser) else (location or None)
    if loc:
        from core.models import Location
        if not Location.objects.filter(pk=loc).exists():
            raise serializers.ValidationError({"location": "Choose a location."})
        from django.db.models import Q
        qs = qs.filter(Q(location_id=loc) | Q(location__isnull=True))
    return qs, label, loc


class AnnouncementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not user_has(request.user, "admin", "can_view"):
            return Response({"detail": "You do not have permission to see alerts that were sent."}, status=403)
        qs = Announcement.objects.select_related("sent_by", "location")
        if request.user.location_id and not request.user.is_superuser:
            qs = qs.filter(location_id=request.user.location_id)
        reach = PushSubscription.objects.filter(user__is_active=True).values("user").distinct().count()
        return Response({
            "people_with_alerts": reach,
            "results": [{"id": a.id, "title": a.title, "body": a.body, "audience": a.audience,
                         "location": a.location.name if a.location else "All locations",
                         "sent_by": display_name(a.sent_by) if a.sent_by else "", "people": a.people,
                         "devices": a.devices, "created_at": a.created_at.isoformat()} for a in qs[:30]],
        })

    def post(self, request):
        if not user_has(request.user, "admin", "can_edit"):
            return Response({"detail": "Only administrators can send alerts."}, status=403)
        s = AnnouncementSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        qs, label, loc = audience_users(request.user, d["audience"], d["location"])
        body = f"{d['body'].strip()} (Sent by {display_name(request.user)})"
        people = devices = 0
        for u in qs.filter(push_subscriptions__isnull=False).distinct():
            n = send(u, "announcements", d["title"].strip(), body, "/", tag=f"announce-{timezone.now().timestamp():.0f}")
            if n:
                people += 1; devices += n
        a = Announcement.objects.create(title=d["title"].strip(), body=d["body"].strip(), audience=label,
                                        location_id=loc, sent_by=request.user, people=people, devices=devices)
        log_audit(request.user, "Sent an alert", "Alert", a.title, f"To {label}: {people} people, {devices} devices")
        return Response({"id": a.id, "people": people, "devices": devices}, status=201)


class NoticesView(APIView):
    """
    The alerts kept in the app (Kay, 26 October 2026): the newest 50, and
    how many are unread. POST marks them read: the ids given, or all.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import Notice
        qs = Notice.objects.filter(user=request.user)
        rows = [{"id": n.id, "kind": n.kind, "title": n.title, "body": n.body, "url": n.url,
                 "created_at": n.created_at, "read": bool(n.read_at)} for n in qs[:50]]
        return Response({"unread": qs.filter(read_at__isnull=True).count(), "results": rows})

    def post(self, request):
        from django.utils import timezone
        from .models import Notice
        qs = Notice.objects.filter(user=request.user, read_at__isnull=True)
        ids = request.data.get("ids")
        if ids:
            qs = qs.filter(id__in=ids)
        n = qs.update(read_at=timezone.now())
        return Response({"marked": n})
