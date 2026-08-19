import datetime

from django.utils import timezone
from rest_framework import serializers

from attendance.models import MeetingType
from accounts.names import display_name
from .models import (
    NewcomerSource, MilestoneType, Newcomer, NewcomerStatusHistory,
    NewcomerMilestone, NewcomerTask, FollowUpUrgencySetting,
)


class NewcomerSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewcomerSource
        fields = ["id", "name"]


class MilestoneTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MilestoneType
        fields = ["id", "name"]


class FollowUpUrgencySettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUpUrgencySetting
        fields = ["id", "stage", "amber_days", "red_days"]


class NewcomerStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = NewcomerStatusHistory
        fields = ["id", "newcomer", "stage", "note", "date"]
        read_only_fields = ["id"]
        # Deliberately fully editable, not append-only , same corrections
        # rule already established for MemberCategoryHistory (Batch 0.1).


class NewcomerTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewcomerTask
        fields = [
            "id", "newcomer", "text", "due_date", "done", "assigned_to",
            "contact_date", "contact_method", "contact_notes",
            "contact_goal", "contact_scripture", "contact_root_cause", "contact_next_step",
        ]
        read_only_fields = [
            "id", "done", "contact_date", "contact_method", "contact_notes",
            "contact_goal", "contact_scripture", "contact_root_cause", "contact_next_step",
        ]
        # done (and the log fields alongside it) are deliberately read-only
        # here , same principle as Member.category and Newcomer.stage
        # elsewhere in this codebase. A checked box with no record of what
        # was discussed isn't useful, so the only correct way to complete
        # a task is NewcomerTaskViewSet.complete(), which requires the
        # visitation outcome and sets done=True together, atomically.

    def create(self, validated_data):
        # Batch 0.3, Finding 3: defaults to the newcomer's primary leader
        # if not explicitly set on the task itself.
        if not validated_data.get("assigned_to"):
            validated_data["assigned_to"] = validated_data["newcomer"].assigned_to
        return super().create(validated_data)


class CompleteNewcomerTaskSerializer(serializers.Serializer):
    """The visitation outcome a leader actually needs recorded. Kept
    separate from the equivalent Member serializer (rather than shared
    across apps) for the same reason the Method choices themselves are
    duplicated, not shared , members is more foundational than newcomers,
    and a shared-serializer import would run the dependency backwards."""
    contact_date = serializers.DateField(required=False)
    contact_method = serializers.ChoiceField(choices=NewcomerTask.Method.choices)
    contact_goal = serializers.CharField(allow_blank=False, trim_whitespace=True)
    contact_scripture = serializers.CharField(allow_blank=False, trim_whitespace=True, max_length=300)
    contact_root_cause = serializers.CharField(allow_blank=False, trim_whitespace=True)
    contact_next_step = serializers.CharField(allow_blank=False, trim_whitespace=True)


class MilestoneStatusSerializer(serializers.Serializer):
    """
    Read-only view of every current MilestoneType against this newcomer ,
    computed dynamically rather than requiring a stored row per type per
    newcomer, so a newly-added MilestoneType (Batch 0.3, Finding 2: these
    are now admin-configurable) automatically shows up for every existing
    newcomer without any backfill step.
    """
    milestone_type_id = serializers.IntegerField()
    name = serializers.CharField()
    achieved_date = serializers.DateField(allow_null=True)


class NewcomerSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    days_in_stage = serializers.SerializerMethodField()
    urgency = serializers.SerializerMethodField()
    milestones = serializers.SerializerMethodField()
    open_tasks_count = serializers.SerializerMethodField()
    meeting_attended_name = serializers.CharField(source="meeting_attended.name", read_only=True, default=None)
    invited_by_member_name = serializers.CharField(source="invited_by_member.full_name", read_only=True, default=None)

    class Meta:
        model = Newcomer
        fields = [
            "id", "name", "source", "source_name", "stage", "assigned_to", "assigned_to_name",
            "location", "created_at", "stage_since", "not_interested_note",
            "days_in_stage", "urgency", "milestones", "open_tasks_count",
            # Real intake-slip fields (both paper and QR self-registration
            # must capture the same set, matching the physical slip)
            "address", "city_governorate", "phone", "email", "gender", "age_group",
            "prayer_request", "meeting_attended", "meeting_attended_name",
            "is_first_timer", "is_new_resident",
            "wants_visit", "wants_to_know_more", "wants_salvation_info",
            "invited_by_member", "invited_by_member_name", "invited_by_name",
        ]
        read_only_fields = ["id", "stage", "stage_since", "created_at", "not_interested_note", "invited_by_member"]
        # stage is read-only for the same reason category/status are elsewhere:
        # the only correct way to change it is change_stage(), which bundles
        # the field update with a NewcomerStatusHistory entry atomically.
        # invited_by_member is read-only here too , it's resolved automatically
        # from invited_by_name at creation time (NewcomerViewSet.perform_create),
        # never set directly, so a client can't silently misattribute a referral.

    def get_assigned_to_name(self, obj):
        return display_name(obj.assigned_to) if obj.assigned_to else None

    def get_days_in_stage(self, obj):
        return (timezone.localdate() - obj.stage_since).days

    def get_urgency(self, obj):
        # Real N+1 caught in Phase 4.1 testing against realistic data
        # volume: this queried FollowUpUrgencySetting fresh for every
        # single newcomer in a list , invisible with 2-3 test records,
        # but 55 extra queries against a real-sized pipeline. It's a
        # tiny, rarely-changing table (one row per stage), so it's
        # fetched once and cached on this serializer instance , safe
        # because DRF reuses one child-serializer instance across every
        # item in a single list response (many=True), so the cache
        # never crosses requests.
        days = self.get_days_in_stage(obj)
        if not hasattr(self, "_urgency_settings_cache"):
            self._urgency_settings_cache = {s.stage: s for s in FollowUpUrgencySetting.objects.all()}
        setting = self._urgency_settings_cache.get(obj.stage)
        if not setting:
            return "green"
        if days >= setting.red_days:
            return "red"
        if days >= setting.amber_days:
            return "amber"
        return "green"

    def get_milestones(self, obj):
        # Same fix as get_urgency , MilestoneType was being re-queried
        # per newcomer despite being a tiny, static table.
        if not hasattr(self, "_milestone_types_cache"):
            self._milestone_types_cache = list(MilestoneType.objects.all())
        existing = {m.milestone_type_id: m.achieved_date for m in obj.milestones.all()}
        return [
            {"milestone_type_id": mt.id, "name": mt.name, "achieved_date": existing.get(mt.id)}
            for mt in self._milestone_types_cache
        ]

    def get_open_tasks_count(self, obj):
        # obj.tasks was prefetched by the viewset's queryset, but
        # .filter() on a related manager always issues a fresh query ,
        # it silently bypasses the prefetch cache, which only serves
        # exact .all() calls. Filtering in Python instead correctly
        # reuses what was already fetched.
        return sum(1 for t in obj.tasks.all() if not t.done)


class ChangeStageSerializer(serializers.Serializer):
    to_stage = serializers.ChoiceField(choices=Newcomer.Stage.choices)
    note = serializers.CharField(required=False, allow_blank=True, default="")


class SetMilestoneSerializer(serializers.Serializer):
    milestone_type = serializers.PrimaryKeyRelatedField(queryset=MilestoneType.objects.all())
    achieved = serializers.BooleanField()
    achieved_date = serializers.DateField(required=False, default=None)


class PublicRegistrationSerializer(serializers.Serializer):
    """
    The real intake-slip fields, for the public QR self-registration
    endpoint. Deliberately excludes location, source, stage, and
    assigned_to , all auto-set server-side, never accepted from an
    unauthenticated public submission.
    """
    name = serializers.CharField(max_length=150)
    address = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")
    city_governorate = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    gender = serializers.ChoiceField(choices=Newcomer.Gender.choices, required=False, allow_blank=True, default="")
    age_group = serializers.ChoiceField(choices=Newcomer.AgeGroup.choices, required=False, allow_blank=True, default="")
    prayer_request = serializers.CharField(required=False, allow_blank=True, default="")
    meeting_attended = serializers.PrimaryKeyRelatedField(
        queryset=MeetingType.objects.all(), required=False, allow_null=True, default=None,
    )
    is_first_timer = serializers.BooleanField(default=False)
    is_new_resident = serializers.BooleanField(default=False)
    wants_visit = serializers.BooleanField(default=False)
    wants_to_know_more = serializers.BooleanField(default=False)
    wants_salvation_info = serializers.BooleanField(default=False)
    invited_by_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")

    # Security fields, same pattern as the login form (Batch 1.4 / 3.2) ,
    # a real human never sees or fills these.
    website = serializers.CharField(required=False, allow_blank=True, default="")
    form_loaded_at = serializers.CharField(required=False, allow_blank=True, default="")
