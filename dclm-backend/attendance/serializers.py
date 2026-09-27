from rest_framework import serializers

from members.models import Member
from .models import Fellowship, MeetingType, AttendanceSession, AttendanceSessionMember


class MeetingTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingType
        fields = ["id", "name", "day", "frequency", "detail_level", "monthly_target",
                  "counts_for_absence", "start_time", "audience", "collects_offering",
                  "generates_sessions", "effective_target"]
        read_only_fields = ["generates_sessions", "effective_target"]

    # Short forms people naturally type, written out in full so the weekly
    # generator can read them.
    DAY_ALIASES = {
        "mon": "Monday", "tue": "Tuesday", "tues": "Tuesday", "wed": "Wednesday",
        "weds": "Wednesday", "thu": "Thursday", "thur": "Thursday", "thurs": "Thursday",
        "fri": "Friday", "sat": "Saturday", "sun": "Sunday",
    }

    def validate_day(self, value):
        raw = (value or "").strip()
        key = raw.lower().rstrip(".")
        if key in self.DAY_ALIASES:
            return self.DAY_ALIASES[key]
        for full in MeetingType.WEEKDAYS:
            if key == full.lower():
                return full
        return raw

    def validate(self, attrs):
        """
        Check the day here, where a clear message can be returned. The model
        refuses it too, but a refusal there reaches the user as a server
        error rather than as something they can act on.
        """
        frequency = attrs.get("frequency", getattr(self.instance, "frequency", ""))
        day = attrs.get("day", getattr(self.instance, "day", ""))
        if frequency == "weekly" and day not in MeetingType.WEEKDAYS:
            if "day" in attrs:
                message = (f"{day or 'A blank day'} is not a day of the week. Use one of: "
                           f"{', '.join(MeetingType.WEEKDAYS)}.")
            else:
                message = (f"This meeting's day, {day or 'blank'}, is not a day of the week, "
                           f"so nothing else can be saved until it is corrected. Set the day "
                           f"in full, such as Friday.")
            raise serializers.ValidationError({"day": message})
        return attrs


class AttendanceSessionMemberSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source="member.full_name", read_only=True)

    class Meta:
        model = AttendanceSessionMember
        fields = ["id", "member", "member_name", "mode", "checked_in_at"]
        read_only_fields = ["id", "checked_in_at"]


