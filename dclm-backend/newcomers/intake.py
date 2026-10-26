"""
Shared intake logic used by both the authenticated Newcomer creation
path (NewcomerViewSet) and the public QR self-registration endpoint ,
factored out so both paths are guaranteed to behave identically, not
just similarly, for the parts of the process (invited-by matching,
auto-task creation) common to both.
"""
from django.utils import timezone

from .models import NewcomerTask


def match_invited_by_member(invited_by_name):
    """
    Exact case-insensitive match on a Member's computed full name.
    full_name is a Python property, not a DB field, so this can't be a
    queryset filter , fetching all members and matching in Python is
    fine at this project's real scale (a single church's membership).
    Only links if unambiguous: two members sharing the exact name are
    left unlinked, text-only, rather than guessing.
    """
    invited_by_name = (invited_by_name or "").strip()
    if not invited_by_name:
        return None
    from members.models import Member
    candidates = [m for m in Member.objects.all() if m.full_name.lower() == invited_by_name.lower()]
    return candidates[0] if len(candidates) == 1 else None


def create_auto_tasks(newcomer):
    """
    Auto-created follow-up tasks from the intake slip's request
    checkboxes , real tasks a leader sees in their Follow-ups list, not
    an automated send. Nothing is emailed or messaged by the system
    itself; a human still does the actual visit/conversation.
    """
    # Give them a shepherd first, so the tasks below have somebody to
    # belong to. A task created unowned is never picked up afterwards.
    from members.assignment import assign_on_registration
    assign_on_registration(newcomer)

    # Every first-visit task is due 24 hours from 6:00 pm on the day the
    # newcomer first came (Kay, 26 October 2026), like an absence task.
    # Before, a visit had 5 days and a salvation conversation 2. Entered on
    # a later day, the clock starts when the newcomer is entered.
    from core.accountable import TaskKind
    from core.followup_rules import at, deadlines, rules
    r = rules()
    now = timezone.now()
    normal = at(newcomer.created_at, r.clock_start)
    start = normal if timezone.localdate(now) <= newcomer.created_at else max(normal, now)
    due = deadlines(start, r)["due_at"]
    task_specs = []
    if newcomer.wants_visit:
        task_specs.append("Schedule a home visit")
    if newcomer.wants_to_know_more:
        task_specs.append("Share more about the church")
    if newcomer.wants_salvation_info:
        task_specs.append("Have a salvation conversation")
    for text in task_specs:
        NewcomerTask.objects.create(
            newcomer=newcomer, text=text, kind=TaskKind.FIRST_VISIT,
            due_date=timezone.localtime(due).date(), due_at=due, clock_start=start, created_at=now,
            assigned_to=newcomer.assigned_to,
        )

def check_in_today(newcomer):
    """
    Somebody registering on the day of a service was at it, so they are
    checked in to it, and their Friday attendance starts from the right
    day. The meeting they named on the slip, or the only service held at
    their location today. Nothing is guessed when it is unclear.
    """
    from attendance.models import AttendanceSession, AttendanceSessionMember
    if not newcomer.location_id:
        return None
    today = timezone.localdate()
    if newcomer.created_at != today:
        return None
    sessions = AttendanceSession.objects.filter(date=today, location_id=newcomer.location_id, fellowship__isnull=True)
    if newcomer.meeting_attended_id:
        sessions = sessions.filter(meeting_type_id=newcomer.meeting_attended_id)
    sessions = list(sessions[:2])
    if len(sessions) != 1:
        return None
    AttendanceSessionMember.objects.get_or_create(session=sessions[0], newcomer=newcomer)
    return sessions[0]
