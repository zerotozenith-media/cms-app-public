"""
The follow-up clock and a service's status words (Kay, 26 October 2026).

Every time limit counts from the clock start (6:00 pm by default) on the
day of the service. When names are ticked after the absence check has run,
the clock starts when the task is made instead, so a shepherd never starts
out late because of a late entry. The numbers live in FollowUpRules and are
changed in Admin, Follow-up Rules.
"""
import datetime

from django.utils import timezone

# The scheduled check runs twice an hour, so a task made up to this long
# after the check time still counts as made by the check.
CHECK_GRACE = datetime.timedelta(hours=1)


def rules():
    from core.models import FollowUpRules
    return FollowUpRules.get()


def at(day, time):
    """A date and a time of day, in the church's time zone."""
    return timezone.make_aware(datetime.datetime.combine(day, time))


def check_time(meeting_type, day, r=None):
    """When the absence check runs for a service: its start time plus the
    hours set in Follow-up Rules. None for a meeting with no start time."""
    if not meeting_type.start_time:
        return None
    r = r or rules()
    return at(day, meeting_type.start_time) + datetime.timedelta(hours=r.check_hours_after_start)


def clock_start(service_day, created_at=None, meeting_type=None, r=None):
    """
    Where the follow-up clock starts for a task about a service.

    Normally the clock start on the service day. A task made well after
    the absence check (names ticked late, or a service followed up on
    request days later) starts when it was made.
    """
    r = r or rules()
    normal = at(service_day, r.clock_start)
    if created_at is None:
        return normal
    check = check_time(meeting_type, service_day, r) if meeting_type is not None else None
    limit = max(normal, check or normal) + CHECK_GRACE
    return normal if created_at <= limit else created_at


def deadlines(start, r=None):
    """Every time limit for a task whose clock started at `start`."""
    r = r or rules()
    return {
        "due_at": start + datetime.timedelta(hours=r.due_hours),
        "reason_at": start + datetime.timedelta(hours=r.reason_hours),
        "review_at": start + datetime.timedelta(days=r.review_days),
        "decide_by": start + datetime.timedelta(days=r.decide_days),
    }


def names_deadline(service_day, r=None):
    """After this a tracked service with no names shows Names not taken:
    the clock start on the day after the service."""
    r = r or rules()
    return at(service_day + datetime.timedelta(days=1), r.clock_start)


STATE_LABELS = {
    "upcoming": "Upcoming",
    "waiting-names": "Waiting for names",
    "waiting": "Waiting to be filled in",
    "names-not-taken": "Names not taken",
    "not-filled": "Not filled in",
    "done": "Done",
    "did-not-hold": "Did not hold",
}


def session_state(session, now=None, r=None, has_names=None):
    """
    The status word a service shows in Attendance (item 20).

    Upcoming before its day, so a session made early is never mistaken for
    one whose names were not taken. A meeting that follows up absence is
    Done only once names are ticked: a headcount alone cannot say who was
    absent, so it shows Names not taken from 6:00 pm the next day.
    """
    now = now or timezone.now()
    today = timezone.localdate(now)
    if session.status == "did-not-hold":
        return "did-not-hold"
    if session.date > today:
        return "upcoming"
    tracked = bool(session.meeting_type.counts_for_absence)
    if has_names is None:
        has_names = any(a.member_id or a.newcomer_id for a in session.attendees.all())
    past = now >= names_deadline(session.date, r)
    filled = session.status == "filled"
    if tracked:
        if filled and has_names:
            return "done"
        if past:
            return "not-filled" if has_names else "names-not-taken"
        return "waiting-names"
    if filled:
        return "done"
    return "not-filled" if past else "waiting"


def late_q(now=None):
    """Open tasks past their due time: the exact time where there is one,
    otherwise the end of the due date (tasks made before 26 October 2026)."""
    from django.db.models import Q
    now = now or timezone.now()
    return Q(due_at__lt=now) | Q(due_at__isnull=True, due_date__lt=timezone.localdate(now))
