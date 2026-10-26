from accounts.permissions import require
from core.scoping import LocationScopedMixin
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from accounts.audit import log_audit
from accounts.permissions import ModulePermission, LocationScopedQuerySetMixin
from .intake import match_invited_by_member, create_auto_tasks, check_in_today
from .models import (
    NewcomerContactAttempt,
    NewcomerSource, MilestoneType, Newcomer, NewcomerStatusHistory,
    NewcomerMilestone, NewcomerTask, FollowUpUrgencySetting, PublicRegistrationAttempt,
)
from .serializers import (
    NewcomerSourceSerializer, MilestoneTypeSerializer, NewcomerSerializer,
    NewcomerStatusHistorySerializer, NewcomerTaskSerializer, CompleteNewcomerTaskSerializer,
    FollowUpUrgencySettingSerializer, ChangeStageSerializer, SetMilestoneSerializer,
    PublicRegistrationSerializer,
)


class NewcomerSourceViewSet(viewsets.ModelViewSet):
    module = "newcomers"
    permission_classes = [ModulePermission]
    queryset = NewcomerSource.objects.all()
    serializer_class = NewcomerSourceSerializer


class MilestoneTypeViewSet(viewsets.ModelViewSet):
    module = "newcomers"
    permission_classes = [ModulePermission]
    queryset = MilestoneType.objects.all()
    serializer_class = MilestoneTypeSerializer


class FollowUpUrgencySettingViewSet(viewsets.ModelViewSet):
    # Affects every location, so only an administrator covering every
    # location may change it. See ModulePermission.
    church_wide = True
    module = "newcomers"
    permission_classes = [ModulePermission]
    queryset = FollowUpUrgencySetting.objects.all()
    serializer_class = FollowUpUrgencySettingSerializer


