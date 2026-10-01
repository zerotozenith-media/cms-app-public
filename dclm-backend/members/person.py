"""
One person, one story (F16).

A newcomer who became a member used to have two pages: the member profile
showed none of the newcomer history, although all of it still existed,
including open newcomer tasks, which became invisible. This builds one
summary for either page, so the profile is the same before and after
membership and the journey simply continues.
"""
from attendance.models import AttendanceSessionMember
from newcomers.journey import build_journey, _name
from newcomers.models import MilestoneType


def _date(d):
    return d.date() if hasattr(d, "date") and callable(d.date) else d


def build_person(member=None, newcomer=None):
    if member is not None and newcomer is None:
        newcomer = member.from_newcomer
    events = []

    if newcomer is not None:
        # The newcomer's own story, without its closing "added to the roll"
        # line: the member part below says it with the category.
        # The stage change to Member is said by "Became a member" below.
        events += [e for e in build_journey(newcomer)
                   if e["kind"] != "member" and not (e["kind"] == "stage" and e["title"] == "Moved to Member")]

    if member is not None:
        events.append({
            "date": member.joined_date, "kind": "member",
            "title": "Became a member",
            "detail": "Joined the member roll" if not newcomer else "Joined the member roll from the newcomer pipeline",
            "by": "",
        })
        for h in member.category_history.all():
            events.append({
                "date": h.changed_date, "kind": "category",
                "title": f"Moved to {h.get_to_category_display()}",
                "detail": f"From {h.get_from_category_display()}", "by": "",
            })
        for t in member.followup_tasks.filter(done=True):
            events.append({
                "date": getattr(t, "contact_date", None) or t.due_date, "kind": "contact",
                "title": t.text, "method": getattr(t, "contact_method", ""),
                "by": _name(t.assigned_to), "detail": "",
            })

    for e in events:
        e["date"] = _date(e["date"])
    # Newest first. On the same day, events keep their natural order: first
    # came, contacts, stage changes, milestones, then membership.
    rank = {"registered": 0, "attempt": 1, "contact": 2, "stage": 3, "milestone": 4, "member": 5, "category": 6}
    events.sort(key=lambda e: (e["date"], rank.get(e["kind"], 3)), reverse=True)
    for e in events:
        e["date"] = e["date"].isoformat() if e["date"] else ""

    # Milestones: every type, reached or not, so the next step is visible.
    reached = {}
    if newcomer is not None:
        reached = {m.milestone_type_id: m.achieved_date for m in newcomer.milestones.all() if m.achieved_date}
    milestones = [{"name": t.name, "date": reached[t.id].isoformat() if t.id in reached else None}
                  for t in MilestoneType.objects.all()]

    # Open follow-ups of both kinds. Open newcomer tasks were invisible once
    # the person became a member.
    open_tasks = []
    if newcomer is not None:
        open_tasks += [{"kind": "newcomer", "id": t.id, "text": t.text, "due_date": t.due_date.isoformat(),
                        "by": _name(t.assigned_to)} for t in newcomer.tasks.filter(done=False)]
    if member is not None:
        open_tasks += [{"kind": "member", "id": t.id, "text": t.text, "due_date": t.due_date.isoformat(),
                        "by": _name(t.assigned_to)} for t in member.followup_tasks.filter(done=False)]
    open_tasks.sort(key=lambda t: t["due_date"])

    # Every check-in, as a newcomer and as a member.
    from django.db.models import Q
    who = Q(pk__in=[])
    if newcomer is not None:
        who |= Q(newcomer=newcomer)
    if member is not None:
        who |= Q(member=member)
    checkins = AttendanceSessionMember.objects.filter(who).select_related("session__meeting_type").order_by("-session__date")
    attendance = {
        "count": checkins.count(),
        "recent": [{"date": c.session.date.isoformat(), "meeting": c.session.meeting_type.name,
                    "as": "newcomer" if c.newcomer_id else "member"} for c in checkins[:12]],
    }

    # First came: registration or the first check-in, whichever is earlier.
    # Someone added later from an enquiry may have been attending for months.
    first_came = _date(newcomer.created_at) if newcomer is not None else None
    first_checkin = checkins.order_by("session__date").values_list("session__date", flat=True).first()
    if first_checkin and (first_came is None or first_checkin < first_came):
        first_came = first_checkin
    return {
        "first_came": first_came.isoformat() if first_came else None,
        "how_came": newcomer.source.name if newcomer is not None and newcomer.source_id else "",
        "newcomer_id": newcomer.id if newcomer is not None else None,
        "member_id": member.id if member is not None else getattr(getattr(newcomer, "became_member", None), "id", None),
        "journey": events,
        "milestones": milestones,
        "open_follow_ups": open_tasks,
        "attendance": attendance,
    }
