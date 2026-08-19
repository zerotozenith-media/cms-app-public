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
    if calc == "task_completion_rate":
        return _task_completion_rate(goal)
    if calc == "testimony_count":
        return _testimony_count(goal)
    if calc == "member_category_moves":
        return _member_category_moves(goal)
    if calc == "milestone_count":
        return _milestone_count(goal)
    return None


def _latest_session_total(goal):
    from attendance.models import AttendanceSession
    if not goal.calculation_meeting_type_id:
        return None
    filled = AttendanceSession.objects.filter(
        meeting_type_id=goal.calculation_meeting_type_id, status="filled",
    ).order_by("-date")
    if not filled.exists():
        return 0
    latest_date = filled.first().date
    same_date_sessions = filled.filter(date=latest_date)
    return sum(s.total for s in same_date_sessions)


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
