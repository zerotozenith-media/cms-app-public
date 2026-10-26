"""
Who missed a service, and their follow-up tasks. Used by the automatic
absence check and by "Follow up those not ticked" on a service ticked off
afterwards, so both follow the same rules (Kay, 26 October 2026):

  - only people expected at that meeting: its audience, its location, not
    marked Away that day, members still attending (not Moved away or
    Left), and newcomers in the stages set in Follow-up Rules;
  - one task per person per missed service, however often the check runs;
  - every missed service gets its own task, even when an earlier one is
    still open (tasks pile, decided 26 October 2026);
  - the clock starts at 6:00 pm on the service day, or when the task is
    made if names were ticked after the check had run.
"""
import datetime

from django.utils import timezone

# The automatic check covers a filled-in service for this many days.
AUTO_LOOKBACK_DAYS = 7
# Kept for older imports. Due times now come from Follow-up Rules.
FOLLOWUP_DUE_IN_DAYS = 1
# How far back a run of misses is counted.
RUN_LOOKBACK = 20


def expected_members(session):
    from members.models import Member
    from .models import MeetingType
    roster = Member.objects.filter(location=session.location, status=Member.Status.ACTIVE)
    audience = getattr(session.meeting_type, "audience", MeetingType.Audience.EVERYONE)
    if audience == MeetingType.Audience.WORKERS:
        roster = roster.filter(category=Member.Category.WORKER)
    elif audience == MeetingType.Audience.LEADERSHIP:
        roster = roster.filter(is_leader=True)
    return roster.exclude(away_from__lte=session.date, away_to__gte=session.date)


def expected_newcomers(session):
    """Newcomers still being followed up, at the meeting's location, who
    first came before this service. Workers and leadership meetings are
    not for newcomers."""
    from core.followup_rules import rules
    from newcomers.models import Newcomer
    from .models import MeetingType
    if getattr(session.meeting_type, "audience", "everyone") != MeetingType.Audience.EVERYONE:
        return Newcomer.objects.none()
    return (Newcomer.objects.filter(location=session.location, stage__in=rules().stages,
                                    created_at__lt=session.date)
            .exclude(away_from__lte=session.date, away_to__gte=session.date))


def plan(session):
    """Who was not ticked: those who would get a task now, and those
    already followed up for this service."""
    from members.models import MemberFollowUpTask
    from newcomers.models import NewcomerTask
    ticked = set(session.attendees.filter(member__isnull=False).values_list("member_id", flat=True))
    ticked_n = set(session.attendees.filter(newcomer__isnull=False).values_list("newcomer_id", flat=True))
    absent = list(expected_members(session).exclude(id__in=ticked).order_by("surname", "first_name"))
    absent_n = list(expected_newcomers(session).exclude(id__in=ticked_n).order_by("name"))
    already = set(MemberFollowUpTask.objects.filter(member__in=absent, missed_session=session)
                  .values_list("member_id", flat=True))
    already_n = set(NewcomerTask.objects.filter(newcomer__in=absent_n, missed_session=session)
                    .values_list("newcomer_id", flat=True))
    open_other = set(MemberFollowUpTask.objects.filter(member__in=absent, done=False)
                     .exclude(missed_session=session).values_list("member_id", flat=True))
    return {
        "ticked": ticked,
        "to_follow_up": [m for m in absent if m.id not in already],
        "newcomers": [n for n in absent_n if n.id not in already_n],
        "already": [m for m in absent if m.id in already],
        # Shown for information: they get a task as well, which piles on
        # the open one.
        "open_elsewhere": [m for m in absent if m.id not in already and m.id in open_other],
    }


