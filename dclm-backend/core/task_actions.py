"""
Recording what happened on a follow-up task (Kay, 26 October 2026), the
same way for member and newcomer tasks:

  Reached               the four boxes are required; the visit closes every
                        open absence task for the person, and a next-step
                        date makes the next task on that date
  Tried, could not reach logged with its date; the task stays open, and
                        after the attempts set in Follow-up Rules it goes to
                        the Follow-up Coordinator
  Known reason          closes with the reason; the person can be marked
                        Away until a date
  Needs the Follow-up Coordinator   handed over at once
  Moved away or left    the person's status changes and no more tasks are made

Plus Was present (attendance), Cancelled (made in error) and changing a
due time. Every action is written to the audit log.
"""
import datetime

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.audit import log_audit
from .accountable import Escalation, TaskKind, TaskResult

ABSENCE_KINDS = [TaskKind.ABSENCE, TaskKind.FALLING]


def is_member_task(task):
    from members.models import MemberFollowUpTask
    return isinstance(task, MemberFollowUpTask)


def person_of(task):
    return task.member if is_member_task(task) else task.newcomer


def person_name(task):
    p = person_of(task)
    return p.full_name if is_member_task(task) else p.name


def _entity(task):
    return "Member" if is_member_task(task) else "Newcomer"


def person_tasks(task):
    model = type(task)
    return model.objects.filter(member=task.member) if is_member_task(task) else model.objects.filter(
        newcomer=task.newcomer)


def location_id(task):
    return person_of(task).location_id


def _close(task, user, result, note="", now=None, covered_by=None):
    task.done = True
    task.result = result
    if note:
        task.result_note = note
    task.closed_at = now or timezone.now()
    task.closed_by = user
    task.covered_by = covered_by


def reached(task, user, data):
    """
    The four boxes are required. One visit closes every open absence task
    for the person, each pointing to this one; a next-step date makes the
    next task on that date.
    """
    if task.done:
        raise ValidationError({"detail": "This task is already closed."})
    now = timezone.now()
    with transaction.atomic():
        task.contact_date = data.get("contact_date") or timezone.localdate()
        task.contact_method = data["contact_method"]
        for f in ("contact_goal", "contact_scripture", "contact_root_cause", "contact_next_step"):
            setattr(task, f, data[f])
        _close(task, user, TaskResult.REACHED, now=now)
        task.save()
        others = list(person_tasks(task).filter(done=False, kind__in=ABSENCE_KINDS).exclude(pk=task.pk))
        for o in others:
            o.contact_date, o.contact_method = task.contact_date, task.contact_method
            _close(o, user, TaskResult.REACHED, f"Closed by the visit recorded on {timezone.localtime(now):%-d %B}.",
                   now, covered_by=task)
            o.save()
        nxt = None
        if data.get("next_step_date"):
            nxt = next_step_task(task, data["next_step_date"], user)
        log_audit(user, "Recorded follow-up outcome", _entity(task), person_name(task),
                  f"Reached by {task.contact_method}: {task.contact_goal[:60]}"
                  + (f". Also closed {len(others)} other open task(s)" if others else ""), instance=task)
    return {"closed_also": [o.id for o in others], "next_task": nxt.id if nxt else None}


def next_step_task(task, day, user):
    from .followup_rules import at, rules
    if day < timezone.localdate():
        raise ValidationError({"next_step_date": "The next step date cannot be in the past."})
    model = type(task)
    due = at(day, rules().clock_start)
    who = {"member": task.member} if is_member_task(task) else {"newcomer": task.newcomer}
    return model.objects.create(
        kind=TaskKind.NEXT_STEP, text=(task.contact_next_step or "Next step")[:300],
        due_date=day, due_at=due, clock_start=due, created_at=timezone.now(),
        assigned_to=task.assigned_to or person_of(task).assigned_to, **who)


def attempt_count(task):
    # Counted afresh: the task may carry an earlier prefetched list.
    if is_member_task(task):
        from members.models import MemberContactAttempt as A
    else:
        from newcomers.models import NewcomerContactAttempt as A
    return A.objects.filter(task=task).count()


