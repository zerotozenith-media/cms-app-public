"""
Lapsed (13 November 2026).

Somebody who misses the same meeting the number of times in a row set in
Follow-up Rules (3 at first) becomes Lapsed: their open absence tasks
close, no more absence tasks are made, and the Follow-up Coordinator
decides on the Review list:

  - Follow up again: Lapsed ends, and misses before today no longer count;
  - Left the church (a member) or Not Interested (a newcomer).

Being ticked present at any service ends Lapsed on its own.

The one-off cleanup (Admin, Follow-up Rules) applies the same rules to the
tasks made before this change: extra open absence tasks are added to the
person's oldest open one, and anyone already at the Lapsed number of misses
becomes Lapsed.
"""
from django.db import transaction
from django.utils import timezone

from accounts.audit import log_audit

CHOICES = ("again", "left")


def _is_member(person):
    from members.models import Member
    return isinstance(person, Member)


def name_of(person):
    return person.full_name if _is_member(person) else person.name


def _tasks(person):
    from members.models import MemberFollowUpTask
    from newcomers.models import NewcomerTask
    return (MemberFollowUpTask.objects.filter(member=person) if _is_member(person)
            else NewcomerTask.objects.filter(newcomer=person))


def _link(person):
    return f"/members/{person.id}" if _is_member(person) else f"/newcomers/{person.id}"


def make_lapsed(person, session, run, now=None, alert=True):
    """Mark the person Lapsed after `run` misses in a row of the session's
    meeting. Their open absence tasks close as Lapsed."""
    from .accountable import TaskKind, TaskResult
    from .task_actions import ABSENCE_KINDS
    now = now or timezone.now()
    meeting = session.meeting_type.name
    person.lapsed_since, person.lapsed_meeting, person.lapsed_run = session.date, meeting, run
    person.save(update_fields=["lapsed_since", "lapsed_meeting", "lapsed_run"])
    note = (f"Missed {run} {meeting} in a row, so they are Lapsed. "
            f"The Follow-up Coordinator decides what happens next.")
    # The Follow-up Coordinator's own visit task closes too: the Lapsed
    # decision replaces it.
    open_tasks = _tasks(person).filter(done=False, kind__in=ABSENCE_KINDS + [TaskKind.COORDINATOR_VISIT])
    shepherds = set(open_tasks.exclude(assigned_to=None).values_list("assigned_to_id", flat=True))
    open_tasks.update(done=True, result=TaskResult.LAPSED, result_note=note, closed_at=now)
    log_audit(None, "Marked Lapsed", "Member" if _is_member(person) else "Newcomer", name_of(person),
              f"{run} {meeting} missed in a row.", instance=person)
    if alert:
        from alerts.events import notify
        from .followup_access import coordinators_for
        name = name_of(person)
        notify([u.id for u in coordinators_for(person.location_id)], f"{name} is now Lapsed",
               f"Missed {run} {meeting} in a row. On your Review list, choose Follow up again, or "
               f"{'Left the church' if _is_member(person) else 'Not Interested'}.",
               "/followup-review", f"lapsed-{type(person).__name__}-{person.id}")
        if shepherds:
            notify(sorted(shepherds), f"{name} is now Lapsed",
                   "Your open task for them is closed, and no more are made. The Follow-up Coordinator decides "
                   "what happens next.", _link(person), f"lapsed-s-{type(person).__name__}-{person.id}")


def back_from_lapsed(person, session):
    """Ticked present at a service: Lapsed ends and follow-up carries on."""
    if not person.lapsed_since:
        return
    person.lapsed_since, person.lapsed_meeting = None, ""
    person.save(update_fields=["lapsed_since", "lapsed_meeting"])
    log_audit(None, "Back from Lapsed", "Member" if _is_member(person) else "Newcomer", name_of(person),
              f"Ticked present at {session.meeting_type.name} on {session.date:%-d %B %Y}.", instance=person)
    from alerts.events import notify
    from .followup_access import coordinators_for
    notify([u.id for u in coordinators_for(person.location_id)], f"{name_of(person)} was at {session.meeting_type.name}",
           "No longer Lapsed. Follow-up carries on as normal.", _link(person),
           f"unlapsed-{type(person).__name__}-{person.id}-{session.id}")