class NewcomerViewSet(LocationScopedQuerySetMixin, viewsets.ModelViewSet):
    module = "newcomers"
    permission_classes = [ModulePermission]
    queryset = Newcomer.objects.select_related("source", "assigned_to", "location").prefetch_related("milestones", "tasks")
    serializer_class = NewcomerSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["created_at", "stage_since"]

    def perform_create(self, serializer):
        invited_by_member = match_invited_by_member(serializer.validated_data.get("invited_by_name"))

        instance = serializer.save(
            created_at=timezone.localdate(),
            stage_since=timezone.localdate(),
            invited_by_member=invited_by_member,
        )
        log_audit(self.request.user, "Created", "Newcomer", instance.name, instance=instance)
        hand_picked = instance.assigned_to_id
        create_auto_tasks(instance)
        check_in_today(instance)
        from alerts.events import arrival, given
        if hand_picked:
            given([("newcomer", instance.pk, instance.name, hand_picked)], by=self.request.user)
        instance.refresh_from_db()
        arrival("newcomer", instance, by=self.request.user)

    def perform_update(self, serializer):
        """
        A newcomer moved to another location gets a shepherd there if theirs
        cannot serve it, and their open tasks go with the new shepherd.
        Moving them used to leave them with a shepherd at the old location.
        """
        before = serializer.instance.location_id
        before_shepherd = serializer.instance.assigned_to_id
        newcomer = serializer.save()
        if newcomer.assigned_to_id != before_shepherd:
            from core.task_actions import move_open_tasks
            move_open_tasks(newcomer, newcomer.assigned_to_id)
        if newcomer.assigned_to_id and newcomer.assigned_to_id != before_shepherd:
            from alerts.events import given
            given([("newcomer", newcomer.pk, newcomer.name, newcomer.assigned_to_id)], by=self.request.user)
        if newcomer.location_id != before and newcomer.assigned_to_id:
            from members.assignment import eligible_shepherds, assign_on_registration
            if newcomer.assigned_to_id not in {u.id for u in eligible_shepherds(location=newcomer.location_id)}:
                newcomer.assigned_to = None
                newcomer.save(update_fields=["assigned_to"])
                assign_on_registration(newcomer)
                # Every open task follows, not only unowned ones: the old
                # shepherd no longer looks after them.
                from newcomers.models import NewcomerTask
                NewcomerTask.objects.filter(newcomer=newcomer, done=False).update(
                    assigned_to=newcomer.assigned_to)

    def perform_destroy(self, instance):
        name = instance.name
        log_audit(self.request.user, "Deleted", "Newcomer", name)
        instance.delete()

    @action(detail=True, methods=["get"])
    def person(self, request, pk=None):
        """The one-profile summary (F16): journey, milestones, open follow-ups, check-ins."""
        from members.person import build_person
        n = self.get_object()
        return Response(build_person(member=getattr(n, "became_member", None), newcomer=n))

    @action(detail=True, methods=["get"])
    def journey(self, request, pk=None):
        """The whole history in order, for the travel map on the profile."""
        from .journey import build_journey
        return Response(build_journey(self.get_object()))

    @action(detail=True, methods=["get"])
    def readiness(self, request, pk=None):
        """Whether this person is proposed for membership, and the working
        behind it. An administrator seeing only a verdict would ask why."""
        from .membership import readiness as compute
        return Response(compute(self.get_object()))

    @action(detail=True, methods=["post"], url_path="log-attempt")
    def log_attempt(self, request, pk=None):
        """
        Record a contact that did not reach the person.

        Separate from completing a task, which requires the four outcome
        fields because someone was actually spoken to. An unanswered call
        has no outcome to record, but still belongs in the history.
        """
        newcomer = self.get_object()
        method = request.data.get("method")
        if method not in dict(NewcomerContactAttempt.Method.choices):
            return Response({"method": "Choose how you tried to reach them."}, status=400)
        attempt = NewcomerContactAttempt.objects.create(
            newcomer=newcomer, method=method,
            note=request.data.get("note", ""), by=request.user,
        )
        log_audit(request.user, "Logged contact attempt", "Newcomer", newcomer.name,
                  f"{method}, no reply", instance=newcomer)
        return Response({"id": attempt.id, "date": attempt.date, "method": attempt.method}, status=201)

    def get_permissions(self):
        if getattr(self, "action", None) == "away":
            from rest_framework.permissions import IsAuthenticated
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=True, methods=["post", "delete"])
    def away(self, request, pk=None):
        """Mark the newcomer away for a known absence, or clear it."""
        return away_action(self, request, self.get_object(), "newcomers")

    @action(detail=True, methods=["post"], url_path="make-member")
    def make_member(self, request, pk=None):
        """
        Add this newcomer to the member roll.

        The newcomer record is kept and linked rather than deleted, so
        their whole follow-up history stays reachable and the church can
        still see how they first arrived. Their card stays on the board
        under Member instead of disappearing.
        """
        require(request.user, ("newcomers", "can_edit"), ("members", "can_create"))
        newcomer = self.get_object()
        if getattr(newcomer, "became_member", None):
            return Response(
                {"detail": f"{newcomer.name} is already on the member roll."}, status=400)
        try:
            member = convert_to_member(newcomer, request.user)
        except ConversionConflict as e:
            return Response({"detail": str(e)}, status=400)
        return Response({"member_id": member.id, "name": member.full_name}, status=201)

    @action(detail=True, methods=["post"], url_path="change-stage")
    def change_stage(self, request, pk=None):
        """
        The only correct way to change a Newcomer's stage , covers every
        transition uniformly (normal pipeline progression, marking Not
        Interested, and reactivating), always creating a
        NewcomerStatusHistory entry, per the Batch 2.3 design decision to
        track the full pipeline journey rather than only not-interested
        episodes.
        """
        require(request.user, ("newcomers", "can_edit"))
        newcomer = self.get_object()
        serializer = ChangeStageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        to_stage = serializer.validated_data["to_stage"]
        note = serializer.validated_data["note"]
        from_stage = newcomer.stage
        today = timezone.localdate()

        if to_stage == from_stage:
            return Response({"detail": f"Newcomer is already {to_stage}."}, status=400)
        # Not Interested stops follow-up (Kay, 26 October 2026), so the
        # reason is kept with it.
        if to_stage == Newcomer.Stage.NOT_INTERESTED and not note.strip():
            return Response({"note": "Say why, for example \"Moved back home\". Not Interested stops "
                                     "follow-up, so the reason is kept with it."}, status=400)

        # Becoming a member is a conversion, not just a new label. Moving
        # the stage alone left the person shown as a member on the board
        # and missing from the member roll.
        if to_stage == Newcomer.Stage.MEMBER:
            try:
                member = convert_to_member(newcomer, request.user)
            except ConversionConflict as e:
                return Response({"detail": str(e)}, status=400)
            return Response({"member_id": member.id, "stage": "member"})

        with transaction.atomic():
            NewcomerStatusHistory.objects.create(
                newcomer=newcomer, stage=to_stage, note=note, date=today,
            )
            log_audit(
                request.user,
                "Marked Not Interested" if to_stage == Newcomer.Stage.NOT_INTERESTED
                else ("Reactivated" if from_stage == Newcomer.Stage.NOT_INTERESTED else "Stage changed"),
                "Newcomer", newcomer.name, f"{from_stage} -> {to_stage}" + (f" ({note})" if note else ""),
                instance=newcomer,
            )
            newcomer.stage = to_stage
            newcomer.stage_since = today
            # Reactivating clears the "current" not-interested note , the
            # episode itself remains permanently visible via
            # NewcomerStatusHistory, this field just reflects present state.
            if to_stage != Newcomer.Stage.NOT_INTERESTED:
                newcomer.not_interested_note = ""
            elif note:
                newcomer.not_interested_note = note
            newcomer.save(update_fields=["stage", "stage_since", "not_interested_note"])
            if to_stage == Newcomer.Stage.NOT_INTERESTED:
                from core.accountable import TaskResult
                from core.task_actions import close_open_for
                close_open_for(newcomer, request.user, TaskResult.KNOWN_REASON, f"Marked Not Interested: {note}")

        return Response(NewcomerSerializer(newcomer).data)

    @action(detail=True, methods=["post"], url_path="set-milestone")
    def set_milestone(self, request, pk=None):
        require(request.user, ("newcomers", "can_edit"))
        newcomer = self.get_object()
        serializer = SetMilestoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        milestone_type = serializer.validated_data["milestone_type"]
        achieved = serializer.validated_data["achieved"]
        achieved_date = serializer.validated_data["achieved_date"] or timezone.localdate()

        record, _ = NewcomerMilestone.objects.get_or_create(
            newcomer=newcomer, milestone_type=milestone_type,
        )
        record.achieved_date = achieved_date if achieved else None
        record.save()

        log_audit(
            request.user, "Milestone achieved" if achieved else "Milestone cleared",
            "Newcomer", newcomer.name, milestone_type.name, instance=newcomer,
        )
        # Re-fetch fresh rather than reusing `newcomer` , its .milestones
        # relation was already cached by prefetch_related at get_object()
        # time, so reusing the same in-memory instance here would return
        # the milestones list from *before* this update, not after.
        fresh = self.get_queryset().get(pk=newcomer.pk)
        return Response(NewcomerSerializer(fresh).data)