def tried(task, user, method, note=""):
    """Log a contact that did not reach the person. The task stays open.
    After the attempts set in Follow-up Rules it goes to the Follow-up
    Coordinator, because the shepherd has tried and needs help."""
    from .followup_rules import rules
    if task.done:
        raise ValidationError({"detail": "This task is already closed."})
    if is_member_task(task):
        from members.models import MemberContactAttempt as A
        kw = {"member": task.member}
    else:
        from newcomers.models import NewcomerContactAttempt as A
        kw = {"newcomer": task.newcomer}
    if method not in dict(A.Method.choices):
        raise ValidationError({"method": "Choose how you tried to reach them."})
    A.objects.create(task=task, method=method, note=(note or "")[:300], by=user, **kw)
    n = attempt_count(task)
    log_audit(user, "Logged contact attempt", _entity(task), person_name(task), f"{method}, no reply (attempt {n})",
              instance=task)
    limit = rules().attempts_before_coordinator
    if n >= limit and not task.escalation:
        escalate(task, Escalation.ATTEMPTS, user)
    return n


def escalate(task, kind, user=None, note=""):
    from .followup_events import escalated
    task.escalation = kind
    task.escalated_at = timezone.now()
    if note:
        task.result_note = note
    task.save(update_fields=["escalation", "escalated_at", "result_note"])
    escalated(task, user)


def known_reason(task, user, note, away_from=None, away_to=None, away_reason=""):
    if task.done:
        raise ValidationError({"detail": "This task is already closed."})
    note = (note or "").strip()
    if not note:
        raise ValidationError({"note": "Say what the reason is, for example travelling until 15 November."})
    with transaction.atomic():
        _close(task, user, TaskResult.KNOWN_REASON, note)
        task.save()
        if away_from and away_to:
            set_away(person_of(task), user, away_from, away_to, away_reason or "other", note)
        log_audit(user, "Recorded follow-up outcome", _entity(task), person_name(task), f"Known reason: {note[:80]}",
                  instance=task)


def needs_coordinator(task, user, note):
    note = (note or "").strip()
    if not note:
        raise ValidationError({"note": "Say briefly what the matter is, so the Follow-up Coordinator knows "
                                       "before calling. It is seen only by the shepherd, the Follow-up "
                                       "Coordinator and administrators."})
    escalate(task, Escalation.NEEDS_COORDINATOR, user, note)
    log_audit(user, "Handed to the Follow-up Coordinator", _entity(task), person_name(task), "", instance=task)


def moved_away(task, user, note=""):
    """The person no longer attends: their status changes and every open
    task for them closes, so no more tasks are made."""
    note = (note or "").strip() or "Moved away or left."
    with transaction.atomic():
        p = person_of(task)
        if is_member_task(task):
            from members.models import Member
            p.status, p.status_date, p.status_note = Member.Status.MOVED_AWAY, timezone.localdate(), note[:300]
            p.save(update_fields=["status", "status_date", "status_note"])
        else:
            from newcomers.models import Newcomer, NewcomerStatusHistory
            NewcomerStatusHistory.objects.create(newcomer=p, stage=Newcomer.Stage.NOT_INTERESTED, note=note,
                                                 date=timezone.localdate())
            p.stage, p.stage_since, p.not_interested_note = Newcomer.Stage.NOT_INTERESTED, timezone.localdate(), note
            p.save(update_fields=["stage", "stage_since", "not_interested_note"])
        closed = close_open_for(p, user, TaskResult.MOVED_AWAY, note)
        log_audit(user, "Recorded follow-up outcome", _entity(task), person_name(task),
                  f"Moved away or left. {closed} open task(s) closed", instance=task)


def close_open_for(person, user, result, note):
    """Close every open task for a person, for example when they leave."""
    from members.models import Member, MemberFollowUpTask
    from newcomers.models import NewcomerTask
    now = timezone.now()
    qs = (MemberFollowUpTask.objects.filter(member=person) if isinstance(person, Member)
          else NewcomerTask.objects.filter(newcomer=person))
    return qs.filter(done=False).update(done=True, result=result, result_note=note[:500], closed_at=now,
                                        closed_by=user)


CANCEL_REASONS = {
    "was-at-service": "The person was at the service",
    "did-not-hold": "The service did not hold",
    "left": "The person has left the church",
    "other": "Other",
}


def cancel(task, user, reason, note=""):
    from .followup_access import can_cancel
    if not can_cancel(user, location_id(task)):
        raise PermissionDenied("Only a Follow-up Coordinator or an administrator can cancel a task, because a "
                               "cancelled task never reaches the shepherd's record.")
    if task.done:
        raise ValidationError({"detail": "This task is already closed."})
    if reason not in CANCEL_REASONS:
        raise ValidationError({"reason": "Choose why it was made in error."})
    text = CANCEL_REASONS[reason] + (f": {note.strip()}" if (note or "").strip() else "")
    _close(task, user, TaskResult.CANCELLED, text)
    task.save()
    log_audit(user, "Cancelled follow-up task", _entity(task), person_name(task), text, instance=task)