def lapsed_people(location_id=None):
    """Everyone Lapsed and still on the books, for the Review list."""
    from core.followup_rules import rules
    from members.models import Member
    from newcomers.models import Newcomer
    members = Member.objects.filter(lapsed_since__isnull=False, status=Member.Status.ACTIVE).select_related(
        "location", "assigned_to")
    newcomers = Newcomer.objects.filter(lapsed_since__isnull=False, stage__in=rules().stages).select_related(
        "location", "assigned_to")
    if location_id:
        members, newcomers = members.filter(location_id=location_id), newcomers.filter(location_id=location_id)
    from accounts.names import display_name
    rows = []
    for p in list(members) + list(newcomers):
        member = _is_member(p)
        rows.append({
            "kind": "member" if member else "newcomer", "id": p.id, "name": name_of(p),
            "location": p.location.name if p.location_id else "",
            "since": p.lapsed_since.isoformat(), "meeting": p.lapsed_meeting, "run": p.lapsed_run,
            "shepherd": display_name(p.assigned_to) if p.assigned_to_id else "",
            "link": _link(p),
            "left_label": "Left the church" if member else "Not Interested",
        })
    rows.sort(key=lambda r: (r["since"], r["name"]))
    return rows


def decide(person, user, choice, note=""):
    from rest_framework.exceptions import PermissionDenied, ValidationError
    from .accountable import TaskResult
    from .followup_access import can_review
    from .task_actions import close_open_for
    if not can_review(user, person.location_id):
        raise PermissionDenied("Only a Follow-up Coordinator or an administrator decides about someone who is "
                               "Lapsed, because it changes whether they are followed up.")
    if not person.lapsed_since:
        raise ValidationError({"detail": f"{name_of(person)} is no longer Lapsed, so there is nothing to decide. "
                                         "They may have been ticked present since."})
    if choice not in CHOICES:
        raise ValidationError({"choice": "Choose Follow up again, or mark them as left."})
    note = (note or "").strip()[:300]
    today = timezone.localdate()
    entity = "Member" if _is_member(person) else "Newcomer"
    with transaction.atomic():
        if choice == "again":
            person.lapsed_since, person.lapsed_meeting, person.follow_up_from = None, "", today
            person.save(update_fields=["lapsed_since", "lapsed_meeting", "follow_up_from"])
            log_audit(user, "Follow up again after Lapsed", entity, name_of(person), note, instance=person)
            return "again"
        text = note or "Lapsed, and the Follow-up Coordinator marked them as left."
        if _is_member(person):
            from members.models import Member
            person.status, person.status_date, person.status_note = Member.Status.LEFT, today, text
            person.lapsed_since, person.lapsed_meeting = None, ""
            person.save(update_fields=["status", "status_date", "status_note", "lapsed_since", "lapsed_meeting"])
        else:
            from newcomers.models import Newcomer, NewcomerStatusHistory
            NewcomerStatusHistory.objects.create(newcomer=person, stage=Newcomer.Stage.NOT_INTERESTED, note=text,
                                                 date=today)
            person.stage, person.stage_since, person.not_interested_note = Newcomer.Stage.NOT_INTERESTED, today, text
            person.lapsed_since, person.lapsed_meeting = None, ""
            person.save(update_fields=["stage", "stage_since", "not_interested_note", "lapsed_since",
                                       "lapsed_meeting"])
        close_open_for(person, user, TaskResult.MOVED_AWAY, text)
        log_audit(user, "Marked left after Lapsed" if _is_member(person) else "Marked Not Interested after Lapsed",
                  entity, name_of(person), text, instance=person)
    return "left"


# One-off cleanup -----------------------------------------------------------

