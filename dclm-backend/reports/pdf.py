"""
Server-side PDF generation for the monthly report.

Rendered with ReportLab rather than an HTML engine. WeasyPrint produced
good output but needs pango, cairo and gdk-pixbuf, system libraries that
managed hosts like Azure App Service will not let you install. ReportLab
is pure Python, so the report works wherever Django does, and it draws
charts natively, which the old HTML version could not do at all.

Deliberately synchronous: one church's monthly report is a small enough
job that adding background-task infrastructure for it alone is not
justified at this scale.
"""
import calendar
import datetime

from django.db.models import Count, Sum

from attendance.models import AttendanceSession
from finance.models import Giving, Expense
from goals.models import Goal
from goals.calculations import compute_goal_value
from members.models import MemberFollowUpTask
from newcomers.models import Newcomer
from reports.models import Testimony, WeeklyNote
from accounts.names import display_name


def _month_bounds(year, month):
    start = datetime.date(year, month, 1)
    end = datetime.date(year, month, calendar.monthrange(year, month)[1])
    return start, end


def gather_report_data(period_year, period_month, other_additions, generated_by):
    start, end = _month_bounds(period_year, period_month)
    period_label = f"{calendar.month_name[period_month]} {period_year}"

    fw_sessions = AttendanceSession.objects.filter(
        meeting_type__id="fri-worship", status="filled", date__gte=start, date__lte=end,
    )
    fw_total = sum(s.total for s in fw_sessions)

    all_sessions = AttendanceSession.objects.filter(status="filled", date__gte=start, date__lte=end)
    attendance_rows = [
        {
            "date": s.date, "meeting": s.meeting_type.name, "location": s.location.name,
            "men": s.men, "women": s.women,
            "youth": s.youth_boys + s.youth_girls,
            "children": s.children_boys + s.children_girls,
            "total": s.total,
        }
        for s in all_sessions.select_related("meeting_type", "location").order_by("date")
    ]

    # The trend chart plots the main service only. Mixing meeting types on
    # one line would compare things that are not comparable.
    fw_ordered = fw_sessions.order_by("date")
    trend_labels = [s.date.strftime("%d %b") for s in fw_ordered]
    trend_values = [s.total for s in fw_ordered]
    fw_count = fw_sessions.count()
    # Python's round() is banker's rounding, so round(30.5) gives 30.
    # Someone checking the arithmetic by hand would read that as a fault,
    # so round half up the way people expect.
    fw_average = int(fw_total / fw_count + 0.5) if fw_count else 0

    giving_qs = Giving.objects.filter(date__gte=start, date__lte=end)
    expense_qs = Expense.objects.filter(date__gte=start, date__lte=end)
    income_total = giving_qs.aggregate(t=Sum("amount"))["t"] or 0
    expense_total = expense_qs.aggregate(t=Sum("amount"))["t"] or 0

    by_fund = [
        {"fund": row["fund__name"], "total": row["total"]}
        for row in giving_qs.values("fund__name").annotate(total=Sum("amount")).order_by("-total")
    ]
    by_category = [
        {"category": row["category__name"], "total": row["total"]}
        for row in expense_qs.values("category__name").annotate(total=Sum("amount")).order_by("-total")
    ]

    testimonies = [
        {"text": t.text, "who": "Anonymous" if t.is_anonymous else (t.member_name or "Unknown"), "service": t.service.name}
        for t in Testimony.objects.filter(date__gte=start, date__lte=end).select_related("service")
    ]
    notes = [
        {"department": n.department.name, "challenges": n.challenges}
        for n in WeeklyNote.objects.filter(week_start__gte=start, week_start__lte=end).select_related("department")
        if n.challenges
    ]

    # Newcomers, which the previous report left out entirely even though
    # the church tracks it closely.
    newcomer_qs = Newcomer.objects.filter(created_at__gte=start, created_at__lte=end)
    newcomers_registered = newcomer_qs.count()
    newcomers_contacted = newcomer_qs.exclude(stage=Newcomer.Stage.NEW).count()
    newcomers_visiting = newcomer_qs.filter(
        stage__in=[Newcomer.Stage.VISITING, Newcomer.Stage.INTEGRATED],
    ).count()
    open_followups = MemberFollowUpTask.objects.filter(done=False).count()

    newcomer_rows = []
    for row in (newcomer_qs.values("source__name")
                .annotate(n=Count("id")).order_by("-n")):
        same_source = newcomer_qs.filter(source__name=row["source__name"])
        newcomer_rows.append({
            "source": row["source__name"],
            "registered": row["n"],
            "contacted": same_source.exclude(stage=Newcomer.Stage.NEW).count(),
            "returned": same_source.filter(
                stage__in=[Newcomer.Stage.VISITING, Newcomer.Stage.INTEGRATED]).count(),
        })

    goals = []
    for g in Goal.objects.all():
        current = g.current if g.tracking == "manual" else (compute_goal_value(g) or 0)
        pct = round(float(current) / float(g.target) * 100) if g.target else 0
        goals.append({"name": g.name, "horizon": g.horizon, "current": current, "target": g.target, "unit": g.unit, "pct": pct})

    return {
        "period_label": period_label,
        "generated_date": datetime.date.today().isoformat(),
        "generated_by_name": display_name(generated_by),
        "fw_total": fw_total,
        "fw_session_count": fw_count,
        "income_total": income_total,
        "expense_total": expense_total,
        "net_total": income_total - expense_total,
        "fw_average": fw_average,
        "attendance_rows": attendance_rows,
        "trend_labels": trend_labels,
        "trend_values": trend_values,
        "newcomers_registered": newcomers_registered,
        "newcomers_contacted": newcomers_contacted,
        "newcomers_visiting": newcomers_visiting,
        "open_followups": open_followups,
        "newcomer_rows": newcomer_rows,
        "by_fund": by_fund,
        "by_category": by_category,
        "testimonies": testimonies,
        "notes": notes,
        "goals": goals,
        "other_additions": other_additions,
    }


def render_report_pdf(period_year, period_month, other_additions, generated_by):
    """Returns raw PDF bytes for the given period."""
    from reports.layout import build_report_pdf

    context = gather_report_data(period_year, period_month, other_additions, generated_by)
    return build_report_pdf(context)
