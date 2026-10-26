"""
The follow-up actions on a task, shared by member and newcomer tasks
(Kay, 26 October 2026): record a result, cancel a task made in error, and
change a due time. See core/task_actions.py for the rules.
"""
from django.utils.dateparse import parse_datetime
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from accounts.permissions import require
from . import task_actions as acts

RESULTS = ["reached", "tried", "known-reason", "needs-coordinator", "moved-away"]


class AccountableFieldsMixin(serializers.Serializer):
    """Read-only fields every task shows: what kind it is, its exact due
    time, whether it is late, how it ended and its attempts."""
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    result_label = serializers.CharField(source="get_result_display", read_only=True)
    escalation_label = serializers.CharField(source="get_escalation_display", read_only=True)
    is_late = serializers.SerializerMethodField()
    attempts = serializers.SerializerMethodField()

    needs_reason = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()

    ACCOUNTABLE = ["kind", "kind_label", "created_at", "clock_start", "due_at", "is_late", "result",
                   "result_label", "result_note", "closed_at", "missed_in_row", "escalation",
                   "escalation_label", "escalated_at", "covered_by", "attempts", "needs_reason",
                   "handed_from", "reviews"]

    def get_needs_reason(self, obj):
        from .followup_review import needs_reason
        from .followup_rules import rules
        if obj.done or not obj.clock_start:
            return False
        if not hasattr(self, "_rules"):
            self._rules = rules()   # once per list, not once per task
        return needs_reason(obj, None, self._rules)

    def get_reviews(self, obj):
        """Every reason and decision, kept on the task so the record can be read later."""
        from accounts.names import display_name
        return [{"reason": r.get_reason_display(), "reason_note": r.reason_note, "new_date": r.new_date,
                 "given_by": display_name(r.given_by) if r.given_by_id else "", "given_at": r.given_at,
                 "choice": r.get_choice_display(), "choice_note": r.choice_note,
                 "handed_to": display_name(r.handed_to) if r.handed_to_id else "",
                 "decided_by": display_name(r.decided_by) if r.decided_by_id else "", "decided_at": r.decided_at}
                for r in obj.reviews.all()]

    def get_is_late(self, obj):
        from django.utils import timezone
        if obj.done:
            return False
        if obj.due_at:
            return obj.due_at < timezone.now()
        return obj.due_date < timezone.localdate()

    def get_attempts(self, obj):
        from accounts.names import display_name
        return [{"id": a.id, "date": a.date, "at": a.at, "method": a.method, "note": a.note,
                 "by": display_name(a.by) if a.by_id else ""} for a in obj.attempts.all()]


class RecordResultSerializer(serializers.Serializer):
    result = serializers.ChoiceField(choices=RESULTS)
    # Reached
    contact_date = serializers.DateField(required=False)
    contact_method = serializers.CharField(required=False, allow_blank=True)
    contact_goal = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    contact_scripture = serializers.CharField(required=False, allow_blank=True, max_length=300)
    contact_root_cause = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    contact_next_step = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    next_step_date = serializers.DateField(required=False, allow_null=True)
    # Tried, could not reach
    method = serializers.CharField(required=False, allow_blank=True)
    # Known reason, needs the coordinator, moved away
    note = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    away_from = serializers.DateField(required=False, allow_null=True)
    away_to = serializers.DateField(required=False, allow_null=True)
    away_reason = serializers.CharField(required=False, allow_blank=True)

    REACHED_NEEDS = {
        "contact_method": "Choose how you reached them.",
        "contact_goal": "Say what the goal of the visit was.",
        "contact_scripture": 'Say which scripture was shared, or "None this time".',
        "contact_root_cause": "Say what the root cause was.",
        "contact_next_step": "Say what the next step is.",
    }

    def validate(self, attrs):
        if attrs["result"] == "reached":
            missing = {f: msg for f, msg in self.REACHED_NEEDS.items() if not (attrs.get(f) or "").strip()}
            if missing:
                raise ValidationError(missing)
        return attrs