class AttendanceSessionSerializer(serializers.ModelSerializer):
    total = serializers.ReadOnlyField()
    online_total = serializers.ReadOnlyField()
    in_person_total = serializers.ReadOnlyField()
    meeting_type_name = serializers.CharField(source="meeting_type.name", read_only=True)
    fellowship_name = serializers.CharField(source="fellowship.name", read_only=True, default=None)
    led_by_name = serializers.CharField(source="led_by.full_name", read_only=True, default=None)
    attendees = AttendanceSessionMemberSerializer(many=True, read_only=True)

    class Meta:
        model = AttendanceSession
        fields = [
            "id", "meeting_type", "meeting_type_name", "date", "location", "mode", "status",
            "track_named", "men", "women", "youth_boys", "youth_girls",
            "children_boys", "children_girls", "total", "attendees",
        "online_men", "online_women", "online_youth_boys", "online_youth_girls",
        "online_children_boys", "online_children_girls", "online_total",
        "in_person_total", "new_comers", "new_converts",
        "fellowship", "fellowship_name", "led_by", "led_by_name", "lesson",
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
                    f: f"{meeting_type.name} records men and women only, so this must be 0."
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

    # Online attendance, kept separate from the counts above. Any meeting
    # can be hybrid and recording only the room understates the month.
    online_men = serializers.IntegerField(min_value=0, default=0)
    online_women = serializers.IntegerField(min_value=0, default=0)
    online_youth_boys = serializers.IntegerField(min_value=0, default=0)
    online_youth_girls = serializers.IntegerField(min_value=0, default=0)
    online_children_boys = serializers.IntegerField(min_value=0, default=0)
    online_children_girls = serializers.IntegerField(min_value=0, default=0)

    new_comers = serializers.IntegerField(min_value=0, default=0)
    new_converts = serializers.IntegerField(min_value=0, default=0)

    # Only meaningful for a house fellowship.
    led_by = serializers.IntegerField(required=False, allow_null=True, default=None)
    lesson = serializers.CharField(required=False, allow_blank=True, default="")

    # What was collected, by fund. Only accepted when the meeting is
    # marked as collecting an offering in Admin.
    offering = serializers.DictField(
        child=serializers.DecimalField(max_digits=12, decimal_places=3, min_value=0),
        required=False, default=dict,
        help_text='Fund name to amount, for example {"Tithe": "120.500"}.')

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


class FellowshipSerializer(serializers.ModelSerializer):
    session_count = serializers.SerializerMethodField()
    location_name = serializers.CharField(source="location.name", read_only=True, default="")

    class Meta:
        model = Fellowship
        fields = ["id", "name", "area", "location", "location_name", "meeting_type",
                  "is_active", "session_count"]

    def get_session_count(self, obj):
        return obj.sessions.count()

    def create(self, validated):
        """
        A fellowship added without a meeting joins the one the others
        hold, so it gets its own weekly session straight away. Without a
        meeting it would be created and never scheduled.

        One added without saying where it meets belongs to the person's
        own location, or the main location for an administrator. Left
        blank it would meet everywhere, and Qatar would be given a
        session for a Bahrain fellowship.
        """
        if "location" not in self.initial_data:
            from core.models import Location
            user = getattr(self.context.get("request"), "user", None)
            if user is not None and getattr(user, "location_id", None):
                validated["location"] = user.location
            else:
                validated["location"] = Location.objects.filter(is_core=True).first()
        if not validated.get("meeting_type"):
            from collections import Counter
            used = Counter(Fellowship.objects.exclude(meeting_type__isnull=True)
                           .values_list("meeting_type_id", flat=True))
            mt = (MeetingType.objects.filter(id=used.most_common(1)[0][0]).first() if used else None) \
                or MeetingType.objects.filter(id="fri-house").first() \
                or MeetingType.objects.filter(name__icontains="fellowship").first()
            if mt:
                validated["meeting_type"] = mt
        fellowship = super().create(validated)
        _schedule_first_session(fellowship)
        return fellowship


def _schedule_first_session(fellowship):
    """
    Give a new fellowship its coming session straight away, using the same
    date rule as the weekly scheduler. It used to have none until the
    scheduled job next ran, so one added on a Friday afternoon had nothing
    to record that evening.

    A location's first fellowship also replaces the plain session made for
    it before it had any, if that session is still untouched, so the
    evening is not listed twice.
    """
    from django.utils import timezone
    from core.models import Location
    from .models import AttendanceSession
    from .management.commands.generate_recurring_sessions import Command, WEEKDAY_MAP
    mt = fellowship.meeting_type
    if not mt or mt.frequency != "weekly":
        return
    weekday = WEEKDAY_MAP.get((mt.day or "").strip().lower())
    if weekday is None:
        return
    date = Command._next_occurrence(timezone.localdate(), weekday)
    places = [fellowship.location] if fellowship.location_id else list(Location.objects.all())
    for loc in places:
        AttendanceSession.objects.get_or_create(
            meeting_type=mt, location=loc, date=date, fellowship=fellowship,
            defaults={"mode": AttendanceSession.Mode.IN_PERSON,
                      "status": AttendanceSession.Status.PENDING})
        for plain in AttendanceSession.objects.filter(
                meeting_type=mt, location=loc, date=date, fellowship__isnull=True,
                status=AttendanceSession.Status.PENDING):
            if plain.total == 0 and not plain.attendees.exists() and not plain.giving.exists():
                plain.delete()
