"""
What happens after follow-up tasks are made or change (Kay, 26 October
2026):

  - a task with no shepherd goes to the Follow-up Coordinator, never left
    Unassigned;
  - the Follow-up Coordinator is alerted when someone misses the same
    meeting a 2nd time in a row, then again on every further miss;
  - at the 3rd miss in a row the Follow-up Coordinator gets a visit task
    of their own, one for the whole run;
  - a task handed over (needs the Follow-up Coordinator, or the attempts
    ran out) alerts the Follow-up Coordinator;
  - a reason given, and a Follow-up Coordinator's decision, reach the
    right person in the app and on the phone.

The numbers come from Follow-up Rules.
"""
from django.utils import timezone

from accounts.names import display_name


def _notify(ids, title, body, url, tag):
    from alerts.events import notify
    return notify(ids, title, body, url, tag)


def _link(task):
    from .task_actions import is_member_task, person_of
    p = person_of(task)
    return f"/members/{p.id}" if is_member_task(task) else f"/newcomers/{p.id}"


def _ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _alert_now(run, r):
    if run < r.alert_from_miss:
        return False
    return r.alert_repeat == "every" or (run - r.alert_from_miss) % 2 == 0


def tasks_made(tasks):
    """Called with every absence task the check or a person makes."""
    from .accountable import Escalation, TaskKind
    from .followup_access import coordinators_for
    from .followup_rules import rules
    from .task_actions import is_member_task, person_name, person_of
    if not tasks:
        return
    from collections import defaultdict
    r = rules()
    per_shepherd = defaultdict(list)
    for t in tasks:
        p = person_of(t)
        coords = coordinators_for(p.location_id)
        name = person_name(t)
        if not t.assigned_to_id and coords:
            t.assigned_to = coords[0]
            t.escalation, t.escalated_at = Escalation.NO_SHEPHERD, timezone.now()
            t.save(update_fields=["assigned_to", "escalation", "escalated_at"])
            _notify([coords[0].id], f"{name} has no shepherd",
                    f"Their task for {t.missed_meeting_name or 'a service'} is yours until a shepherd is chosen.",
                    _link(t), f"noshepherd-{t.id}")
        elif t.assigned_to_id:
            per_shepherd[t.assigned_to_id].append((name, t))
        run = t.missed_in_row or 0
        if t.kind == TaskKind.ABSENCE and _alert_now(run, r):
            shep = display_name(t.assigned_to) if t.assigned_to_id else "none"
            extra = ""
            if run == r.visit_task_at_miss:
                v = visit_task(t, coords[0] if coords else None)
                extra = " A visit task for you is on your list." if v else ""
            _notify([u.id for u in coords], f"{name} missed a {_ordinal(run)} {t.missed_meeting_name} in a row",
                    f"Shepherd: {shep}.{extra}", _link(t), f"run-{type(t).__name__}-{p.id}-{run}")
    # One alert per shepherd, naming the people, rather than one per task.
    for uid, items in per_shepherd.items():
        names = [n for n, _ in items]
        first = items[0][1]
        due = timezone.localtime(first.due_at)
        who = names[0] if len(names) == 1 else (", ".join(names[:2]) + (f" and {len(names) - 2} more" if len(names) > 2 else ""))
        _notify([uid], f"{len(names)} {'person' if len(names) == 1 else 'people'} to follow up",
                f"{who} missed {first.missed_meeting_name}. Due {due:%A %-d %B, %-I:%M %p}.",
                "/follow-up", f"made-{uid}-{first.missed_session_id}")


