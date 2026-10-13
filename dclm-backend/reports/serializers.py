from rest_framework import serializers

from .models import Service, Department, Testimony, WeeklyNote, Report


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name"]


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name"]


class TestimonySerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = Testimony
        fields = ["id", "member_name", "is_anonymous", "date", "service", "service_name", "text"]


class WeeklyNoteSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = WeeklyNote
        fields = [
            "id", "department", "department_name", "week_label", "week_start",
            "highlights", "challenges", "prayer_points",
        ]


class ReportSerializer(serializers.ModelSerializer):
    # Blank means the whole church.
    location_name = serializers.CharField(source="location.name", read_only=True, default="")
    generated_by_name = serializers.CharField(source="generated_by.email", read_only=True)
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    period_label = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            "id", "kind", "kind_label", "start_month", "start_year", "period_month", "period_year",
            "period_label", "generated_by", "generated_by_name",
            "generated_at", "other_additions", "pdf_file", "location", "location_name",
            "summary", "challenges", "training", "conclusion",
        ]
        read_only_fields = ["id", "generated_by", "generated_at", "pdf_file", "location"]
        # Reports are only ever created via the generate action, never a
        # plain POST , pdf_file, generated_by, and generated_at all need
        # to be set together, correctly, by that action.


    def get_period_label(self, obj):
        from .church_data import month_list, period_words
        y, m = obj.first_month
        return period_words(month_list((y, m), (obj.period_year, obj.period_month)))[2]


MAX_MONTHS = 12


class GenerateReportSerializer(serializers.Serializer):
    """Which report, and for which months. from_* and to_* are the first and
    last month. period_* alone, as older screens send, means one month."""
    kind = serializers.ChoiceField(choices=Report.Kind.choices, default=Report.Kind.OVERSEER)
    from_month = serializers.IntegerField(min_value=1, max_value=12, required=False)
    from_year = serializers.IntegerField(min_value=2020, max_value=2100, required=False)
    to_month = serializers.IntegerField(min_value=1, max_value=12, required=False)
    to_year = serializers.IntegerField(min_value=2020, max_value=2100, required=False)
    period_month = serializers.IntegerField(min_value=1, max_value=12, required=False)
    period_year = serializers.IntegerField(min_value=2020, max_value=2100, required=False)
    other_additions = serializers.CharField(required=False, allow_blank=True, default="")
    summary = serializers.CharField(required=False, allow_blank=True, default="", max_length=6000)
    challenges = serializers.CharField(required=False, allow_blank=True, default="", max_length=6000)
    training = serializers.CharField(required=False, allow_blank=True, default="", max_length=6000)
    conclusion = serializers.CharField(required=False, allow_blank=True, default="", max_length=6000)

    def validate(self, d):
        from django.utils import timezone
        if d.get("to_month") is None and d.get("period_month") is not None:
            d["to_month"], d["to_year"] = d["period_month"], d.get("period_year")
        if d.get("from_month") is None:
            d["from_month"], d["from_year"] = d.get("to_month"), d.get("to_year")
        if not all(d.get(k) for k in ("from_month", "from_year", "to_month", "to_year")):
            raise serializers.ValidationError({"detail": "Choose the first and last month."})
        start, end = (d["from_year"], d["from_month"]), (d["to_year"], d["to_month"])
        if start > end:
            raise serializers.ValidationError({"detail": "The first month must come before the last month."})
        today = timezone.localdate()
        if end > (today.year, today.month):
            raise serializers.ValidationError({"detail": "That month has not started yet."})
        months = (end[0] - start[0]) * 12 + end[1] - start[1] + 1
        if months > MAX_MONTHS:
            raise serializers.ValidationError({"detail": f"A report can cover up to {MAX_MONTHS} months."})
        d["start"], d["end"] = start, end
        return d
