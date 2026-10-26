"""
The follow-up clock (Kay, 26 October 2026). Runs with the absence check,
twice an hour, and sends each of these once:

  1. 3 hours after a tracked service starts with no names ticked, a reminder
     to the administrators (and Location Coordinators if switched on) to
     fill in the attendance form and tick names;
  2. still no names at 6:00 pm the next day, an alert to the Follow-up
     Coordinator;
  3. tasks reaching 48 hours with no reason, an alert to the shepherd;
  4. tasks reaching 3 days, an alert to the Follow-up Coordinator that they
     are on the Review list;
  5. a Review list decision not made in 5 days, an alert to the
     administrators;
  6. once a day after the morning alert time, an "attendance falling" task
     for anyone who came to fewer than half of the last 8 services.

All times and numbers come from Follow-up Rules.
"""
import datetime
from collections import defaultdict

from django.db.models import Q
from django.utils import timezone

from accounts.names import display_name


def _notify(ids, title, body, url, tag):
    from alerts.events import notify
    return notify(ids, title, body, url, tag)


def reminders(now, r):
    from attendance.models import AttendanceSession
    from .followup_access import administrators, coordinators_for
    from .followup_rules import check_time, names_deadline
    sent = alerts = 0
    recent = timezone.localdate(now) - datetime.timedelta(days=3)
    qs = (AttendanceSession.objects.filter(meeting_type__counts_for_absence=True, meeting_type__start_time__isnull=False,
                                           date__gte=recent, date__lte=timezone.localdate(now))
          .exclude(status="did-not-hold").select_related("meeting_type", "location"))
    for s in qs:
        names = s.attendees.filter(member__isnull=False).exists()
        if names:
            continue
        when = f"{s.meeting_type.name}, {s.location.name}, {s.date:%-d %B}"
        if s.reminder_sent_at is None and now >= check_time(s.meeting_type, s.date, r):
            ids = [u.id for u in administrators()] if r.remind_administrators else []
            if r.remind_location_coordinators:
                from accounts.models import User
                ids += [u.id for u in User.objects.filter(is_active=True, location_id=s.location_id,
                                                          role__name="Location Coordinator")]
            _notify(ids, f"{when}: please tick names",
                    "Fill in the attendance form and tick who came. Nobody can be followed up until names are ticked.",
                    f"/attendance/{s.id}", f"remind-{s.id}")
            s.reminder_sent_at = now
            s.save(update_fields=["reminder_sent_at"])
            sent += 1
        if s.names_alert_sent_at is None and now >= names_deadline(s.date, r):
            _notify([u.id for u in coordinators_for(s.location_id)], f"Names still not taken: {when}",
                    f"It is past {timezone.localtime(names_deadline(s.date, r)):%-I:%M %p} the next day, so nobody "
                    f"at {s.location.name} can be followed up for this service yet.", f"/attendance/{s.id}",
                    f"names-{s.id}")
            s.names_alert_sent_at = now
            s.save(update_fields=["names_alert_sent_at"])
            alerts += 1
    return sent, alerts


def task_alerts(now, r):
    from .followup_access import administrators, coordinators_for
    from . import followup_review as rev
    from . import task_actions as acts
    reasons = defaultdict(list)
    reviews = defaultdict(list)
    late = 0
    for t in rev.open_tasks():
        if t.reason_alerted_at is None and t.assigned_to_id and rev.needs_reason(t, now, r):
            reasons[t.assigned_to_id].append(t)
        if rev.on_review(t, now, r):
            if t.review_alerted_at is None and t.clock_start:
                for u in coordinators_for(acts.location_id(t))[:5]:
                    reviews[u.id].append(t)
                t.review_alerted_at = now
                t.save(update_fields=["review_alerted_at"])
            if now > rev.decide_by(t, r):
                rnd = rev.latest(t)
                if rnd is None or rnd.choice in rev.FINAL:
                    rnd = rev._round_for(t)
                    rnd.save()
                if rnd.admins_alerted_at is None:
                    _notify([u.id for u in administrators()], f"Late decision: {acts.person_name(t)}",
                            "The Follow-up Coordinator has not decided on this late task in time. It is on the Review "
                            "list.", "/followup-review", f"admins-{t.id}-{rnd.id}")
                    rnd.admins_alerted_at = now
                    rnd.save(update_fields=["admins_alerted_at"])
                    late += 1
    for uid, items in reasons.items():
        names = sorted({acts.person_name(t) for t in items})
        _notify([uid], f"{len(items)} late task{'s need' if len(items) != 1 else ' needs'} a reason",
                f"{', '.join(names[:3])}{' and more' if len(names) > 3 else ''}. Give a reason and a new date for each "
                f"before recording anything else.", "/follow-up", f"reasons-{uid}-{now:%Y%m%d%H}")
        for t in items:
            t.reason_alerted_at = now
            t.save(update_fields=["reason_alerted_at"])
    for uid, items in reviews.items():
        _notify([uid], f"{len(items)} task{'s' if len(items) != 1 else ''} on your Review list",
                f"Still open {r.review_days} days after the service.", "/followup-review", f"review-{uid}-{now:%Y%m%d%H}")
    return sum(len(v) for v in reasons.values()), sum(len(v) for v in reviews.values()), late


