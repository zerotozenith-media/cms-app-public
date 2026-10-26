"""
The Follow-up Review page's figures (Kay, 26 October 2026): the five
measures against the targets in Follow-up Rules, and one row per shepherd.

  On time        tasks due in the month with a result by their due time
  First contact  average hours from the clock start to the first recorded
                 attempt or visit
  Reached        tasks closed as Reached, out of all closed
  Late, no reason  open tasks needing a reason now
  3 Fridays or more  people with an open task at the visit-task run or more

Tasks closed as Was present or Cancelled are left out of every measure,
because they were never really owed.
"""
import calendar
import datetime

from django.utils import timezone

from accounts.names import display_name
from .followup_rules import at, rules
from . import followup_review as rev

LEFT_OUT = ("was-present", "cancelled")


def _month_bounds(month):
    y, m = (int(x) for x in month.split("-"))
    start = at(datetime.date(y, m, 1), datetime.time(0, 0))
    end = at(datetime.date(y, m, calendar.monthrange(y, m)[1]), datetime.time(23, 59, 59))
    return start, end


def _tasks(location_id, start, end, shepherd_id=None):
    from members.models import MemberFollowUpTask
    from newcomers.models import NewcomerTask
    out = []
    for model, loc in ((MemberFollowUpTask, "member__location_id"), (NewcomerTask, "newcomer__location_id")):
        qs = model.objects.filter(due_at__gte=start, due_at__lte=end).exclude(result__in=LEFT_OUT).prefetch_related(
            "attempts")
        if location_id:
            qs = qs.filter(**{loc: location_id})
        if shepherd_id:
            qs = qs.filter(assigned_to_id=shepherd_id)
        out += list(qs)
    return out


def measures(tasks, now):
    due = [t for t in tasks if t.due_at <= now]
    on_time = [t for t in due if t.done and t.closed_at and t.closed_at <= t.due_at]
    closed = [t for t in tasks if t.done]
    reached = [t for t in closed if t.result == "reached"]
    hours = []
    for t in tasks:
        if not t.clock_start:
            continue
        firsts = [a.at for a in t.attempts.all()] + ([t.closed_at] if t.result == "reached" and t.closed_at else [])
        if firsts:
            hours.append(max(0, (min(firsts) - t.clock_start).total_seconds() / 3600))
    pct = lambda a, b: round(100 * len(a) / len(b)) if b else None
    return {
        "on_time": pct(on_time, due),
        "first_contact_hours": round(sum(hours) / len(hours)) if hours else None,
        "reached": pct(reached, closed),
        "due": len(due),
    }


