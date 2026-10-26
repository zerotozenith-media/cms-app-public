"""
Late tasks, reasons and the Follow-up Coordinator's Review list (Kay, 26
October 2026). With the decided values:

  due        24 hours after the clock start (6:00 pm on the service day)
  reason     from 48 hours the shepherd must give a reason and a new date,
             up to 7 days ahead, for each late task
  review     from 3 days a task still open is on the Review list
  decide     the Follow-up Coordinator chooses within 5 days: Accept, Hand
             to another shepherd (this task only), Take it myself, or Ask
             the shepherd; not decided by then, the administrators are told

Tasks made before 26 October 2026 have no clock, so they reach the Review
list only when handed over (escalated).
"""
import datetime

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.audit import log_audit
from accounts.names import display_name
from .followup_rules import at, deadlines, rules
from . import task_actions as acts

FINAL = ("accept", "hand-on", "take")


def rounds(task):
    return list(task.reviews.all())


def latest(task):
    r = rounds(task)
    return r[-1] if r else None


def latest_reason(task):
    for rnd in reversed(rounds(task)):
        if rnd.reason:
            return rnd
    return None


def new_date_deadline(day, r=None):
    return at(day, (r or rules()).clock_start)


def reason_valid(task, now, r):
    rnd = latest_reason(task)
    return bool(rnd and rnd.new_date and now < new_date_deadline(rnd.new_date, r))


def needs_reason(task, now=None, r=None):
    """The shepherd must give a reason and a new date for this task now."""
    now = now or timezone.now()
    r = r or rules()
    if task.done or not task.clock_start or task.escalation == "needs-coordinator":
        return False
    if now < deadlines(task.clock_start, r)["reason_at"] and not _passed_accepted_date(task, now, r):
        return False
    return not reason_valid(task, now, r)


def _passed_accepted_date(task, now, r):
    rnd = latest(task)
    return bool(rnd and rnd.choice == "accept" and task.due_at and now >= task.due_at)


def settled(task, now):
    rnd = latest(task)
    return bool(rnd and rnd.choice in FINAL and task.due_at and now < task.due_at)


def on_review(task, now=None, r=None):
    now = now or timezone.now()
    r = r or rules()
    if task.done or settled(task, now):
        return False
    if task.escalation:
        return True
    rnd = latest(task)
    if rnd and (rnd.reason and not rnd.choice or rnd.choice == "ask"):
        return True
    if not task.clock_start:
        return False
    return now >= deadlines(task.clock_start, r)["review_at"]


def decide_by(task, r=None):
    r = r or rules()
    base = (deadlines(task.clock_start, r)["decide_by"] if task.clock_start
            else (task.escalated_at or timezone.now()) + datetime.timedelta(days=r.decide_days - r.review_days))
    rnd = latest(task)
    if rnd and rnd.given_at and not rnd.choice:
        base = max(base, rnd.given_at + datetime.timedelta(days=r.decide_days - r.review_days))
    if task.escalated_at:
        base = max(base, task.escalated_at + datetime.timedelta(days=r.decide_days - r.review_days))
    return base


def _round_for(task):
    from .models import FollowUpReview
    kw = {"member_task": task} if acts.is_member_task(task) else {"newcomer_task": task}
    return FollowUpReview(**kw)


def give_reason(task, user, reason, note, new_date, alert=True):
    from .followup_access import can_review
    from .models import FollowUpReview
    if task.done:
        raise ValidationError({"detail": "This task is already closed."})
    if task.assigned_to_id != user.id and not can_review(user, acts.location_id(task)):
        raise PermissionDenied("Only the shepherd the task belongs to gives its reason.")
    now = timezone.now()
    if not task.due_at or now < task.due_at:
        raise ValidationError({"detail": "This task is not late yet, so no reason is needed."})
    if reason not in dict(FollowUpReview.REASONS):
        raise ValidationError({"reason": "Choose a reason."})
    r = rules()
    today = timezone.localdate()
    limit = today + datetime.timedelta(days=r.max_new_date_days)
    if not new_date or new_date < today or new_date > limit:
        raise ValidationError({"new_date": f"Choose a new date from today up to {limit:%A %-d %B}, "
                                           f"{r.max_new_date_days} days ahead, so a late task is not pushed far away."})
    rnd = _round_for(task)
    rnd.reason, rnd.reason_note, rnd.new_date = reason, (note or "")[:500], new_date
    rnd.given_by, rnd.given_at = user, now
    rnd.save()
    log_audit(user, "Gave reason for late task", acts._entity(task), acts.person_name(task),
              f"{rnd.get_reason_display()}. New date {new_date:%-d %B}" + (f". {note}" if note else ""), instance=task)
    if alert:
        from .followup_events import reason_given
        reason_given(task, rnd)
    return rnd