from core.task_views import TaskActionsMixin, away_action


class NewcomerTaskViewSet(TaskActionsMixin, LocationScopedMixin, viewsets.ModelViewSet):
    location_lookup = "newcomer__location_id"
    module = "newcomers"
    permission_classes = [ModulePermission]
    queryset = NewcomerTask.objects.select_related("newcomer", "newcomer__assigned_to", "newcomer__assigned_to__member", "assigned_to", "assigned_to__member").prefetch_related("attempts", "attempts__by", "reviews")
    serializer_class = NewcomerTaskSerializer

    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["due_date"]
    ordering = ["due_date"]

    def get_queryset(self):
        qs = super().get_queryset()
        newcomer = self.request.query_params.get("newcomer")
        if newcomer:
            qs = qs.filter(newcomer_id=newcomer)
        # Without this the aggregate Follow-up tab's Open/Completed
        # filter would be ignored server-side and quietly return
        # everything, which looks like the filter is broken.
        done = self.request.query_params.get("done")
        if done is not None:
            qs = qs.filter(done=done.lower() == "true")
        return qs

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """
        The only correct way to mark a task done , requires the real
        visitation outcome, not just a checkbox. Phase 4.3 fix: a done
        task with no record of what was discussed wasn't useful to a
        leader reviewing history later.
        """
        from core import task_actions as acts
        from core.task_views import block_until_reasons
        task = self.get_object()
        self._may_record(request, task)
        block_until_reasons(request.user, task)
        serializer = CompleteNewcomerTaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        extra = acts.reached(task, request.user, serializer.validated_data)
        task.refresh_from_db()
        data = dict(NewcomerTaskSerializer(task).data)
        data.update(extra)
        return Response(data)


