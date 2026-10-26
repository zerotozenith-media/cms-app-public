from rest_framework import serializers

from members.models import Member
from .models import Fellowship, MeetingType, AttendanceSession, AttendanceSessionMember


class MeetingTypeSerializer(serializers.ModelSerializer):
    held_at_names = serializers.SerializerMethodField()
    setup_warnings = serializers.SerializerMethodField()

    class Meta:
        model = MeetingType
        fields = ["id", "name", "day", "frequency", "detail_level", "monthly_target",
                  "counts_for_absence", "start_time", "audience", "collects_offering",
                  "generates_sessions", "effective_target", "usual_mode",
                  "create_days_ahead", "held_at", "held_at_names", "setup_warnings"]
        read_only_fields = ["generates_sessions", "effective_target"]
        extra_kwargs = {"held_at": {"required": False}}

    def get_held_at_names(self, obj):
        # None ticked means every location.
        return [l.name for l in obj.held_locations()]

    def get_setup_warnings(self, obj):
        """What stops this meeting working as its ticks suggest, said on its
        row (review item A3). Ticking Follows up absence did nothing without
        a start time, and no screen said so."""
        out = []
        if obj.counts_for_absence and not obj.start_time:
            out.append("Follows up absence but has no start time, so nobody missing it is "
                       "followed up. Set a start time.")
        return out

    def validate_create_days_ahead(self, value):
        if value is not None and value > 14:
            raise serializers.ValidationError(
                "Sessions can be created at most 14 days ahead, so they never fill the list "
                "with services weeks away.")
        return value


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
    member_name = serializers.CharField(source="member.full_name", read_only=True, default=None)
    # A row holds a member or a newcomer, never both.
    newcomer_name = serializers.CharField(source="newcomer.name", read_only=True, default=None)

    class Meta:
        model = AttendanceSessionMember
        fields = ["id", "member", "member_name", "newcomer", "newcomer_name", "mode", "checked_in_at"]
        read_only_fields = ["id", "checked_in_at"]


class AttendanceSessionSerializer(serializers.ModelSerializer):
    total = serializers.ReadOnlyField()
    online_total = serializers.ReadOnlyField()
    in_person_total = serializers.ReadOnlyField()
    meeting_type_name = serializers.CharField(source="meeting_type.name", read_only=True)
    fellowship_name = serializers.CharField(source="fellowship.name", read_only=True, default=None)
    led_by_name = serializers.CharField(source="led_by.full_name", read_only=True, default=None)
    attendees = AttendanceSessionMemberSerializer(many=True, read_only=True)
    # So the check-in screen can say when ticking names late will make
    # absence follow-up tasks for those not ticked.
    counts_for_absence = serializers.BooleanField(source="meeting_type.counts_for_absence", read_only=True)
    # Item 20: the status word shown in Attendance, so a session made early
    # reads Upcoming rather than Pending.
    state = serializers.SerializerMethodField()
    state_label = serializers.SerializerMethodField()
    # Names ticked after the absence check ran: shown on the check-in
    # screen with when the tasks will be due (Kay, 26 October 2026).
    late_entry = serializers.SerializerMethodField()
    # O1: the offering as saved, so reopening the form shows it.
    offering = serializers.SerializerMethodField()

    def get_offering(self, obj):
        from decimal import Decimal
        out = {}
        for g in obj.giving.select_related("fund").all():
            out[g.fund.name] = out.get(g.fund.name, Decimal("0")) + g.amount
        return {k: f"{v:.3f}" for k, v in out.items()}

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
        "edition_name", "edition_place", "counts_for_absence",
        "state", "state_label", "not_held_reason", "late_entry", "offering",
        ]
        read_only_fields = ["id", "status", "not_held_reason"]
        # status is deliberately read-only here too , the only correct way
        # to fill a session is AttendanceSessionViewSet.record(), which sets
        # status='filled' together with the headcounts, atomically.

    def _rules(self):
        if not hasattr(self, "_rules_cache"):
            from core.followup_rules import rules
            self._rules_cache = rules()
        return self._rules_cache

    def get_state(self, obj):
        from core.followup_rules import session_state
        return session_state(obj, r=self._rules())

    def get_late_entry(self, obj):
        """None, or the hours shepherds get from when the tasks are made."""
        from django.utils import timezone
        from core.followup_rules import check_time
        mt = obj.meeting_type
        if not (mt.counts_for_absence and mt.start_time) or obj.status == "did-not-hold":
            return None
        r = self._rules()
        ran = check_time(mt, obj.date, r)
        if timezone.now() < ran or (timezone.localdate() - obj.date).days > 7:
            return None
        return {"check_ran": ran, "due_hours": r.due_hours}

    def get_state_label(self, obj):
        from core.followup_rules import STATE_LABELS
        return STATE_LABELS[self.get_state(obj)]

    def validate(self, attrs):
        # Review item O4: a second session for the same meeting, date,
        # location and fellowship was accepted, doubled the dashboard
        # totals, and its untouched twin stayed Pending.
        if self.instance is None:
            mt = attrs.get("meeting_type")
            twin = AttendanceSession.objects.filter(
                meeting_type=mt, date=attrs.get("date"), location=attrs.get("location"),
                fellowship=attrs.get("fellowship")).first() if mt else None
            if twin:
                raise serializers.ValidationError({
                    "detail": f"{twin.meeting_type.name} at {twin.location.name} on "
                              f"{twin.date:%A %-d %B} already exists. Open it to record attendance "
                              f"instead of adding a second one, which would count the service twice.",
                    "existing_id": twin.id})
        # F22: only occasional meetings have editions.
        mt = attrs.get("meeting_type") or getattr(self.instance, "meeting_type", None)
        for f in ("edition_name", "edition_place"):
            if f in attrs:
                attrs[f] = (attrs[f] or "").strip()
                if attrs[f] and mt and mt.frequency != MeetingType.Frequency.OCCASIONAL:
                    raise serializers.ValidationError({f: f"{mt.name} meets every week, so it has no edition. Editions are for occasional meetings such as GCK."})
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
    edition_name = serializers.CharField(required=False, allow_blank=True, max_length=120)
    edition_place = serializers.CharField(required=False, allow_blank=True, max_length=120)
    mode = serializers.ChoiceField(required=False, choices=["in-person", "online", "in-person-and-online"])

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
    today = timezone.localdate()
    date = Command._next_occurrence(today, weekday)
    # The same rule as the nightly run: only once the meeting is within its
    # "Create each session" days, and only where it is held.
    if (date - today).days > (mt.create_days_ahead or 0):
        return
    held = mt.held_locations()
    places = [fellowship.location] if fellowship.location_id else held
    places = [p for p in places if p in held]
    for loc in places:
        AttendanceSession.objects.get_or_create(
            meeting_type=mt, location=loc, date=date, fellowship=fellowship,
            defaults={"mode": mt.usual_mode,
                      "status": AttendanceSession.Status.PENDING})
        for plain in AttendanceSession.objects.filter(
                meeting_type=mt, location=loc, date=date, fellowship__isnull=True,
                status=AttendanceSession.Status.PENDING):
            if plain.total == 0 and not plain.attendees.exists() and not plain.giving.exists():
                plain.delete()
