from rest_framework import serializers

from .calculations import compute_goal_value
from .models import Goal


class GoalSerializer(serializers.ModelSerializer):
    current_value = serializers.SerializerMethodField()
    calculation_error = serializers.SerializerMethodField()

    class Meta:
        model = Goal
        fields = [
            "id", "horizon", "name", "target", "current", "unit", "tracking",
            "period_type", "source", "link_route", "link_tab",
            "calculation_type", "calculation_meeting_type",
            "calculation_target_category", "calculation_milestone_type",
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
