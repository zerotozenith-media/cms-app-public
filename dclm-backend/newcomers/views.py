from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from accounts.audit import log_audit
from accounts.permissions import ModulePermission, LocationScopedQuerySetMixin
from .intake import match_invited_by_member, create_auto_tasks
from .models import (
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
        create_auto_tasks(instance)

    def perform_destroy(self, instance):
        name = instance.name
        log_audit(self.request.user, "Deleted", "Newcomer", name)
        instance.delete()

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
        newcomer = self.get_object()
        serializer = ChangeStageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        to_stage = serializer.validated_data["to_stage"]
        note = serializer.validated_data["note"]
        from_stage = newcomer.stage
        today = timezone.localdate()

        if to_stage == from_stage:
            return Response({"detail": f"Newcomer is already {to_stage}."}, status=400)

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

        return Response(NewcomerSerializer(newcomer).data)

    @action(detail=True, methods=["post"], url_path="set-milestone")
    def set_milestone(self, request, pk=None):
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


class NewcomerTaskViewSet(viewsets.ModelViewSet):
    module = "newcomers"
    permission_classes = [ModulePermission]
    queryset = NewcomerTask.objects.select_related("newcomer", "assigned_to")
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
        task = self.get_object()
        serializer = CompleteNewcomerTaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        task.done = True
        task.contact_date = data.get("contact_date") or timezone.localdate()
        task.contact_method = data["contact_method"]
        task.contact_goal = data["contact_goal"]
        task.contact_scripture = data["contact_scripture"]
        task.contact_root_cause = data["contact_root_cause"]
        task.contact_next_step = data["contact_next_step"]
        task.save()
        log_audit(
            request.user, "Recorded follow-up outcome", "Newcomer", task.newcomer.name,
            f"{task.contact_method}: {task.contact_goal[:60]}", instance=task,
        )
        return Response(NewcomerTaskSerializer(task).data)


class NewcomerStatusHistoryViewSet(viewsets.ModelViewSet):
    module = "newcomers"
    permission_classes = [ModulePermission]
    queryset = NewcomerStatusHistory.objects.select_related("newcomer")
    serializer_class = NewcomerStatusHistorySerializer


# --- Public QR self-registration (no authentication) ---

REGISTRATION_MIN_SUBMIT_SECONDS = 2.0
REGISTRATION_RATE_LIMIT_WINDOW_HOURS = 24
REGISTRATION_MAX_PER_IP = 5  # generous enough for one family submitting multiple members from a shared phone

GENERIC_REGISTRATION_ERROR = {"detail": "We couldn't process your submission. Please see a leader at the welcome desk."}


def _get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


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

    def reject(reason, response_status=status.HTTP_400_BAD_REQUEST):
        PublicRegistrationAttempt.objects.create(ip_address=ip, successful=False, reason=reason)
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

    window_start = timezone.now() - timedelta(hours=REGISTRATION_RATE_LIMIT_WINDOW_HOURS)
    recent_count = PublicRegistrationAttempt.objects.filter(
        ip_address=ip, successful=True, timestamp__gte=window_start,
    ).count()
    if recent_count >= REGISTRATION_MAX_PER_IP:
        return reject(PublicRegistrationAttempt.Reason.RATE_LIMITED, status.HTTP_429_TOO_MANY_REQUESTS)

    serializer = PublicRegistrationSerializer(data=request.data)
    if not serializer.is_valid():
        PublicRegistrationAttempt.objects.create(
            ip_address=ip, successful=False, reason=PublicRegistrationAttempt.Reason.INVALID_DATA,
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    from core.models import Location
    bahrain = Location.objects.get(id="bahrain")
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
            wants_salvation_info=data["wants_salvation_info"],
            invited_by_member=invited_by_member, invited_by_name=data["invited_by_name"],
        )
        create_auto_tasks(newcomer)
        log_audit(None, "Created (QR self-registration)", "Newcomer", newcomer.name, instance=newcomer)
        PublicRegistrationAttempt.objects.create(ip_address=ip, successful=True, reason=PublicRegistrationAttempt.Reason.SUCCESS)

    return Response({"detail": "Thank you! Someone from our team will be in touch soon."}, status=status.HTTP_201_CREATED)