def decide(task, user, choice, note="", handed_to=None):
    """The Follow-up Coordinator's choice for a task on the Review list."""
    from .followup_access import can_review
    from .followup_events import decided
    if not can_review(user, acts.location_id(task)):
        raise PermissionDenied("Only a Follow-up Coordinator for this person's location, or an administrator, "
                               "decides on late tasks.")
    if task.done:
        raise ValidationError({"detail": "This task is already closed."})
    if choice not in ("accept", "hand-on", "take", "ask"):
        raise ValidationError({"choice": "Choose Accept, Hand to another shepherd, Take it myself or Ask the shepherd."})
    note = (note or "").strip()
    now = timezone.now()
    r = rules()
    rnd = latest(task)
    if not rnd or rnd.choice:
        rnd = _round_for(task)
    if choice == "accept":
        rr = latest_reason(task)
        if rr and rr.new_date and not rr.choice:
            task.due_at = new_date_deadline(rr.new_date, r)
            task.due_date = rr.new_date
        else:
            # Nothing new to accept: the shepherd keeps it, with a fresh day.
            task.due_at = now + datetime.timedelta(hours=r.due_hours)
            task.due_date = timezone.localtime(task.due_at).date()
        task.escalation = ""
    elif choice in ("hand-on", "take"):
        to = user if choice == "take" else handed_to
        if to is None:
            raise ValidationError({"handed_to": "Choose who takes this task."})
        if choice == "hand-on":
            check_can_take(task, to)
        task.handed_from = task.assigned_to
        task.assigned_to = to
        task.clock_start = now
        task.due_at = now + datetime.timedelta(hours=r.due_hours)
        task.due_date = timezone.localtime(task.due_at).date()
        task.escalation = ""
        task.reason_alerted_at = task.review_alerted_at = None
        rnd.handed_to = to
    elif choice == "ask" and not note:
        raise ValidationError({"note": "Write the question for the shepherd, for example \"Did you try her "
                                       "husband's number?\""})
    task.save()
    rnd.choice, rnd.choice_note, rnd.decided_by, rnd.decided_at = choice, note[:500], user, now
    rnd.save()
    label = dict(rnd.CHOICES)[choice]
    detail = label + (f" to {display_name(rnd.handed_to)}" if rnd.handed_to_id else "") + (f". {note}" if note else "")
    log_audit(user, "Follow-up review decision", acts._entity(task), acts.person_name(task), detail, instance=task)
    decided(task, rnd, user)
    return rnd


def check_can_take(task, user):
    """Hand to another shepherd: someone who shepherds, at the person's
    location, men for men and women for women. This one task only; the
    person keeps their shepherd."""
    from accounts.gender import can_pair
    from members.assignment import eligible_shepherds
    person = acts.person_of(task)
    allowed = {u.id for u in eligible_shepherds(location=person.location_id)}
    if user.id not in allowed:
        raise ValidationError({"handed_to": "Choose a shepherd at this person's location."})
    if not can_pair(getattr(person, "gender", "") or "", user):
        raise ValidationError({"handed_to": "Men follow up men and women follow up women, so choose a shepherd "
                                            "of the same gender."})


# ---- Lists -----------------------------------------------------------------

def open_tasks(location_id=None):
    """Every open task, member and newcomer, at a location or everywhere."""
    from members.models import MemberFollowUpTask
    from newcomers.models import NewcomerTask
    m = (MemberFollowUpTask.objects.filter(done=False).select_related("member", "assigned_to", "handed_from")
         .prefetch_related("reviews", "attempts"))
    n = (NewcomerTask.objects.filter(done=False).select_related("newcomer", "assigned_to", "handed_from")
         .prefetch_related("reviews", "attempts"))
    if location_id:
        m = m.filter(member__location_id=location_id)
        n = n.filter(newcomer__location_id=location_id)
    return list(m) + list(n)