class NewcomerStatusHistoryViewSet(LocationScopedMixin, viewsets.ModelViewSet):
    location_lookup = "newcomer__location_id"
    module = "newcomers"
    permission_classes = [ModulePermission]
    queryset = NewcomerStatusHistory.objects.select_related("newcomer")
    serializer_class = NewcomerStatusHistorySerializer


# --- Public QR self-registration (no authentication) ---

REGISTRATION_MIN_SUBMIT_SECONDS = 2.0
REGISTRATION_RATE_LIMIT_WINDOW_HOURS = 24
# P10 (review, 25 October 2026): counted per phone, since visitors on the
# church Wi-Fi share one internet address. 5 a day from one phone covers a
# family filling it in for each other. The address limit only stops a flood.
REGISTRATION_MAX_PER_DEVICE = 5
REGISTRATION_MAX_PER_IP = 60
REGISTRATION_MAX_PER_IP_BURST = 15   # in 10 minutes

GENERIC_REGISTRATION_ERROR = {"detail": "We couldn't process your submission. Please see a leader at the welcome desk."}


def _get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


def _blocked(ip, device, now=None):
    """Whether this phone, or this internet address, has sent too many."""
    now = now or timezone.now()
    ok = PublicRegistrationAttempt.objects.filter(successful=True, counted=True,
                                                  timestamp__gte=now - timedelta(hours=REGISTRATION_RATE_LIMIT_WINDOW_HOURS))
    if device and ok.filter(device_id=device).count() >= REGISTRATION_MAX_PER_DEVICE:
        return True
    if not device and ok.filter(ip_address=ip, device_id="").count() >= REGISTRATION_MAX_PER_DEVICE:
        return True   # an old form with no phone id: counted as before
    if ok.filter(ip_address=ip).count() >= REGISTRATION_MAX_PER_IP:
        return True
    return ok.filter(ip_address=ip, timestamp__gte=now - timedelta(minutes=10)).count() >= REGISTRATION_MAX_PER_IP_BURST


@api_view(["GET", "POST"])
def registration_blocks(request):
    """
    P10: phones and addresses the QR form is refusing now, for an
    administrator. POST {"ip": ..., "device_id": ...} lifts a block; the
    attempts stay in the log.
    """
    from accounts.permissions import require
    require(request.user, ("newcomers", "can_edit"), ("admin", "can_view"))
    window = timezone.now() - timedelta(hours=REGISTRATION_RATE_LIMIT_WINDOW_HOURS)
    if request.method == "POST":
        qs = PublicRegistrationAttempt.objects.filter(successful=True, counted=True, timestamp__gte=window)
        if request.data.get("device_id"):
            qs = qs.filter(device_id=request.data["device_id"])
        elif request.data.get("ip"):
            qs = qs.filter(ip_address=request.data["ip"])
        else:
            return Response({"detail": "Say which phone or address to unblock."}, status=400)
        n = qs.update(counted=False)
        log_audit(request.user, "Lifted QR form block", "Public registration",
                  request.data.get("device_id") or request.data.get("ip"), f"{n} submission(s) no longer counted")
        return Response({"lifted": n})
    from django.db.models import Count, Max
    refused = (PublicRegistrationAttempt.objects.filter(reason=PublicRegistrationAttempt.Reason.RATE_LIMITED,
                                                        timestamp__gte=window)
               .values("ip_address", "device_id").annotate(n=Count("id"), last=Max("timestamp")).order_by("-last"))
    rows = [{"ip": r["ip_address"], "device_id": r["device_id"], "refused": r["n"], "last": r["last"],
             "still_blocked": _blocked(r["ip_address"], r["device_id"])} for r in refused]
    return Response({"results": rows, "per_phone": REGISTRATION_MAX_PER_DEVICE, "per_address": REGISTRATION_MAX_PER_IP})


