"""
Real server-side PDF generation (Batch 0.5 technical note: browser
print-to-PDF was fine for a no-backend demo, but the real system needs
this to work reliably regardless of the requesting user's browser).
Deliberately synchronous , a single church's monthly report is a small
enough job that adding background-task infrastructure (Celery, etc.)
for this alone isn't justified at this scale.
"""
import calendar
import datetime

from django.db.models import Sum
from django.template.loader import render_to_string
from weasyprint import HTML

from attendance.models import AttendanceSession
from finance.models import Giving, Expense
from goals.models import Goal
from goals.calculations import compute_goal_value
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
        {"date": s.date, "meeting": s.meeting_type.name, "location": s.location.name, "total": s.total}
        for s in all_sessions.select_related("meeting_type", "location").order_by("date")
    ]

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
        "fw_session_count": fw_sessions.count(),
        "income_total": income_total,
        "expense_total": expense_total,
        "net_total": income_total - expense_total,
        "attendance_rows": attendance_rows,
        "by_fund": by_fund,
        "by_category": by_category,
        "testimonies": testimonies,
        "notes": notes,
        "goals": goals,
        "other_additions": other_additions,
    }


def render_report_pdf(period_year, period_month, other_additions, generated_by):
    """Returns raw PDF bytes for the given period."""
    context = gather_report_data(period_year, period_month, other_additions, generated_by)
    html_string = render_to_string("reports/monthly_report.html", context)
    return HTML(string=html_string).write_pdf()