def overview(user, location_id=None, month=None):
    from accounts.models import User
    from members.models import Member
    from newcomers.models import Newcomer
    from attendance.models import AttendanceSession
    from .followup_access import coverage
    from .followup_rules import session_state
    now, r = timezone.now(), rules()
    loc = location_id or coverage(user)
    month = month or timezone.localdate().strftime("%Y-%m")
    start, end = _month_bounds(month)
    tasks = _tasks(loc, start, end)
    m = measures(tasks, now)
    open_ = rev.open_tasks(loc)
    late_no_reason = [t for t in open_ if rev.needs_reason(t, now, r)]
    run_people = {(type(t).__name__, rev.acts.person_of(t).id) for t in open_ if t.missed_in_row >= r.visit_task_at_miss}
    today = timezone.localdate()
    members = Member.objects.filter(status="active")
    newcomers = Newcomer.objects.filter(stage__in=["new", "contacted", "attending"])
    if loc:
        members, newcomers = members.filter(location_id=loc), newcomers.filter(location_id=loc)
    away = ([{"type": "member", "id": p.id, "person": p.full_name, "away_from": p.away_from, "away_to": p.away_to,
              "reason": p.get_away_reason_display(), "shepherd": display_name(p.assigned_to) if p.assigned_to_id else ""}
             for p in members.filter(away_to__gte=today).select_related("assigned_to")]
            + [{"type": "newcomer", "id": p.id, "person": p.name, "away_from": p.away_from, "away_to": p.away_to,
                "reason": p.away_reason, "shepherd": display_name(p.assigned_to) if p.assigned_to_id else ""}
               for p in newcomers.filter(away_to__gte=today).select_related("assigned_to")])
    sessions = AttendanceSession.objects.filter(meeting_type__counts_for_absence=True,
                                                date__gte=today - datetime.timedelta(days=14), date__lt=today)
    if loc:
        sessions = sessions.filter(location_id=loc)
    names_not_taken = [{"id": s.id, "name": str(s)} for s in sessions.select_related("meeting_type", "location")
                       if session_state(s, now, r) == "names-not-taken"]
    review = [t for t in open_ if rev.on_review(t, now, r)]

    shepherds = []
    users = User.objects.filter(is_active=True, can_shepherd=True)
    if loc:
        users = users.filter(location_id__in=[loc]) | User.objects.filter(is_active=True, can_shepherd=True,
                                                                           location__isnull=True)
    for u in users.distinct().order_by("first_name", "last_name"):
        carried = members.filter(assigned_to=u).count() + newcomers.filter(assigned_to=u).count()
        mine_open = [t for t in open_ if t.assigned_to_id == u.id]
        mm = measures([t for t in tasks if t.assigned_to_id == u.id], now)
        shepherds.append({
            "id": u.id, "name": display_name(u), "people": carried, "limit": r.shepherd_limit,
            "open": len(mine_open), "on_time": mm["on_time"], "reached": mm["reached"],
            "late_no_reason": sum(1 for t in mine_open if rev.needs_reason(t, now, r)),
        })
    return {
        "month": month, "location": loc,
        "stats": {"open": len(open_), "review": len(review), "late_no_reason": len(late_no_reason),
                  "away": len(away), "names_not_taken": len(names_not_taken)},
        "measures": {**m, "late_no_reason": len(late_no_reason), "run": len(run_people)},
        "targets": {"on_time": r.target_on_time, "first_contact_hours": r.target_first_contact_hours,
                    "reached": r.target_reached, "late_no_reason": 0, "run_at": r.visit_task_at_miss},
        "shepherds": shepherds, "away": away, "names_not_taken": names_not_taken,
    }


def shepherd_people(shepherd_id, location_id=None):
    """The people one shepherd follows up, for the row opened on the page."""
    from members.models import Member
    from newcomers.models import Newcomer
    now, r = timezone.now(), rules()
    open_ = [t for t in rev.open_tasks(location_id) if t.assigned_to_id == shepherd_id]
    today = timezone.localdate()
    out = []
    for p in Member.objects.filter(assigned_to_id=shepherd_id, status="active"):
        out.append(_person("member", p, p.full_name, "Member", open_, now, r, today))
    for p in Newcomer.objects.filter(assigned_to_id=shepherd_id, stage__in=["new", "contacted", "attending"]):
        out.append(_person("newcomer", p, p.name, f"Newcomer, {p.get_stage_display()}", open_, now, r, today))
    return out


def _person(kind, p, name, label, open_, now, r, today):
    mine = [t for t in open_ if rev.acts.person_of(t).id == p.id and (kind == "member") == rev.acts.is_member_task(t)]
    away = p.away_from and p.away_to and p.away_to >= today
    if away:
        status, tone = f"Away until {p.away_to:%-d %B}", "blue"
    elif any(rev.needs_reason(t, now, r) for t in mine):
        status, tone = f"{len(mine)} open, late with no reason", "red"
    elif any(rev.on_review(t, now, r) for t in mine):
        status, tone = f"{len(mine)} open, on the Review list", "amber"
    elif mine:
        run = max(t.missed_in_row for t in mine)
        status = f"{len(mine)} open" + (f", {run} missed in a row" if run >= r.alert_from_miss else "")
        tone = "amber" if run >= r.alert_from_miss else "gray"
    else:
        status, tone = "Nothing open", "green"
    return {"type": kind, "id": p.id, "person": name, "label": label, "status": status, "tone": tone,
            "open": len(mine)}
