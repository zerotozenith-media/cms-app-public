"""
Working out each person's points, level and next steps (F21).

Points come from the last 90 days. About 70% reward effort, which is in
the person's hands, and 30% reward results, which are shared credit,
because how people respond is not in the shepherd's control. The figures
are the drafts Kay approved.
"""
import datetime
import math

from django.utils import timezone

WINDOW_DAYS = 90
GRACE_DAYS = 30
POINTS = {
    "followup_on_time": 10, "followup_late": 5, "message": 2, "reply": 3, "step": 8,
    "return_visit": 5, "became_member": 15, "baptised": 15, "member_returned": 5,
}
LEVELS = [  # name, scripture, lowest points
    ("Sower", "Psalm 126:6", 0),
    ("Reaper", "John 4:36", 100),
    ("Labourer", "Matthew 9:38", 250),
    ("Soul Winner", "Proverbs 11:30", 450),
    ("Faithful Steward", "1 Corinthians 4:2", 700),
    ("Good and Faithful Servant", "Matthew 25:21", 1000),
]


def level_for(points):
    return max(i for i, (_, _, low) in enumerate(LEVELS) if points >= low)


def points(user, today=None):
    """Points in the last 90 days, with what earned them."""
    from attendance.models import AttendanceSessionMember
    from followup.models import MessageLog, StepDone
    from members.models import Member, MemberFollowUpTask
    from newcomers.models import Newcomer, NewcomerMilestone, NewcomerTask
    today = today or timezone.localdate()
    start = today - datetime.timedelta(days=WINDOW_DAYS - 1)
    got = dict.fromkeys(POINTS, 0)

    # Effort: follow-ups done with the visit record, on time or late.
    for model in (NewcomerTask, MemberFollowUpTask):
        for due, when in model.objects.filter(assigned_to=user, done=True, contact_date__range=(start, today)).values_list("due_date", "contact_date"):
            got["followup_on_time" if when <= due else "followup_late"] += 1
    # Effort: planned and own messages sent, and personal replies. Skips earn nothing.
    logs = MessageLog.objects.filter(sent_by=user, on_date__range=(start, today))
    got["message"] = logs.filter(kind__in=["planned", "own"]).count()
    got["reply"] = logs.filter(kind="reply").count()
    # Effort: discipler steps ticked for new converts.
    got["step"] = StepDone.objects.filter(by=user, done_on__range=(start, today)).count()

    # Results, shared credit, for the people this person looks after.
    mine = Newcomer.objects.filter(assigned_to=user)
    for n in mine:
        dates = sorted(set(AttendanceSessionMember.objects.filter(newcomer=n).values_list("session__date", flat=True)))
        got["return_visit"] += sum(1 for d in dates[1:3] if start <= d <= today)   # their second and third visits
    got["became_member"] = Member.objects.filter(from_newcomer__assigned_to=user, joined_date__range=(start, today)).count()
    got["baptised"] = NewcomerMilestone.objects.filter(newcomer__assigned_to=user, milestone_type__name__iexact="Water Baptism",
                                                       achieved_date__range=(start, today)).count()
    for t in MemberFollowUpTask.objects.filter(assigned_to=user, done=True, contact_date__range=(start, today)):
        if AttendanceSessionMember.objects.filter(member=t.member, session__date__gt=t.missed_date, session__date__lte=today).exists():
            got["member_returned"] += 1

    total = sum(POINTS[k] * n for k, n in got.items())
    return total, got


def refresh(user, today=None):
    """Bring this person's level up to date. Moving up is immediate. Moving
    down waits 30 days after a notice, then goes one level at a time."""
    from .models import ServiceStanding
    today = today or timezone.localdate()
    total, got = points(user, today)
    reached = level_for(total)
    s = ServiceStanding.objects.filter(user=user).first()
    if s is None:
        s = ServiceStanding.objects.create(user=user, level=reached, since=today)
    elif reached > s.level:
        s.level, s.since, s.moved_up_on, s.grace_until = reached, today, today, None
        s.save()
    elif reached < s.level:
        if s.grace_until is None:
            s.grace_until = today + datetime.timedelta(days=GRACE_DAYS)
        elif today >= s.grace_until:
            s.level -= 1
            s.since = today
            s.grace_until = today + datetime.timedelta(days=GRACE_DAYS) if reached < s.level else None
        s.save()
    elif s.grace_until:
        s.grace_until = None
        s.save()
    return s, total, got


def next_steps(total, level):
    """Plain steps that together reach the next level."""
    if level >= len(LEVELS) - 1:
        return 0, []
    need = LEVELS[level + 1][2] - total
    if need <= 0:
        return 0, []
    messages = math.ceil(need * 0.2 / POINTS["message"])
    left = need - messages * POINTS["message"]
    followups = max(1, math.ceil(left / POINTS["followup_on_time"]))
    steps = [(followups, short(followups, "follow-up")), (messages, short(messages, "message"))]
    return need, [s for s in steps if s[0] > 0]


def short(n, what):
    """The step in plain words, singular or plural by count."""
    if what == "follow-up":
        return "follow-up completed on time" if n == 1 else "follow-ups completed on time"
    return "planned message sent" if n == 1 else "planned messages sent"


def eligible_users(location_id=None):
    """Everyone who follows people up: shepherds, and anyone whose role covers newcomers."""
    from accounts.models import User
    from accounts.permissions import user_has
    qs = User.objects.filter(is_active=True).select_related("role")
    if location_id:
        qs = qs.filter(location_id=location_id)
    return [u for u in qs if u.can_shepherd or user_has(u, "newcomers", "can_edit")]
