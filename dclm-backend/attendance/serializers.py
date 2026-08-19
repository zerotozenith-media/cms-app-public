from rest_framework import serializers

from members.models import Member
from .models import MeetingType, AttendanceSession, AttendanceSessionMember


class MeetingTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingType
        fields = ["id", "name", "day", "frequency", "detail_level", "monthly_target", "counts_for_absence", "start_time"]


class AttendanceSessionMemberSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source="member.full_name", read_only=True)

    class Meta:
        model = AttendanceSessionMember
        fields = ["id", "member", "member_name", "mode", "checked_in_at"]
        read_only_fields = ["id", "checked_in_at"]


class AttendanceSessionSerializer(serializers.ModelSerializer):
    total = serializers.ReadOnlyField()
    meeting_type_name = serializers.CharField(source="meeting_type.name", read_only=True)
    attendees = AttendanceSessionMemberSerializer(many=True, read_only=True)

    class Meta:
        model = AttendanceSession
        fields = [
            "id", "meeting_type", "meeting_type_name", "date", "location", "mode", "status",
            "track_named", "men", "women", "youth_boys", "youth_girls",
            "children_boys", "children_girls", "total", "attendees",
        ]
        read_only_fields = ["id", "status"]
        # status is deliberately read-only here too , the only correct way
        # to fill a session is AttendanceSessionViewSet.record(), which sets
        # status='filled' together with the headcounts, atomically.

    def validate(self, attrs):
        # Server-side enforcement of the detailed/simple rule (Batch 0.2):
        # a "simple" meeting only ever has Men/Women , reject youth/children
        # counts rather than silently accepting and ignoring them.
        meeting_type = attrs.get("meeting_type") or getattr(self.instance, "meeting_type", None)
        if meeting_type and meeting_type.detail_level == MeetingType.DetailLevel.SIMPLE:
            youth_children_fields = ["youth_boys", "youth_girls", "children_boys", "children_girls"]
            offending = [f for f in youth_children_fields if attrs.get(f)]
            if offending:
                raise serializers.ValidationError({
                    f: f"{meeting_type.name} is a simple (Men/Women only) meeting , "
                       f"this field must be 0."
                    for f in offending
                })
        return attrs


class RecordAttendanceSerializer(serializers.Serializer):
    """
    Payload for AttendanceSessionViewSet.record() , the dedicated action
    for filling in a session's actual numbers, bundling the headcount
    save, the status flip to 'filled', and (optionally) named attendance
    into one atomic action. Mirrors the same pattern as Member.move_category.
    """
    men = serializers.IntegerField(min_value=0, default=0)
    women = serializers.IntegerField(min_value=0, default=0)
    youth_boys = serializers.IntegerField(min_value=0, default=0)
    youth_girls = serializers.IntegerField(min_value=0, default=0)
    children_boys = serializers.IntegerField(min_value=0, default=0)
    children_girls = serializers.IntegerField(min_value=0, default=0)
    track_named = serializers.BooleanField(default=False)
    attendee_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list,
        help_text="Member IDs present. No location restriction, per Batch 0.2.",
    )

    def validate_attendee_ids(self, value):
        existing = set(Member.objects.filter(id__in=value).values_list("id", flat=True))
        missing = set(value) - existing
        if missing:
            raise serializers.ValidationError(f"Unknown member id(s): {sorted(missing)}")
        return value