class TaskActionsMixin:
    """Mixed into MemberFollowUpTaskViewSet and NewcomerTaskViewSet, which
    set `module` to members or newcomers."""

    ACTIONS = ("record_result", "give_reason", "cancel", "change_due", "complete")

    def get_permissions(self):
        # These check their own rules inside: the module's edit right, or
        # being a Follow-up Coordinator for the person's location, who
        # records visits on tasks they took even with a view-only role.
        if getattr(self, "action", None) in self.ACTIONS:
            from rest_framework.permissions import IsAuthenticated
            return [IsAuthenticated()]
        return super().get_permissions()

    def _may_record(self, request, task):
        from accounts.permissions import user_has
        from .followup_access import can_review
        if not (user_has(request.user, self.module, "can_edit") or can_review(request.user, acts.location_id(task))):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Your role does not allow this.")

    def _method_choices(self, task):
        return dict(type(task).Method.choices)

    @action(detail=True, methods=["post"], url_path="give-reason")
    def give_reason(self, request, pk=None):
        """A reason and a new date for a late task. Each late task needs its
        own reason, even for the same person (Kay, 26 October 2026)."""
        from .followup_review import give_reason
        task = self.get_object()
        nd = request.data.get("new_date")
        from django.utils.dateparse import parse_date
        give_reason(task, request.user, request.data.get("reason"), request.data.get("note", ""),
                    parse_date(nd) if isinstance(nd, str) else None)
        task.refresh_from_db()
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=["post"], url_path="record-result")
    def record_result(self, request, pk=None):
        task = self.get_object()
        self._may_record(request, task)
        block_until_reasons(request.user, task)
        ser = RecordResultSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        result = d["result"]
        extra = {}
        if result == "reached":
            if d["contact_method"] not in self._method_choices(task):
                raise ValidationError({"contact_method": "Choose how you reached them."})
            extra = acts.reached(task, request.user, d)
        elif result == "tried":
            extra = {"attempt_count": acts.tried(task, request.user, d.get("method"), d.get("note", ""))}
        elif result == "known-reason":
            acts.known_reason(task, request.user, d.get("note"), d.get("away_from"), d.get("away_to"),
                              d.get("away_reason", ""))
        elif result == "needs-coordinator":
            acts.needs_coordinator(task, request.user, d.get("note"))
        elif result == "moved-away":
            acts.moved_away(task, request.user, d.get("note", ""))
        task.refresh_from_db()
        data = dict(self.get_serializer(task).data)
        data.update(extra)
        return Response(data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        task = self.get_object()
        acts.cancel(task, request.user, request.data.get("reason"), request.data.get("note", ""))
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=["post"], url_path="change-due")
    def change_due(self, request, pk=None):
        from django.utils import timezone
        task = self.get_object()
        raw = request.data.get("due_at") or ""
        due = parse_datetime(raw)
        if due is None:
            raise ValidationError({"due_at": "Give the new due date and time."})
        if timezone.is_naive(due):
            due = timezone.make_aware(due)
        acts.change_due(task, request.user, due, request.data.get("why"))
        return Response(self.get_serializer(task).data)


class AwaySerializer(serializers.Serializer):
    away_from = serializers.DateField()
    away_to = serializers.DateField()
    away_reason = serializers.ChoiceField(choices=["travelling", "sick", "shift-abroad", "other"])
    away_note = serializers.CharField(required=False, allow_blank=True, max_length=300)


def away_action(view, request, person, module):
    """POST marks someone away, DELETE clears it. Their shepherd, a
    Follow-up Coordinator or an administrator can do it."""
    from rest_framework.exceptions import PermissionDenied
    from .followup_access import can_manage_task
    require(request.user, (module, "can_edit"))
    if person.assigned_to_id != request.user.id and not can_manage_task(request.user, person.location_id):
        raise PermissionDenied("Only their shepherd, a Follow-up Coordinator or an administrator can mark "
                               "someone away, so nobody else's people stop being followed up by mistake.")
    if request.method == "DELETE":
        acts.clear_away(person, request.user)
    else:
        ser = AwaySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        acts.set_away(person, request.user, d["away_from"], d["away_to"], d["away_reason"], d.get("away_note", ""))
    return Response({"away_from": person.away_from, "away_to": person.away_to,
                     "away_reason": person.away_reason, "away_note": person.away_note})


def block_until_reasons(user, task):
    """A shepherd gives a reason for each of their late tasks before
    recording anything else, because the Follow-up Coordinator reviews them
    (Kay, 26 October 2026). Someone recording on another shepherd's task,
    such as a Follow-up Coordinator, is not held up."""
    if task.assigned_to_id != user.id:
        return
    from .followup_review import my_followup
    n = my_followup(user)["needs_reason"]
    if n:
        raise ValidationError({"detail": f"{n} of your late task{'s need' if n != 1 else ' needs'} a reason first. "
                                         f"Give a reason and a new date for each, then record this result. Your "
                                         f"Follow-up Coordinator reviews them."})
