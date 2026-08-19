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
    generated_by_name = serializers.CharField(source="generated_by.email", read_only=True)

    class Meta:
        model = Report
        fields = [
            "id", "period_month", "period_year", "generated_by", "generated_by_name",
            "generated_at", "other_additions", "pdf_file",
        ]
        read_only_fields = ["id", "generated_by", "generated_at", "pdf_file"]
        # Reports are only ever created via the generate action, never a
        # plain POST , pdf_file, generated_by, and generated_at all need
        # to be set together, correctly, by that action.


class GenerateReportSerializer(serializers.Serializer):
    period_month = serializers.IntegerField(min_value=1, max_value=12)
    period_year = serializers.IntegerField(min_value=2020, max_value=2100)
    other_additions = serializers.CharField(required=False, allow_blank=True, default="")