def task_row(task, now, r):
    """One task as every follow-up screen shows it."""
    person = acts.person_of(task)
    member = acts.is_member_task(task)
    rr = latest_reason(task)
    rnd = latest(task)
    return {
        "type": "member" if member else "newcomer",
        "id": task.id,
        "person_id": person.id,
        "person": acts.person_name(task),
        "person_kind": "Member" if member else f"Newcomer, {person.get_stage_display()}",
        "location": person.location_id,
        "text": task.text,
        "kind": task.kind,
        "kind_label": task.get_kind_display(),
        "missed_meeting_name": task.missed_meeting_name,
        "missed_date": task.missed_date,
        "missed_in_row": task.missed_in_row,
        "due_at": task.due_at,
        "due_date": task.due_date,
        "is_late": bool(task.due_at and now >= task.due_at) or (not task.due_at and task.due_date < timezone.localdate(now)),
        "needs_reason": needs_reason(task, now, r),
        "on_review": on_review(task, now, r),
        "decide_by": decide_by(task, r) if on_review(task, now, r) else None,
        "escalation": task.escalation,
        "escalation_label": task.get_escalation_display() if task.escalation else "",
        "result_note": task.result_note if task.escalation == "needs-coordinator" else "",
        "shepherd_id": task.assigned_to_id,
        "shepherd": display_name(task.assigned_to) if task.assigned_to_id else "",
        "handed_from": display_name(task.handed_from) if task.handed_from_id else "",
        "attempts": [{"date": a.date, "at": a.at, "method": a.method, "note": a.note} for a in task.attempts.all()],
        "reason": ({"reason": rr.get_reason_display(), "note": rr.reason_note, "new_date": rr.new_date,
                    "given_at": rr.given_at} if rr else None),
        "last_choice": ({"choice": rnd.get_choice_display(), "note": rnd.choice_note, "at": rnd.decided_at}
                        if rnd and rnd.choice else None),
    }


def my_followup(user, shepherd_id=None):
    """
    One list of a shepherd's open tasks, members and newcomers together,
    grouped under each person (Kay, 26 October 2026), late tasks first.
    """
    from members.models import Member
    from newcomers.models import Newcomer
    now, r = timezone.now(), rules()
    who = shepherd_id or user.id
    tasks = [t for t in open_tasks() if t.assigned_to_id == who]
    rows = [task_row(t, now, r) for t in tasks]
    people = {}
    for row in rows:
        key = (row["type"], row["person_id"])
        people.setdefault(key, {"type": row["type"], "person_id": row["person_id"], "person": row["person"],
                                "person_kind": row["person_kind"], "tasks": []})["tasks"].append(row)
    out = list(people.values())
    for p in out:
        p["tasks"].sort(key=lambda t: (t["due_at"] or now))
        p["needs_reason"] = sum(1 for t in p["tasks"] if t["needs_reason"])
        p["late"] = sum(1 for t in p["tasks"] if t["is_late"])
        p["priority"] = max([t["missed_in_row"] for t in p["tasks"]] + [0]) >= r.alert_from_miss
        p["run"] = max([t["missed_in_row"] for t in p["tasks"]] + [0])
    out.sort(key=lambda p: (-p["needs_reason"], -p["late"], -int(p["priority"]), p["person"]))
    # People away, so the shepherd knows why nobody is chasing them.
    today = timezone.localdate()
    away = []
    for m in Member.objects.filter(assigned_to_id=who, status="active", away_to__gte=today):
        away.append({"type": "member", "person_id": m.id, "person": m.full_name, "away_from": m.away_from, "away_to": m.away_to,
                     "away_reason": m.get_away_reason_display()})
    for n in Newcomer.objects.filter(assigned_to_id=who, away_to__gte=today):
        away.append({"type": "newcomer", "person_id": n.id, "person": n.name, "away_from": n.away_from, "away_to": n.away_to,
                     "away_reason": dict(Newcomer._meta.get_field("away_reason").choices).get(n.away_reason, "")})
    return {"people": out, "away": away,
            "needs_reason": sum(p["needs_reason"] for p in out),
            "open": len(rows)}


def review_list(user, location_id=None):
    from .followup_access import coverage
    now, r = timezone.now(), rules()
    loc = location_id or coverage(user)
    rows = [task_row(t, now, r) for t in open_tasks(loc) if on_review(t, now, r)]
    rows.sort(key=lambda x: (x["decide_by"] or now))
    for row in rows:
        row["shepherd_late_this_quarter"] = late_this_quarter(row["shepherd_id"], now) if row["shepherd_id"] else 0
    return rows


def late_this_quarter(user_id, now):
    """How many of this shepherd's tasks went late this quarter, for the
    Review list."""
    from members.models import MemberFollowUpTask
    from newcomers.models import NewcomerTask
    local = timezone.localtime(now)
    q_start = datetime.date(local.year, 3 * ((local.month - 1) // 3) + 1, 1)
    start = at(q_start, datetime.time(0, 0))
    n = 0
    for model in (MemberFollowUpTask, NewcomerTask):
        for t in model.objects.filter(assigned_to_id=user_id, due_at__gte=start, due_at__lte=now).only(
                "due_at", "closed_at", "done", "result"):
            if t.result in ("was-present", "cancelled"):
                continue
            if not t.done or (t.closed_at and t.closed_at > t.due_at):
                n += 1
    return n
