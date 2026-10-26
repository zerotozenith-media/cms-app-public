"""
Real computation logic for auto-tracked goals (Batch 0.5, Finding 1):
every goal that names a time period actually filters to that period now,
rather than the demo's bug of counting all-time totals regardless of
what the goal's name claimed.
"""
import calendar
import datetime

from django.utils import timezone


def period_bounds(period_type):
    """Returns (start_date, end_date_inclusive) for the given period_type,
    relative to today. None, None for period_type == 'none' (no filtering)."""
    today = timezone.localdate()
    if period_type == "month":
        start = today.replace(day=1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        end = today.replace(day=last_day)
        return start, end
    if period_type == "quarter":
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        start = today.replace(month=quarter_start_month, day=1)
        end_month = quarter_start_month + 2
        last_day = calendar.monthrange(today.year, end_month)[1]
        end = today.replace(month=end_month, day=last_day)
        return start, end
    if period_type == "year":
        return today.replace(month=1, day=1), today.replace(month=12, day=31)
    return None, None  # 'none' , no filtering


def compute_goal_value(goal):
    """Returns the live-computed current value for an auto-tracked goal,
    or None if the goal has no calculation_type configured (a real
    config gap, not silently treated as zero)."""
    calc = goal.calculation_type
    if calc == "latest_session_total":
        return _latest_session_total(goal)
    if calc == "monthly_average_attendance":
        return _monthly_average(goal)
    if calc == "task_completion_rate":
        return _task_completion_rate(goal)
    if calc == "testimony_count":
        return _testimony_count(goal)
    if calc == "member_category_moves":
        return _member_category_moves(goal)
    if calc == "milestone_count":
        return _milestone_count(goal)
    if calc == "sessions_held":
        return _sessions_held(goal)
    if calc == "fund_total":
        return _fund_total(goal)
    if calc == "net_giving":
        return _net_giving(goal)
    if calc == "named_checkins":
        return _named_checkins(goal)
    return None


def _window(goal, qs, field="date"):
    start, end = period_bounds(goal.period_type)
    if start:
        qs = qs.filter(**{f"{field}__gte": start, f"{field}__lte": end})
    if goal.calculation_location_id:
        loc = "location_id" if field == "date" else field.replace("date", "location_id")
        qs = qs.filter(**{loc: goal.calculation_location_id})
    return qs


def _sessions_held(goal):
    """Item 11: sessions of a meeting with attendance recorded."""
    from attendance.models import AttendanceSession
    if not goal.calculation_meeting_type_id:
        return None
    return _window(goal, AttendanceSession.objects.filter(meeting_type_id=goal.calculation_meeting_type_id,
                                                          status="filled")).count()


def _fund_total(goal):
    from django.db.models import Sum
    from finance.models import Giving
    if not goal.calculation_fund_id:
        return None
    return _window(goal, Giving.objects.filter(fund_id=goal.calculation_fund_id)).aggregate(t=Sum("amount"))["t"] or 0


def _net_giving(goal):
    from django.db.models import Sum
    from finance.models import Expense, Giving
    income = _window(goal, Giving.objects.all()).aggregate(t=Sum("amount"))["t"] or 0
    spent = _window(goal, Expense.objects.all()).aggregate(t=Sum("amount"))["t"] or 0
    return income - spent


def _named_checkins(goal):
    """Different people checked in by name at a meeting in the period."""
    from attendance.models import AttendanceSessionMember
    if not goal.calculation_meeting_type_id:
        return None
    qs = AttendanceSessionMember.objects.filter(session__meeting_type_id=goal.calculation_meeting_type_id)
    start, end = period_bounds(goal.period_type)
    if start:
        qs = qs.filter(session__date__gte=start, session__date__lte=end)
    if goal.calculation_location_id:
        qs = qs.filter(session__location_id=goal.calculation_location_id)
    return qs.values("member_id", "newcomer_id").distinct().count()


def _latest_session_total(goal):
    from attendance.models import AttendanceSession
    if not goal.calculation_meeting_type_id:
        return None
    filled = AttendanceSession.objects.filter(
        meeting_type_id=goal.calculation_meeting_type_id, status="filled",
    ).order_by("-date")
    if goal.calculation_location_id:
        filled = filled.filter(location_id=goal.calculation_location_id)
    if not filled.exists():
        return 0
    latest_date = filled.first().date
    same_date_sessions = filled.filter(date=latest_date)
    return sum(s.total for s in same_date_sessions)


def _monthly_average(goal):
    """
    Average attendance per service this month, counting every location's
    session on a date as one service. Early in a month with nothing
    recorded yet, last month's average stands in.

    The goals called "monthly avg" used the latest single service, so one
    unusual Friday moved the figure the whole leadership was watching.
    """
    import datetime
    from django.utils import timezone
    from attendance.models import AttendanceSession
    if not goal.calculation_meeting_type_id:
        return None
    today = timezone.localdate()

    def average(start, end):
        per_date = {}
        qs = AttendanceSession.objects.filter(
            meeting_type_id=goal.calculation_meeting_type_id, status="filled", date__gte=start, date__lte=end)
        if goal.calculation_location_id:
            qs = qs.filter(location_id=goal.calculation_location_id)
        for s in qs:
            per_date[s.date] = per_date.get(s.date, 0) + s.total
        return round(sum(per_date.values()) / len(per_date)) if per_date else None

    this_month = average(today.replace(day=1), today)
    if this_month is not None:
        return this_month
    last_end = today.replace(day=1) - datetime.timedelta(days=1)
    return average(last_end.replace(day=1), last_end) or 0


def _task_completion_rate(goal):
    from newcomers.models import NewcomerTask
    total = NewcomerTask.objects.count()
    if total == 0:
        return 0
    done = NewcomerTask.objects.filter(done=True).count()
    return round(done / total * 100)


def _testimony_count(goal):
    from reports.models import Testimony
    start, end = period_bounds(goal.period_type)
    qs = Testimony.objects.all()
    if start:
        qs = qs.filter(date__gte=start, date__lte=end)
    return qs.count()


def _member_category_moves(goal):
    from members.models import MemberCategoryHistory
    if not goal.calculation_target_category:
        return None
    start, end = period_bounds(goal.period_type)
    qs = MemberCategoryHistory.objects.filter(to_category=goal.calculation_target_category)
    if start:
        qs = qs.filter(changed_date__gte=start, changed_date__lte=end)
    return qs.count()


def _milestone_count(goal):
    from newcomers.models import NewcomerMilestone
    if not goal.calculation_milestone_type_id:
        return None
    start, end = period_bounds(goal.period_type)
    qs = NewcomerMilestone.objects.filter(
        milestone_type_id=goal.calculation_milestone_type_id, achieved_date__isnull=False,
    )
    if start:
        qs = qs.filter(achieved_date__gte=start, achieved_date__lte=end)
    return qs.count()
