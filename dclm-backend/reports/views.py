from django.utils import timezone
from django.http import HttpResponse
from django.core.files.base import ContentFile
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from accounts.permissions import user_has

from accounts.audit import log_audit
from accounts.permissions import ModulePermission
from .models import Service, Department, Testimony, WeeklyNote, Report
from core.viewing import scope_location_id
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
            f"{instance.department.name} · {instance.week_label}", instance=instance,
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
        # A location-limited person sees their own location's reports only.
        user = self.request.user
        if scope_location_id(user):
            qs = qs.filter(location_id=scope_location_id(user))
        year = self.request.query_params.get("year")
        if year:
            qs = qs.filter(period_year=year)
        return qs

    def create(self, request, *args, **kwargs):
        return Response({"detail": "Use /generate/ to create a report."}, status=405)

    def perform_destroy(self, instance):
        label = f"{instance.get_kind_display()}, {ReportSerializer(instance).data['period_label']}"
        log_audit(self.request.user, "Deleted", "Report", label)
        instance.delete()

    @action(detail=False, methods=["post"])
    def generate(self, request):
        serializer = GenerateReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        # One location's report, or the whole church's for an administrator
        # who does not choose one.
        location = report_location(request)
        scope = location.name if location else "all locations"
        (y1, m1), (y2, m2) = d["start"], d["end"]
        if Report.objects.filter(kind=d["kind"], start_year=y1, start_month=m1, period_year=y2,
                                 period_month=m2, location=location).exists():
            return Response(
                {"detail": f"This report already exists for {scope}. Delete it first to make it again."},
                status=status.HTTP_409_CONFLICT,
            )
        pdf_bytes, title = make_pdf(d, location)
        report = Report.objects.create(
            kind=d["kind"], start_month=m1, start_year=y1, period_month=m2, period_year=y2,
            generated_by=request.user, location=location, other_additions=d["other_additions"],
            **{k: d[k].strip() for k in TEXTS},
        )
        slug = location.id if location else "all"
        report.pdf_file.save(f"{title.replace(' ', '-').replace(',', '')}-{slug}.pdf", ContentFile(pdf_bytes), save=True)
        log_audit(request.user, "Generated", "Report", title, f"{scope}, {len(pdf_bytes)} bytes", instance=report)
        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="last-text")
    def last_text(self, request):
        """What was written in the last overseer report for these figures,
        brought forward so only what is new needs changing."""
        location = report_location(request)
        last = Report.objects.filter(kind=Report.Kind.OVERSEER, location=location).order_by("-generated_at").first()
        return Response({k: (getattr(last, k) if last else "") for k in TEXTS} | {
            "from_report": ReportSerializer(last).data["period_label"] if last else ""})


TEXTS = ("summary", "challenges", "training", "conclusion")


def make_pdf(d, location):
    from .church_data import gather, month_list
    ctx = gather(month_list(d["start"], d["end"]), location)
    if d["kind"] == Report.Kind.ZONAL:
        from .zonal import build_pdf
        return build_pdf(ctx)
    from .overseer import build
    return build(ctx, {k: d.get(k, "") for k in TEXTS})


class PreviewView(APIView):
    """The report as it would come out, without saving it. Anybody who can
    see reports can preview one."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not user_has(request.user, "reports", "can_view"):
            return Response({"detail": "You do not have permission to see reports."}, status=403)
        serializer = GenerateReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pdf_bytes, title = make_pdf(serializer.validated_data, report_location(request))
        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        resp["Content-Disposition"] = f'inline; filename="{title.replace(" ", "-").replace(",", "")}-preview.pdf"'
        return resp


class _ReportsModulePermission(ModulePermission):
    """ModulePermission reads `module` off the view. A function view has
    no class to hang that on, so this names it explicitly."""
    def has_permission(self, request, view):
        view.module = "reports"
        return super().has_permission(request, view)


@api_view(["GET"])
@permission_classes([_ReportsModulePermission])
def monthly_spreadsheet(request):
    """
    The zonal report's tables as a spreadsheet, for whoever at Zonal
    combines several locations and would otherwise retype the figures.
    from=YYYY-MM and to=YYYY-MM give the months; year and month alone, as
    older screens send, mean one month.
    """
    from .church_data import gather, month_list
    from .zonal import build_xlsx
    q = request.query_params
    today = timezone.localdate()
    try:
        if q.get("from"):
            y1, m1 = (int(x) for x in q["from"].split("-"))
            y2, m2 = (int(x) for x in (q.get("to") or q["from"]).split("-"))
        else:
            y1 = y2 = int(q.get("year", today.year))
            m1 = m2 = int(q.get("month", today.month))
        ser = GenerateReportSerializer(data={"kind": "zonal", "from_year": y1, "from_month": m1, "to_year": y2, "to_month": m2})
        ser.is_valid(raise_exception=True)
    except (ValueError, TypeError):
        return Response({"detail": "Choose the first and last month."}, status=400)
    d = ser.validated_data
    location = report_location(request)
    ctx = gather(month_list(d["start"], d["end"]), location)
    data = build_xlsx(ctx)
    log_audit(request.user, "Exported", "Report", f"Zonal monthly, {ctx['label']}", "As a spreadsheet")
    resp = HttpResponse(data, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    name = f"DCLM-Bahrain-Zonal-{y1}-{m1:02d}" + (f"-to-{y2}-{m2:02d}" if (y1, m1) != (y2, m2) else "")
    if location:
        name += "-" + location.name.replace(" ", "-")
    resp["Content-Disposition"] = f'attachment; filename="{name}.xlsx"'
    return resp

def report_location(request):
    """
    Whose figures a report covers. Somebody limited to one location always
    gets their own. Anybody else chooses a location with "location", or
    gets the whole church when they do not.
    """
    from core.models import Location
    user = request.user
    if not user.is_superuser and user.location_id:
        return user.location
    wanted = (request.data.get("location") if hasattr(request, "data") and hasattr(request.data, "get") else None) \
        or request.query_params.get("location")
    return Location.objects.filter(id=wanted).first() if wanted else None

