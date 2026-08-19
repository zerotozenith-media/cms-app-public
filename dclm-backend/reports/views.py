from django.core.files.base import ContentFile
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.audit import log_audit
from accounts.permissions import ModulePermission
from .models import Service, Department, Testimony, WeeklyNote, Report
from .pdf import render_report_pdf
from .serializers import (
    ServiceSerializer, DepartmentSerializer, TestimonySerializer,
    WeeklyNoteSerializer, ReportSerializer, GenerateReportSerializer,
)


class ServiceViewSet(viewsets.ModelViewSet):
    module = "reports"
    permission_classes = [ModulePermission]
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer


class DepartmentViewSet(viewsets.ModelViewSet):
    module = "reports"
    permission_classes = [ModulePermission]
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer


class TestimonyViewSet(viewsets.ModelViewSet):
    module = "reports"
    permission_classes = [ModulePermission]
    queryset = Testimony.objects.select_related("service")
    serializer_class = TestimonySerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["date"]

    def get_queryset(self):
        qs = super().get_queryset()
        service = self.request.query_params.get("service")
        if service:
            qs = qs.filter(service_id=service)
        return qs

    def perform_create(self, serializer):
        instance = serializer.save()
        who = "Anonymous" if instance.is_anonymous else (instance.member_name or "Unknown")
        log_audit(self.request.user, "Submitted", "Testimony", who, instance=instance)


class WeeklyNoteViewSet(viewsets.ModelViewSet):
    module = "reports"
    permission_classes = [ModulePermission]
    queryset = WeeklyNote.objects.select_related("department")
    serializer_class = WeeklyNoteSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["week_start"]

    def get_queryset(self):
        qs = super().get_queryset()
        department = self.request.query_params.get("department")
        if department:
            qs = qs.filter(department_id=department)
        return qs

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit(
            self.request.user, "Submitted", "Weekly Note",
            f"{instance.department.name} , {instance.week_label}", instance=instance,
        )


class ReportViewSet(viewsets.ModelViewSet):
    """
    Read-only for standard CRUD (reports are only ever created via
    generate()) , list/retrieve to browse past reports, delete allowed
    for correcting a mistaken generation, no create/update.
    """
    module = "reports"
    permission_classes = [ModulePermission]
    queryset = Report.objects.select_related("generated_by")
    serializer_class = ReportSerializer
    http_method_names = ["get", "delete", "post", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        year = self.request.query_params.get("year")
        if year:
            qs = qs.filter(period_year=year)
        return qs

    def create(self, request, *args, **kwargs):
        return Response({"detail": "Use /generate/ to create a report."}, status=405)

    def perform_destroy(self, instance):
        label = f"{instance.period_month}/{instance.period_year}"
        log_audit(self.request.user, "Deleted", "Report", label)
        instance.delete()

    @action(detail=False, methods=["post"])
    def generate(self, request):
        serializer = GenerateReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        month = serializer.validated_data["period_month"]
        year = serializer.validated_data["period_year"]
        other_additions = serializer.validated_data["other_additions"]

        if Report.objects.filter(period_month=month, period_year=year).exists():
            return Response(
                {"detail": f"A report for {month}/{year} already exists. Delete it first to regenerate."},
                status=status.HTTP_409_CONFLICT,
            )

        pdf_bytes = render_report_pdf(year, month, other_additions, request.user)

        report = Report.objects.create(
            period_month=month, period_year=year, generated_by=request.user,
            other_additions=other_additions,
        )
        report.pdf_file.save(f"report-{year}-{month:02d}.pdf", ContentFile(pdf_bytes), save=True)

        log_audit(
            request.user, "Generated", "Report", f"{month}/{year}",
            f"{len(pdf_bytes)} bytes", instance=report,
        )
        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)
