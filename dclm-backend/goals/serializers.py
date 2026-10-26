from rest_framework import serializers

from .calculations import compute_goal_value
from .models import Goal


class GoalSerializer(serializers.ModelSerializer):
    current_value = serializers.SerializerMethodField()
    calculation_error = serializers.SerializerMethodField()
    measure_note = serializers.SerializerMethodField()

    PICK = {"sessions_held": "calculation_meeting_type", "monthly_average_attendance": "calculation_meeting_type",
            "latest_session_total": "calculation_meeting_type", "named_checkins": "calculation_meeting_type",
            "fund_total": "calculation_fund"}
    PICK_WORDS = {"calculation_meeting_type": "Choose the meeting.", "calculation_fund": "Choose the fund."}

    def validate(self, attrs):
        """Item 11: an automatic goal says what it measures."""
        get = lambda f: attrs.get(f, getattr(self.instance, f, None))
        if get("tracking") == Goal.Tracking.AUTO:
            calc = get("calculation_type")
            if not calc:
                raise serializers.ValidationError({"calculation_type": "Choose what it measures."})
            need = self.PICK.get(calc)
            if need and not get(need):
                raise serializers.ValidationError({need: self.PICK_WORDS[need]})
        return attrs

    def get_measure_note(self, obj):
        """What an automatic goal counts, in words, under the goal."""
        if obj.tracking != Goal.Tracking.AUTO or not obj.calculation_type:
            return ""
        where = f" at {obj.calculation_location.name}" if obj.calculation_location_id else " at all locations"
        when = {"month": " this month", "quarter": " this quarter", "year": " this year"}.get(obj.period_type, "")
        meeting = obj.calculation_meeting_type.name if obj.calculation_meeting_type_id else "the meeting"
        return {
            "sessions_held": f"{meeting} sessions held{when}{where}",
            "monthly_average_attendance": f"Average attendance at {meeting} this month{where}",
            "latest_session_total": f"Attendance at the latest {meeting}{where}",
            "named_checkins": f"Different people checked in by name at {meeting}{when}{where}",
            "fund_total": f"{obj.calculation_fund.name if obj.calculation_fund_id else 'Fund'} giving{when}{where}",
            "net_giving": f"Giving less expenses{when}{where}",
        }.get(obj.calculation_type, obj.get_calculation_type_display())

    class Meta:
        model = Goal
        fields = [
            "id", "horizon", "name", "target", "current", "unit", "tracking",
            "target_date", "measured_by",
            "period_type", "source", "link_route", "link_tab",
            "calculation_type", "calculation_meeting_type",
            "calculation_target_category", "calculation_milestone_type",
            "calculation_location", "calculation_fund", "measure_note",
            "current_value", "calculation_error",
        ]

    def get_current_value(self, obj):
        if obj.tracking == Goal.Tracking.MANUAL:
            return obj.current
        computed = compute_goal_value(obj)
        return computed if computed is not None else obj.current

    def get_calculation_error(self, obj):
        # Surfaces a real config gap (auto-tracked but no calculation_type
        # set, or missing a required reference) rather than silently
        # showing 0 and letting it look like genuine data.
        if obj.tracking != Goal.Tracking.AUTO:
            return None
        if not obj.calculation_type:
            return "Auto-tracked goal has no calculation_type configured."
        if compute_goal_value(obj) is None:
            return "Calculation is missing a required reference (meeting type, category, or milestone type)."
        return None
