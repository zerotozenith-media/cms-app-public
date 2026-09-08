"""
One person's history, gathered from everywhere it is recorded.

The records live in several places because they are different kinds of
thing: stage changes, completed follow-ups, attempts that did not reach
anyone, milestones, and the day they joined. A leader reading a profile
wants none of that structure, only the story in order.
"""
from newcomers.models import Newcomer


def build_journey(newcomer):
    """Every event for this person, oldest first."""
    events = []

    events.append({
        "date": newcomer.created_at,
        "kind": "registered",
        "title": "Registered as a newcomer",
        "detail": f"Came through {newcomer.source.name}" if newcomer.source else "",
        "by": "",
    })

    for h in newcomer.status_history.all():
        events.append({
            "date": h.date,
            "kind": "stage",
            "title": f"Moved to {h.get_stage_display()}",
            "detail": h.note or "",
            "by": "",
        })

    for t in newcomer.tasks.filter(done=True):
        events.append({
            "date": t.contact_date or t.due_date,
            "kind": "contact",
            "title": t.text,
            "method": t.contact_method,
            "by": _name(t.assigned_to),
            "log": {
                "goal": t.contact_goal,
                "scripture": t.contact_scripture,
                "root_cause": t.contact_root_cause,
                "next_step": t.contact_next_step,
            },
        })

    # Attempts that did not reach anyone. Without these the record
    # flatters the work: three unanswered calls look like nobody tried.
    for a in newcomer.contact_attempts.all():
        events.append({
            "date": a.date,
            "kind": "attempt",
            "title": f"{a.method}, no reply",
            "detail": a.note or "",
            "by": _name(a.by),
        })

    for m in newcomer.milestones.filter(achieved_date__isnull=False):
        events.append({
            "date": m.achieved_date,
            "kind": "milestone",
            "title": f"{m.milestone_type.name} recorded",
            "detail": "",
            "by": "",
        })

    member = getattr(newcomer, "became_member", None)
    if member:
        events.append({
            "date": member.joined_date,
            "kind": "member",
            "title": "Added to the member roll",
            "detail": "This history stays with them.",
            "by": "",
        })

    events.sort(key=lambda e: (e["date"], e["kind"]))
    return events


def _name(user):
    if not user:
        return ""
    from accounts.names import display_name
    return display_name(user)
