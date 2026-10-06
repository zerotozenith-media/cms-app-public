from accounts.permissions import require
from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from accounts.audit import log_audit
from accounts.permissions import ModulePermission, LocationScopedQuerySetMixin
from .models import Fellowship, MeetingType, AttendanceSession, AttendanceSessionMember
from core.viewing import scope_location_id
from .serializers import (
    FellowshipSerializer, MeetingTypeSerializer, AttendanceSessionSerializer, AttendanceSessionMemberSerializer, RecordAttendanceSerializer,
)


class MeetingTypeViewSet(viewsets.ModelViewSet):
    # Affects every location, so only an administrator covering every
    # location may change it. See ModulePermission.
    church_wide = True
    module = "attendance"
    permission_classes = [ModulePermission]

    def get_permissions(self):
        # Anyone signed in can read the meetings, as with locations: forms
        # such as manual newcomer entry offer them. The enquiries role was
        # refused, leaving that dropdown empty. Changes still need permission.
        from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
        if self.request.method in SAFE_METHODS:
            return [IsAuthenticated()]
        return super().get_permissions()
    queryset = MeetingType.objects.all()
    serializer_class = MeetingTypeSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit(self.request.user, "Created", "Meeting Type", instance.name, instance=instance)

    def perform_destroy(self, instance):
        name = instance.name
        log_audit(self.request.user, "Deleted", "Meeting Type", name)
        instance.delete()