def change_due(task, user, due_at, why):
    from .followup_access import can_manage_task
    if not can_manage_task(user, location_id(task)):
        raise PermissionDenied("Only a Follow-up Coordinator or an administrator can change a due time, so the "
                               "time limits stay the same for every shepherd.")
    if task.done:
        raise ValidationError({"detail": "This task is already closed."})
    if due_at <= timezone.now():
        raise ValidationError({"due_at": "Choose a time that has not passed yet."})
    why = (why or "").strip()
    if not why:
        raise ValidationError({"why": "Say why the due time changes. It is kept with the task."})
    before = task.due_at
    task.due_at = due_at
    task.due_date = timezone.localtime(due_at).date()
    task.save(update_fields=["due_at", "due_date"])
    after = f"{timezone.localtime(due_at):%-d %b %H:%M}"
    detail = (f"{timezone.localtime(before):%-d %b %H:%M} to {after}" if before else f"to {after}") + f". {why}"
    log_audit(user, "Changed due time", _entity(task), person_name(task), detail, instance=task)


def set_away(person, user, away_from, away_to, reason, note=""):
    if away_to < away_from:
        raise ValidationError({"away_to": "The end date must be on or after the start date."})
    if (away_to - away_from).days > 366:
        raise ValidationError({"away_to": "Away can be set for up to a year at a time."})
    person.away_from, person.away_to, person.away_reason = away_from, away_to, reason
    person.away_note = (note or "")[:300]
    person.save(update_fields=["away_from", "away_to", "away_reason", "away_note"])
    name = getattr(person, "full_name", None) or person.name
    log_audit(user, "Marked away", "Member" if hasattr(person, "full_name") else "Newcomer", name,
              f"{away_from:%-d %b} to {away_to:%-d %b %Y}" + (f", {reason}" if reason else ""))


def clear_away(person, user):
    person.away_from = person.away_to = None
    person.away_reason, person.away_note = "", ""
    person.save(update_fields=["away_from", "away_to", "away_reason", "away_note"])
    name = getattr(person, "full_name", None) or person.name
    log_audit(user, "Cleared away dates", "Member" if hasattr(person, "full_name") else "Newcomer", name)


def move_open_tasks(person, new_user_id):
    """
    A person's shepherd changed for good: their open tasks move with them
    (Kay, 26 October 2026). A task handed to someone for that task only,
    and the Follow-up Coordinator's own visit task, stay where they are.
    With nobody new, the tasks go to the Follow-up Coordinator.
    """
    from members.models import Member, MemberFollowUpTask
    from newcomers.models import NewcomerTask
    qs = (MemberFollowUpTask.objects.filter(member=person) if isinstance(person, Member)
          else NewcomerTask.objects.filter(newcomer=person))
    qs = qs.filter(done=False, handed_from__isnull=True).exclude(kind=TaskKind.COORDINATOR_VISIT)
    if new_user_id:
        return qs.update(assigned_to_id=new_user_id, escalation="")
    from .followup_access import coordinators_for
    coords = coordinators_for(person.location_id)
    if not coords:
        return 0
    return qs.update(assigned_to_id=coords[0].id, escalation=Escalation.NO_SHEPHERD, escalated_at=timezone.now())


def release_tasks(user):
    """
    A shepherd switched off or no longer shepherding: each open task goes
    to the person's shepherd if that is someone else who can shepherd, or
    else to the Follow-up Coordinator, never left with nobody.
    """
    from members.models import MemberFollowUpTask
    from newcomers.models import NewcomerTask
    from .followup_access import coordinators_for
    moved = 0
    for t in list(MemberFollowUpTask.objects.filter(assigned_to=user, done=False).select_related("member__assigned_to")) + \
            list(NewcomerTask.objects.filter(assigned_to=user, done=False).select_related("newcomer__assigned_to")):
        p = person_of(t)
        s = p.assigned_to
        if s and s.id != user.id and s.is_active and s.can_shepherd:
            t.assigned_to, t.escalation = s, ""
        else:
            coords = [c for c in coordinators_for(p.location_id) if c.id != user.id]
            if not coords:
                continue
            t.assigned_to, t.escalation, t.escalated_at = coords[0], Escalation.NO_SHEPHERD, timezone.now()
        t.save(update_fields=["assigned_to", "escalation", "escalated_at"])
        moved += 1
    return moved