@api_view(["POST"])
@permission_classes([AllowAny])
def public_newcomer_registration(request):
    """
    The real, working public self-registration form the QR code points
    to (confirmed: Bahrain-only , DCLM Bahrain is the main church, Qatar
    is a supporting location expected to eventually be phased out, so no
    location picker is offered here). A genuine unauthenticated write
    endpoint, so it gets the same class of protection as login (Batch
    1.4): honeypot, minimum-submit-time, and per-IP rate limiting , all
    attempts logged to PublicRegistrationAttempt regardless of outcome,
    mirroring LoginAttempt's design.
    """
    import datetime as dt

    ip = _get_client_ip(request)
    device = str(request.data.get("device_id") or "")[:64]

    def reject(reason, response_status=status.HTTP_400_BAD_REQUEST):
        PublicRegistrationAttempt.objects.create(ip_address=ip, device_id=device, successful=False, reason=reason)
        return Response(GENERIC_REGISTRATION_ERROR, status=response_status)

    website = request.data.get("website") or ""
    if website:
        return reject(PublicRegistrationAttempt.Reason.HONEYPOT)

    form_loaded_at = request.data.get("form_loaded_at")
    if form_loaded_at:
        try:
            loaded = dt.datetime.fromisoformat(str(form_loaded_at).replace("Z", "+00:00"))
            elapsed = (dt.datetime.now(dt.timezone.utc) - loaded).total_seconds()
            if elapsed < REGISTRATION_MIN_SUBMIT_SECONDS:
                return reject(PublicRegistrationAttempt.Reason.TOO_FAST)
        except (ValueError, AttributeError):
            pass  # malformed timestamp , don't hard-fail a real submission over it

    if _blocked(ip, device):
        return reject(PublicRegistrationAttempt.Reason.RATE_LIMITED, status.HTTP_429_TOO_MANY_REQUESTS)

    serializer = PublicRegistrationSerializer(data=request.data)
    if not serializer.is_valid():
        PublicRegistrationAttempt.objects.create(
            ip_address=ip, successful=False, reason=PublicRegistrationAttempt.Reason.INVALID_DATA,
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    from core.models import Location
    # The location comes from the QR code the visitor scanned, so a visitor
    # at a Qatar service lands in Qatar's pipeline. Every registration used
    # to be filed under the main location. An unknown or missing code falls
    # back to the main location, found by its flag rather than its name.
    wanted = request.data.get("location") or request.query_params.get("location")
    bahrain = (Location.objects.filter(id=wanted).first() if wanted else None) \
        or Location.objects.filter(is_core=True).first()
    qr_source, _ = NewcomerSource.objects.get_or_create(name="Church website (QR self-registration)")
    invited_by_member = match_invited_by_member(data.get("invited_by_name"))

    with transaction.atomic():
        newcomer = Newcomer.objects.create(
            name=data["name"], source=qr_source, location=bahrain,
            created_at=timezone.localdate(), stage_since=timezone.localdate(),
            address=data["address"], city_governorate=data["city_governorate"],
            phone=data["phone"], email=data["email"], gender=data["gender"], age_group=data["age_group"],
            prayer_request=data["prayer_request"], meeting_attended=data["meeting_attended"],
            is_first_timer=data["is_first_timer"], is_new_resident=data["is_new_resident"],
            wants_visit=data["wants_visit"], wants_to_know_more=data["wants_to_know_more"],
            wants_salvation_info=data["wants_salvation_info"], keep_in_touch=data["keep_in_touch"],
            invited_by_member=invited_by_member, invited_by_name=data["invited_by_name"],
        )
        create_auto_tasks(newcomer)
        check_in_today(newcomer)
        log_audit(None, "Created (QR self-registration)", "Newcomer", newcomer.name, instance=newcomer)
        from alerts.events import arrival
        newcomer.refresh_from_db()
        arrival("newcomer", newcomer)
        PublicRegistrationAttempt.objects.create(ip_address=ip, device_id=device, successful=True,
                                                 reason=PublicRegistrationAttempt.Reason.SUCCESS)

    return Response({"detail": "Thank you! Someone from our team will be in touch soon."}, status=status.HTTP_201_CREATED)

class ConversionConflict(Exception):
    """Raised when converting would put the same person on the roll twice."""


def _shepherd_to_keep(newcomer):
    """The newcomer's shepherd, if they are a shepherd at the newcomer's
    location. Otherwise nobody, for auto-assign to fill properly."""
    if not newcomer.assigned_to_id:
        return None
    from members.assignment import eligible_shepherds
    from accounts.gender import can_pair
    ok = {u.id for u in eligible_shepherds(location=newcomer.location_id)}
    if newcomer.assigned_to_id in ok and can_pair(newcomer.gender, newcomer.assigned_to):
        return newcomer.assigned_to
    return None


def convert_to_member(newcomer, user):
    """
    Put a newcomer on the member roll.

    Shared by Make a member and by dragging a card to the Member column.
    Moving the stage alone left a person shown as a member on the board
    and missing from the member roll.

    The newcomer record is kept and linked rather than deleted, so their
    follow-up history stays reachable.
    """
    from members.models import Member
    existing = getattr(newcomer, "became_member", None)
    if existing:
        return existing

    # Phone numbers are unique on the member roll. A blank one must be
    # stored as nothing rather than as an empty string, or the second
    # newcomer without a phone could never become a member. A number
    # already on the roll almost certainly means this person is there
    # already, so that is reported rather than duplicated.
    phone = (newcomer.phone or "").strip() or None
    if phone:
        clash = Member.objects.filter(phone=phone).first()
        if clash:
            raise ConversionConflict(
                f"{clash.full_name} is already on the member roll with the phone number "
                f"{phone}. If this is the same person, link them rather than adding them "
                f"again.")

    parts = newcomer.name.strip().split()
    first = parts[0] if parts else newcomer.name
    surname = " ".join(parts[1:]) if len(parts) > 1 else ""

    with transaction.atomic():
        member = Member.objects.create(
            surname=surname or first, first_name=first,
            phone=phone, email=newcomer.email,
            location=newcomer.location,
            gender=newcomer.gender,
            joined_date=timezone.localdate(),
            category=Member.Category.GENERAL,
            from_newcomer=newcomer,
            # The shepherd who followed them as a newcomer keeps them, if they
            # can shepherd members there. They used to join with nobody, just
            # when they most need somebody.
            assigned_to=_shepherd_to_keep(newcomer),
        )
        newcomer.stage = Newcomer.Stage.MEMBER
        newcomer.stage_since = timezone.localdate()
        newcomer.save(update_fields=["stage", "stage_since"])
        NewcomerStatusHistory.objects.create(
            newcomer=newcomer, stage=Newcomer.Stage.MEMBER,
            note="Added to the member roll", date=timezone.localdate(),
        )

    log_audit(user, "Made a member", "Newcomer", newcomer.name,
              "Added to the member roll", instance=newcomer)
    return member



class BulkAssignNewcomersView(APIView):
    """Item 13 (Kay, 26 October 2026): give several newcomers one shepherd.
    Same rules as one at a time: someone who may shepherd, of the same
    gender, at the newcomer's location; their open tasks move too."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from accounts.gender import WORD, can_pair
        from accounts.models import User
        from accounts.names import display_name
        from accounts.permissions import require
        from alerts.events import given
        from core.task_actions import move_open_tasks
        require(request.user, ("newcomers", "can_edit"))
        ids = request.data.get("newcomer_ids") or []
        shepherd = User.objects.filter(id=request.data.get("shepherd_id"), is_active=True).first()
        if not shepherd:
            return Response({"shepherd_id": "Choose a shepherd."}, status=400)
        if not shepherd.can_shepherd:
            return Response({"shepherd_id": "That person is not set up to shepherd others. An administrator can tick "
                                            "Can shepherd others on their account."}, status=400)
        qs = Newcomer.objects.filter(id__in=ids)
        if not request.user.is_superuser and request.user.location_id:
            qs = qs.filter(location_id=request.user.location_id)
        people = list(qs)
        if not people:
            return Response({"detail": "Tick at least one newcomer."}, status=400)
        clash = [n for n in people if not can_pair(n.gender, shepherd)]
        if clash:
            names = ", ".join(f"{n.name} ({WORD.get(n.gender, 'gender not known')})" for n in clash[:5])
            return Response({"detail": f"Men follow up men and women follow up women. Not saved, because of {names}. "
                                       f"Untick them or choose someone of the same gender."}, status=400)
        elsewhere = [n for n in people if shepherd.location_id and n.location_id != shepherd.location_id]
        if elsewhere:
            return Response({"detail": f"{display_name(shepherd)} serves {shepherd.location.name} only. Not saved, "
                                       f"because {elsewhere[0].name} is at another location."}, status=400)
        newly = [("newcomer", n.id, n.name, shepherd.id) for n in people if n.assigned_to_id != shepherd.id]
        Newcomer.objects.filter(id__in=[n.id for n in people]).update(assigned_to=shepherd)
        for n in people:
            move_open_tasks(n, shepherd.id)
        given(newly, by=request.user)
        log_audit(request.user, "Bulk assigned shepherd", "Newcomer", f"{len(people)} newcomer(s)",
                  f"Assigned to {display_name(shepherd)}")
        return Response({"updated": len(people), "shepherd": display_name(shepherd)})