class AttendanceSessionViewSet(LocationScopedQuerySetMixin, viewsets.ModelViewSet):
    module = "attendance"
    permission_classes = [ModulePermission]
    queryset = AttendanceSession.objects.select_related("meeting_type", "location").prefetch_related("attendees__member")
    serializer_class = AttendanceSessionSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["date", "total_computed"]

    class _StableOrdering(filters.OrderingFilter):
        """Sessions on the same date had no fixed order, so paging could repeat
        or skip one (found in the manual walk). Ties now go newest first."""
        def get_ordering(self, request, queryset, view):
            ordering = list(super().get_ordering(request, queryset, view) or ["-date"])
            return ordering if "-id" in ordering or "id" in ordering else ordering + ["-id"]
    filter_backends = [_StableOrdering]

    def get_queryset(self):
        from django.db.models import F
        qs = super().get_queryset()
        meeting_type = self.request.query_params.get("meeting_type")
        if meeting_type:
            qs = qs.filter(meeting_type_id=meeting_type)
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        # Who the meeting was for. Lets a leader look only at workers
        # meetings without wading through every Friday service.
        audience = self.request.query_params.get("audience")
        if audience:
            qs = qs.filter(meeting_type__audience=audience)

        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(date__gte=date_from)
        date_to = self.request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(date__lte=date_to)

        # Sessions where nobody was ticked off by name are exactly the ones
        # where absence follow-up silently did not happen, so being able to
        # find them matters more than it looks.
        checked_in = self.request.query_params.get("checked_in")
        if checked_in == "yes":
            qs = qs.filter(attendees__isnull=False).distinct()
        elif checked_in == "no":
            qs = qs.filter(attendees__isnull=True)
        # total is a Python property, not a DB field , sorting "by total"
        # client-side would only reorder the current page, not the true
        # global order. Annotated here so ?ordering=total_computed sorts
        # correctly across the whole (possibly paginated) result set.
        qs = qs.annotate(
            total_computed=F("men") + F("women") + F("youth_boys") + F("youth_girls") + F("children_boys") + F("children_girls")
        )
        return qs

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit(
            self.request.user, "Created", "Attendance Session",
            f"{instance.meeting_type.name} · {instance.date}", instance=instance,
        )

    def perform_destroy(self, instance):
        name = f"{instance.meeting_type.name} · {instance.date}"
        log_audit(self.request.user, "Deleted", "Attendance Session", name)
        instance.delete()

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """
        Same reasoning as Member.stats() in Batch 3.4: sessions
        accumulate indefinitely over years of weekly meetings, so a real
        aggregate query is correct regardless of how much history exists,
        rather than a client-side count that only reflects one page.
        """
        from django.utils import timezone
        base = LocationScopedQuerySetMixin.get_queryset(self)
        today = timezone.localdate()
        # year/month lookups, not date__startswith , a string-prefix match
        # on a DateField risks behaving differently between SQLite (local
        # dev) and PostgreSQL (production); year/month is the portable,
        # correct way to filter a date by calendar month in Django's ORM.
        this_month = base.filter(date__year=today.year, date__month=today.month)
        return Response({
            "sessions_this_month": this_month.count(),
            "filled": base.filter(status="filled").count(),
            "pending": base.filter(status="pending").count(),
        })

    @staticmethod
    def _record_offering(session, amounts):
        """
        Save what was collected at this meeting as giving linked to it.

        Recorded once, not copied onto the session as well: the same
        money in two places disagrees the first time somebody corrects
        one of them. Rewritten wholesale each save so an amount lowered
        to zero disappears rather than lingering.
        """
        from finance.models import Fund, Giving, PaymentMethod

        if not session.meeting_type.collects_offering:
            return
        session.giving.all().delete()
        if not amounts:
            return
        cash, _ = PaymentMethod.objects.get_or_create(name="Cash")
        for fund_name, amount in amounts.items():
            if not amount:
                continue
            fund = Fund.objects.filter(name__iexact=fund_name).first()
            if not fund:
                continue
            Giving.objects.create(
                date=session.date, fund=fund, method=cash, amount=amount,
                location=session.location, session=session)

    @action(detail=True, methods=["post"])
    def record(self, request, pk=None):
        """
        The only correct way to fill in a session's attendance. Headcounts
        remain the source of truth (Batch 0.2) regardless of whether named
        attendance is also used. No location restriction on attendee_ids,
        per the approved Batch 0.2 decision.
        """
        require(request.user, ("attendance", "can_edit"))
        session = self.get_object()
        # A service that has not happened yet has no attendance. Accepting
        # it let a figure for next Friday stand as the latest service on the
        # dashboard.
        if session.date > timezone.localdate():
            return Response(
                {"detail": f"This service is on {session.date:%-d %B}. Attendance can be "
                           f"recorded on the day or after."}, status=400)
        serializer = RecordAttendanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if session.meeting_type.detail_level == MeetingType.DetailLevel.SIMPLE:
            offending = [f for f in ["youth_boys", "youth_girls", "children_boys", "children_girls"] if data.get(f)]
            if offending:
                return Response(
                    {f: f"{session.meeting_type.name} is a simple (Men/Women only) meeting." for f in offending},
                    status=400,
                )

        with transaction.atomic():
            for field in ["men", "women", "youth_boys", "youth_girls",
                          "children_boys", "children_girls",
                          "online_men", "online_women", "online_youth_boys",
                          "online_youth_girls", "online_children_boys",
                          "online_children_girls", "new_comers", "new_converts"]:
                setattr(session, field, data[field])
            # The session's mode can be changed, for example a week moved online.
            if data.get("mode"):
                session.mode = data["mode"]
            if session.meeting_type.frequency == MeetingType.Frequency.OCCASIONAL:
                for f in ("edition_name", "edition_place"):
                    if f in data:
                        setattr(session, f, (data[f] or "").strip())
            if session.fellowship_id:
                session.lesson = data.get("lesson", "")
                if data.get("led_by"):
                    session.led_by_id = data["led_by"]

            self._record_offering(session, data.get("offering") or {})
            session.status = AttendanceSession.Status.FILLED
            session.track_named = data["track_named"]

            log_audit(
                request.user, "Recorded attendance", "Attendance Session",
                f"{session.meeting_type.name} · {session.date}",
                f"Total {sum(data[f] for f in ['men','women','youth_boys','youth_girls','children_boys','children_girls','online_men','online_women','online_youth_boys','online_youth_girls','online_children_boys','online_children_girls'])}",
                instance=session,
            )
            session.save()

            if data["track_named"]:
                # bulk_create() deliberately used here , per Batch 1.5, bulk
                # operations don't trigger the automatic audit signal, and
                # that's fine in this specific case: the "Recorded attendance"
                # entry above already covers this action at the right level
                # of detail. Individually logging every checked-in member
                # would be noise, not signal , named attendance is explicitly
                # supplementary data (Batch 0.2), not the audited headline event.
                # Only members' ticks are replaced. Newcomers checked in at the
                # door are kept: wiping them lost their visits, readiness and
                # follow-up stage (found in the manual check).
                AttendanceSessionMember.objects.filter(session=session, member__isnull=False).delete()
                AttendanceSessionMember.objects.bulk_create([
                    AttendanceSessionMember(session=session, member_id=mid)
                    for mid in data["attendee_ids"]
                ])

        return Response(AttendanceSessionSerializer(session).data)

    def get_permissions(self):
        # Manual check: undoing a check-in by tapping again was refused for
        # ushers, because the general rule treats any DELETE as deleting a
        # record. check_in applies its own rule (edit attendance) inside.
        if getattr(self, "action", None) == "check_in":
            from rest_framework.permissions import IsAuthenticated
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=True, methods=["post", "delete", "patch"])
    def check_in(self, request, pk=None):
        """
        Real-time, single-tap check-in , deliberately separate from
        record()'s batch headcount submission. Each tap is its own
        atomic request, not part of a larger form, because concurrent
        ushers at different doors must never overwrite each other's taps
        with a stale full-form resubmit. Three explicit operations, not
        one ambiguous toggle: POST checks a member in, DELETE checks them
        out, PATCH changes their mode (in-person/online) without
        affecting whether they're checked in at all , mirrors the two
        genuinely different taps in the real UI (tapping the row vs.
        tapping "Mark online").

        Headcounts stay completely untouched here, on purpose , Batch 0.2
        already established headcounts as the source of truth,
        independent of named attendance; this endpoint doesn't change
        that, it only manages the supplementary named list in real time.
        """
        require(request.user, ("attendance", "can_edit"))
        session = self.get_object()
        if session.date > timezone.localdate():
            return Response(
                {"detail": f"This service is on {session.date:%-d %B}. People can be checked "
                           f"in on the day."}, status=400)
        member_id = request.data.get("member_id")
        if not member_id:
            return Response({"member_id": "This field is required."}, status=400)

        if request.method == "POST":
            mode = request.data.get("mode", AttendanceSessionMember.Mode.IN_PERSON)
            AttendanceSessionMember.objects.update_or_create(
                session=session, member_id=member_id, defaults={"mode": mode},
            )
        elif request.method == "DELETE":
            AttendanceSessionMember.objects.filter(session=session, member_id=member_id).delete()
        elif request.method == "PATCH":
            mode = request.data.get("mode")
            if mode not in AttendanceSessionMember.Mode.values:
                return Response({"mode": "Must be 'in-person' or 'online'."}, status=400)
            updated = AttendanceSessionMember.objects.filter(
                session=session, member_id=member_id,
            ).update(mode=mode)
            if not updated:
                return Response({"detail": "This member isn't checked in yet."}, status=404)

        # session.attendees.all() would return the queryset's own
        # prefetch_related("attendees__member") cache, populated when
        # get_object() fetched the session , stale as of before this
        # request's create/delete/update above. Found via a real
        # end-to-end API test, not the unit tests, which checked the
        # database directly and so never exercised this response body.
        # Querying AttendanceSessionMember directly bypasses that cache.
        fresh_attendees = AttendanceSessionMember.objects.filter(session=session).select_related("member")
        return Response({
            "attendees": AttendanceSessionMemberSerializer(fresh_attendees, many=True).data,
        })


