"""
Who missed a service, and their follow-up tasks. Used by the automatic
absence check and by "Follow up those not ticked" on a service ticked
off afterwards, so both follow the same rules:

  - only members expected at that meeting (its audience, its location);
  - one task per member per missed service, however often it runs;
  - no second task while an earlier follow-up is still open.
"""
import datetime

from django.utils import timezone

FOLLOWUP_DUE_IN_DAYS = 2
# The automatic check covers a filled-in service for this many days.
AUTO_LOOKBACK_DAYS = 7


def expected_members(session):
    from members.models import Member
    from .models import MeetingType
    roster = Member.objects.filter(location=session.location)
    audience = getattr(session.meeting_type, "audience", MeetingType.Audience.EVERYONE)
    if audience == MeetingType.Audience.WORKERS:
        roster = roster.filter(category=Member.Category.WORKER)
    elif audience == MeetingType.Audience.LEADERSHIP:
        roster = roster.filter(is_leader=True)
    return roster


def plan(session):
    """Members not ticked, split into those who would get a task now,
    those already followed up for this service, and those with another
    follow-up still open."""
    from members.models import MemberFollowUpTask
    ticked = set(session.attendees.filter(member__isnull=False).values_list("member_id", flat=True))
    absent = list(expected_members(session).exclude(id__in=ticked).order_by("surname", "first_name"))
    already = set(MemberFollowUpTask.objects.filter(member__in=absent, missed_session=session)
                  .values_list("member_id", flat=True))
    open_other = set(MemberFollowUpTask.objects.filter(member__in=absent, done=False)
                     .exclude(missed_session=session).values_list("member_id", flat=True))
    return {
        "ticked": ticked,
        "to_follow_up": [m for m in absent if m.id not in already and m.id not in open_other],
        "already": [m for m in absent if m.id in already],
        "open_elsewhere": [m for m in absent if m.id not in already and m.id in open_other],
    }


def create_tasks(session, members):
    from members.models import MemberFollowUpTask
    due = timezone.localdate() + datetime.timedelta(days=FOLLOWUP_DUE_IN_DAYS)
    for member in members:
        MemberFollowUpTask.objects.create(
            member=member,
            text=f"Missed {session.meeting_type.name}, check in with them",
            due_date=due,
            assigned_to=member.assigned_to,
            missed_session=session,
            missed_meeting_name=session.meeting_type.name,
            missed_date=session.date,
        )
    return len(members)


def followed_up_automatically(session, today=None):
    """Whether the automatic check covers this service: a meeting that
    follows up absence, with a start time, held in the last 7 days."""
    today = today or timezone.localdate()
    mt = session.meeting_type
    return bool(mt.counts_for_absence and mt.start_time
                and session.date >= today - datetime.timedelta(days=AUTO_LOOKBACK_DAYS))