def visit_task(task, coordinator):
    """The Follow-up Coordinator's own visit task, beside the shepherd's,
    one for the whole run of misses."""
    from .accountable import TaskKind
    from .followup_rules import deadlines, rules
    from .task_actions import is_member_task, person_tasks
    if coordinator is None:
        return None
    if person_tasks(task).filter(kind=TaskKind.COORDINATOR_VISIT, done=False).exists():
        return None
    model = type(task)
    who = {"member": task.member} if is_member_task(task) else {"newcomer": task.newcomer}
    now = timezone.now()
    due = deadlines(now, rules())["due_at"]
    return model.objects.create(
        kind=TaskKind.COORDINATOR_VISIT, text=f"Visit: {task.missed_in_row} {task.missed_meeting_name} missed in a row",
        due_date=timezone.localtime(due).date(), due_at=due, clock_start=now, created_at=now,
        assigned_to=coordinator, missed_session=task.missed_session, missed_meeting_name=task.missed_meeting_name,
        missed_date=task.missed_date, missed_in_row=task.missed_in_row, **who)


def escalated(task, user=None):
    """A task handed to the Follow-up Coordinator: the shepherd asked for
    help, or the attempts set in Follow-up Rules ran out."""
    from .followup_access import coordinators_for
    from .task_actions import location_id, person_name
    coords = [u.id for u in coordinators_for(location_id(task)) if not user or u.id != user.id]
    why = {"needs-coordinator": "needs the Follow-up Coordinator", "attempts": "could not be reached after several attempts"}
    _notify(coords, f"{person_name(task)}: {why.get(task.escalation, 'needs you')}",
            "The task is on your Review list.", "/followup-review", f"esc-{task.id}")


def reason_given(task, rnd):
    from .followup_access import coordinators_for
    from .followup_review import decide_by
    from .task_actions import location_id, person_name
    coords = [u.id for u in coordinators_for(location_id(task))]
    _notify(coords, f"{person_name(task)}: reason given for a late task",
            f"{rnd.get_reason_display()}. Decide by {timezone.localtime(decide_by(task)):%A %-d %B, %-I:%M %p}.",
            "/followup-review", f"reason-{rnd.id}")


def reasons_given(user, done):
    """Several reasons sent together: one alert per coordinator, naming the
    people, rather than one per task."""
    from collections import defaultdict
    from .followup_access import coordinators_for
    from .task_actions import location_id, person_name
    per = defaultdict(list)
    for task, rnd in done:
        for u in coordinators_for(location_id(task)):
            if u.id != user.id:
                per[u.id].append(person_name(task))
    for uid, names in per.items():
        uniq = sorted(set(names))
        who = ", ".join(uniq[:3]) + (f" and {len(uniq) - 3} more" if len(uniq) > 3 else "")
        _notify([uid], f"{display_name(user)} gave reasons for {len(names)} late task{'s' if len(names) != 1 else ''}",
                f"{who}. They are on your Review list.", "/followup-review", f"reasons-{user.id}-{timezone.now():%Y%m%d%H%M}")


def decided(task, rnd, user):
    """Each choice reaches the shepherd on the task itself, in the app and on
    the phone; handing on also tells the new shepherd."""
    from .task_actions import person_name
    name = person_name(task)
    by = display_name(user)
    to_shepherd = {
        "accept": f"{by} accepted your reason. The new date stands.",
        "hand-on": f"{by} handed this task to {display_name(rnd.handed_to) if rnd.handed_to_id else 'another shepherd'}.",
        "take": f"{by} is taking this task on.",
        "ask": f"{by} asks: {rnd.choice_note}",
    }[rnd.choice]
    shepherd = task.handed_from_id if rnd.choice in ("hand-on", "take") else task.assigned_to_id
    if shepherd and shepherd != user.id:
        _notify([shepherd], f"{name}: {rnd.get_choice_display()}", to_shepherd, "/follow-up", f"dec-{rnd.id}")
    if rnd.choice == "hand-on" and rnd.handed_to_id and rnd.handed_to_id != user.id:
        _notify([rnd.handed_to_id], f"Task handed to you: {name}",
                f"From {by}, for this task only. Due {timezone.localtime(task.due_at):%A %-d %B, %-I:%M %p}.",
                "/follow-up", f"handed-{rnd.id}")