def missed_in_row(session, member=None, newcomer=None):
    """
    How many times in a row the person has missed this meeting at this
    location, counting this service. A service with nobody ticked says
    nothing about who came, so it is skipped rather than counted or
    treated as attended; Did not hold is skipped too.
    """
    from .models import AttendanceSession
    earlier = (AttendanceSession.objects
               .filter(meeting_type=session.meeting_type, location=session.location, date__lte=session.date,
                       fellowship=session.fellowship)
               .exclude(status=AttendanceSession.Status.DID_NOT_HOLD)
               .order_by("-date", "-id")[:RUN_LOOKBACK])
    since = member.joined_date if member else newcomer.created_at
    run = 0
    for s in earlier:
        if s.date < since:
            break
        names = s.attendees.filter(member__isnull=False).exists()
        if not names:
            continue
        here = (s.attendees.filter(member=member) if member else s.attendees.filter(newcomer=newcomer)).exists()
        if here:
            break
        run += 1
    return max(run, 1)


def _timing(session, now):
    from core.followup_rules import clock_start, deadlines, rules
    r = rules()
    start = clock_start(session.date, now, session.meeting_type, r)
    due = deadlines(start, r)["due_at"]
    return start, due


def create_tasks(session, members, newcomers=(), now=None):
    """Make one task per person. Returns the tasks made."""
    from core.accountable import TaskKind
    from members.models import MemberFollowUpTask
    from newcomers.models import NewcomerTask
    now = now or timezone.now()
    start, due = _timing(session, now)
    name = session.meeting_type.name
    made = []
    for member in members:
        made.append(MemberFollowUpTask.objects.create(
            member=member, kind=TaskKind.ABSENCE,
            text=f"Missed {name}, check in with them",
            due_date=timezone.localtime(due).date(), due_at=due, clock_start=start, created_at=now,
            assigned_to=member.assigned_to, missed_session=session,
            missed_meeting_name=name, missed_date=session.date,
            missed_in_row=missed_in_row(session, member=member),
        ))
    for newcomer in newcomers:
        made.append(NewcomerTask.objects.create(
            newcomer=newcomer, kind=TaskKind.ABSENCE,
            text=f"Missed {name}, check in with them",
            due_date=timezone.localtime(due).date(), due_at=due, clock_start=start, created_at=now,
            assigned_to=newcomer.assigned_to, missed_session=session,
            missed_meeting_name=name, missed_date=session.date,
            missed_in_row=missed_in_row(session, newcomer=newcomer),
        ))
    from core.followup_events import tasks_made
    tasks_made(made)
    return made


def close_was_present(session, member_ids=(), newcomer_ids=()):
    """
    Somebody ticked after their task was made was there after all: the
    task closes as Was present and does not count against the shepherd,
    who is told (Kay, 26 October 2026). Returns the names closed.
    """
    from core.accountable import TaskResult
    from core.task_actions import person_name
    from members.models import MemberFollowUpTask
    from newcomers.models import NewcomerTask
    now = timezone.now()
    closed = []
    for model, field, ids in ((MemberFollowUpTask, "member_id__in", member_ids),
                              (NewcomerTask, "newcomer_id__in", newcomer_ids)):
        if not ids:
            continue
        for t in model.objects.filter(missed_session=session, done=False, **{field: list(ids)}):
            t.done, t.result, t.closed_at = True, TaskResult.WAS_PRESENT, now
            t.result_note = "Ticked present after the task was made."
            t.save(update_fields=["done", "result", "closed_at", "result_note"])
            name = person_name(t)
            closed.append(name)
            if t.assigned_to_id:
                from alerts.events import notify
                notify([t.assigned_to_id], f"{name} was at {session.meeting_type.name} after all",
                       f"Ticked present after the task was made, so it is closed as Was present. Nothing to do.",
                       "/follow-up", f"present-{type(t).__name__}-{t.id}")
    return closed


def followed_up_automatically(session, today=None):
    """Whether the automatic check covers this service: a meeting that
    follows up absence, with a start time, held in the last 7 days."""
    today = today or timezone.localdate()
    mt = session.meeting_type
    return bool(mt.counts_for_absence and mt.start_time
                and session.date >= today - datetime.timedelta(days=AUTO_LOOKBACK_DAYS))