def attendance_falling(now, r, dry_run=False):
    """
    Someone drifting away without missing several in a row: fewer than the
    set share of the last services (half of the last 8 by default) at their
    location's tracked meetings for everyone. Once a day; one open task per
    person at a time, and not again within the window.
    """
    from attendance.models import AttendanceSession
    from core.models import AppSetting
    from members.models import Member, MemberFollowUpTask
    from newcomers.models import Newcomer, NewcomerTask
    from .accountable import TaskKind
    from .followup_rules import deadlines
    local = timezone.localtime(now)
    key = "followup_falling_checked"
    if not dry_run:
        if local.time() < r.morning_alert_time:
            return 0
        row = AppSetting.objects.filter(key=key).first()
        if row and row.value == local.date().isoformat():
            return 0
        AppSetting.objects.update_or_create(key=key, defaults={"value": local.date().isoformat()})
    since = local.date() - datetime.timedelta(weeks=r.falling_window * 2)
    made = 0
    per_shepherd = defaultdict(list)
    for loc_id in set(Member.objects.values_list("location_id", flat=True)):
        sessions = list(AttendanceSession.objects.filter(
            location_id=loc_id, meeting_type__counts_for_absence=True, meeting_type__audience="everyone",
            date__gte=since, date__lte=local.date(), attendees__member__isnull=False)
            .exclude(status="did-not-hold").distinct().order_by("-date")[:r.falling_window * 3])
        if len(sessions) < r.falling_window:
            continue
        people = [("member", m) for m in Member.objects.filter(location_id=loc_id, status="active")] + \
                 [("newcomer", n) for n in Newcomer.objects.filter(location_id=loc_id, stage__in=r.stages)]
        for kind, p in people:
            start = p.joined_date if kind == "member" else p.created_at
            mine = [s for s in sessions if s.date > start and not p.away_on(s.date)][:r.falling_window]
            if len(mine) < r.falling_window:
                continue
            came = sum(1 for s in mine if (s.attendees.filter(member=p) if kind == "member"
                                           else s.attendees.filter(newcomer=p)).exists())
            if came * 100 >= r.falling_percent * len(mine):
                continue
            model = MemberFollowUpTask if kind == "member" else NewcomerTask
            who = {"member": p} if kind == "member" else {"newcomer": p}
            recent = model.objects.filter(kind=TaskKind.FALLING, **who).filter(
                Q(done=False) | Q(created_at__gte=now - datetime.timedelta(weeks=r.falling_window)))
            if recent.exists():
                continue
            if dry_run:
                made += 1
                continue
            due = deadlines(now, r)["due_at"]
            t = model.objects.create(
                kind=TaskKind.FALLING, text=f"Attendance falling: came to {came} of the last {len(mine)} services",
                due_date=timezone.localtime(due).date(), due_at=due, clock_start=now, created_at=now,
                assigned_to=p.assigned_to, **who)
            made += 1
            if p.assigned_to_id:
                per_shepherd[p.assigned_to_id].append(getattr(p, "full_name", None) or p.name)
            else:
                from .followup_events import tasks_made  # routes it to the Follow-up Coordinator
                tasks_made([t])
    for uid, names in per_shepherd.items():
        _notify([uid], f"Attendance falling: {len(names)} {'person' if len(names) == 1 else 'people'}",
                f"{', '.join(names[:3])}{' and more' if len(names) > 3 else ''}. A task is on your list.", "/follow-up",
                f"falling-{uid}-{local.date()}")
    return made


def run(now=None):
    from .followup_rules import rules
    now = now or timezone.now()
    r = rules()
    sent, names = reminders(now, r)
    reasons, reviews, late = task_alerts(now, r)
    falling = attendance_falling(now, r)
    return (f"Follow-up clock: {sent} reminder(s) to tick names, {names} names-not-taken alert(s), {reasons} reason "
            f"alert(s), {reviews} Review list alert(s), {late} late decision alert(s), {falling} attendance falling "
            f"task(s).")