def _merge_open():
    """Extra open absence tasks join the person's oldest open one."""
    from attendance.absence import refresh_open
    from members.models import MemberFollowUpTask
    from newcomers.models import NewcomerTask
    from .accountable import TaskKind, TaskResult
    now = timezone.now()
    joined, people = 0, 0
    for model, field in ((MemberFollowUpTask, "member_id"), (NewcomerTask, "newcomer_id")):
        by_person = {}
        for t in model.objects.filter(kind=TaskKind.ABSENCE, done=False).order_by("created_at", "id"):
            by_person.setdefault(getattr(t, field), []).append(t)
        for tasks in by_person.values():
            if len(tasks) < 2:
                continue
            keep, rest = tasks[0], tasks[1:]
            for t in rest:
                t.done, t.result, t.closed_at, t.covered_by = True, TaskResult.JOINED, now, keep
                t.result_note = "Added to the open task by the one-off cleanup."
                t.save(update_fields=["done", "result", "closed_at", "covered_by", "result_note"])
            refresh_open(keep)
            joined += len(rest)
            people += 1
    return joined, people


def _lapse_now(limit):
    """Anyone whose latest tracked service makes `limit` misses in a row."""
    from attendance.absence import expected_members, expected_newcomers, missed_in_row
    from attendance.models import AttendanceSession, MeetingType
    found = []
    seen = set()
    for mt in MeetingType.objects.filter(counts_for_absence=True):
        sessions = (AttendanceSession.objects.filter(meeting_type=mt)
                    .exclude(status=AttendanceSession.Status.DID_NOT_HOLD)
                    .filter(attendees__member__isnull=False).distinct().order_by("-date", "-id"))
        latest = {}
        for s in sessions[:200]:
            latest.setdefault((s.location_id, s.fellowship_id), s)
        for s in latest.values():
            ticked = set(s.attendees.filter(member__isnull=False).values_list("member_id", flat=True))
            ticked_n = set(s.attendees.filter(newcomer__isnull=False).values_list("newcomer_id", flat=True))
            for m in expected_members(s).exclude(id__in=ticked):
                run = missed_in_row(s, member=m)
                if run >= limit and ("m", m.id) not in seen:
                    seen.add(("m", m.id))
                    found.append((m, s, run))
            for n in expected_newcomers(s).exclude(id__in=ticked_n):
                run = missed_in_row(s, newcomer=n)
                if run >= limit and ("n", n.id) not in seen:
                    seen.add(("n", n.id))
                    found.append((n, s, run))
    return found


def cleanup(user, apply=False):
    """
    The one-off cleanup. With apply False nothing changes: the same work is
    done and rolled back, so the counts shown match what pressing it does.
    """
    from .followup_rules import rules
    r = rules()
    out = {}
    with transaction.atomic():
        joined, people = _merge_open()
        found = _lapse_now(r.lapsed_after_misses) if r.lapsed_after_misses else []
        for person, session, run in found:
            make_lapsed(person, session, run, alert=False)
        out = {"tasks_joined": joined, "people_with_extra_tasks": people, "lapsed": len(found),
               "lapsed_names": sorted(name_of(p) for p, _, _ in found)[:50]}
        if not apply:
            transaction.set_rollback(True)
            return out
    log_audit(user, "Ran the one-off follow-up cleanup", "Follow-up Rules", "Follow-up Rules",
              f"{joined} extra task(s) added to open tasks for {people} people. {len(found)} people marked Lapsed.")
    if found:
        from alerts.events import notify
        from .followup_access import coordinators_for
        by_coord = {}
        for p, _, _ in found:
            for u in coordinators_for(p.location_id):
                by_coord[u.id] = by_coord.get(u.id, 0) + 1
        for uid, n in by_coord.items():
            notify([uid], f"{n} {'person is' if n == 1 else 'people are'} now Lapsed",
                   "The one-off cleanup found them. Decide for each on your Review list.", "/followup-review",
                   f"cleanup-{uid}-{timezone.now():%Y%m%d%H%M}")
    return out