class FellowshipViewSet(viewsets.ModelViewSet):
    """
    The house fellowships. Configurable because the number changes as the
    church grows, rather than fixed in the software.
    """
    module = "attendance"
    permission_classes = [ModulePermission]
    queryset = Fellowship.objects.all()
    serializer_class = FellowshipSerializer

    def get_queryset(self):
        # Fellowships meeting at this person's location, or at every
        # location. Qatar was shown Bahrain's fellowships, and could pick
        # one when starting a session.
        from django.db.models import Q
        qs = super().get_queryset()
        user = self.request.user
        loc = scope_location_id(user)
        if loc:
            qs = qs.filter(Q(location_id=loc) | Q(location__isnull=True))
        return qs

    def perform_destroy(self, instance):
        # PROTECT on the session link already prevents this at the database
        # level, but the message it raises means nothing to a church
        # administrator.
        if instance.sessions.exists():
            raise ValidationError({
                "detail": f"{instance.name} has {instance.sessions.count()} session(s) "
                          "recorded. Those records would lose what they belong to."
            })
        log_audit(self.request.user, "Deleted", "Fellowship", instance.name, "")
        instance.delete()



from rest_framework.decorators import api_view, permission_classes as _pc
from rest_framework.permissions import AllowAny as _AllowAny
from rest_framework.response import Response as _Response


@api_view(["GET"])
@_pc([_AllowAny])
def public_meetings(request):
    """Meeting names only, for the public QR registration form's "Meeting"
    question. It was refused before sign-in, so the list was always empty."""
    from .models import MeetingType
    rows = MeetingType.objects.order_by("name").values("id", "name")
    return _Response([{"id": r["id"], "name": r["name"]} for r in rows])
