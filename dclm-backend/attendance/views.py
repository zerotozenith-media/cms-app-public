from django.db import transaction
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.audit import log_audit
from accounts.permissions import ModulePermission, LocationScopedQuerySetMixin
from .models import MeetingType, AttendanceSession, AttendanceSessionMember
from .serializers import (
    MeetingTypeSerializer, AttendanceSessionSerializer, AttendanceSessionMemberSerializer, RecordAttendanceSerializer,
)


class MeetingTypeViewSet(viewsets.ModelViewSet):
    module = "attendance"
    permission_classes = [ModulePermission]
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

    def get_queryset(self):
        from django.db.models import F
        qs = super().get_queryset()
        meeting_type = self.request.query_params.get("meeting_type")
        if meeting_type:
            qs = qs.filter(meeting_type_id=meeting_type)
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
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
            f"{instance.meeting_type.name} , {instance.date}", instance=instance,
        )

    def perform_destroy(self, instance):
        name = f"{instance.meeting_type.name} , {instance.date}"
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

    @action(detail=True, methods=["post"])
    def record(self, request, pk=None):
        """
        The only correct way to fill in a session's attendance. Headcounts
        remain the source of truth (Batch 0.2) regardless of whether named
        attendance is also used. No location restriction on attendee_ids,
        per the approved Batch 0.2 decision.
        """
        session = self.get_object()
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
            for field in ["men", "women", "youth_boys", "youth_girls", "children_boys", "children_girls"]:
                setattr(session, field, data[field])
            session.status = AttendanceSession.Status.FILLED
            session.track_named = data["track_named"]

            log_audit(
                request.user, "Recorded attendance", "Attendance Session",
                f"{session.meeting_type.name} , {session.date}",
                f"Total {sum(data[f] for f in ['men','women','youth_boys','youth_girls','children_boys','children_girls'])}",
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
                AttendanceSessionMember.objects.filter(session=session).delete()
                AttendanceSessionMember.objects.bulk_create([
                    AttendanceSessionMember(session=session, member_id=mid)
                    for mid in data["attendee_ids"]
                ])

        return Response(AttendanceSessionSerializer(session).data)

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
        session = self.get_object()
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
