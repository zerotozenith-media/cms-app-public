"""
Who follows up online contacts (Kay, 10 October 2026).

Contacts are not tied to a location, so anyone ticked "Can shepherd others"
whose role can work on contacts (the newcomers permission, which Online
Enquiries uses) may be given them. Auto-assign shares only contacts still
being followed up, giving each to the person with the fewest, and saves
nothing until the caller applies the changes.
"""
from accounts.gender import choose, shepherd_gender, skipped_notice
from accounts.names import display_name
from accounts.permissions import user_has
from members.assignment import eligible_shepherds

from .models import Enquiry

ACTIVE_EXCLUDE = [Enquiry.Stage.ATTENDED, Enquiry.Stage.NOT_PURSUING]


def followup_people():
    return sorted((u for u in eligible_shepherds() if user_has(u, "newcomers", "can_edit")), key=display_name)


def active_contacts():
    return Enquiry.objects.exclude(stage__in=ACTIVE_EXCLUDE)


def contact_load(people):
    load = {p.id: 0 for p in people}
    for pid in active_contacts().filter(assigned_to_id__in=load).values_list("assigned_to_id", flat=True):
        load[pid] += 1
    return load


def people_payload():
    people = followup_people()
    load = contact_load(people)
    return [{"id": p.id, "name": display_name(p), "contacts": load[p.id], "gender": shepherd_gender(p)} for p in people]


def build_preview(everyone=False):
    people = followup_people()
    if not people:
        return {"people": [], "rows": [], "error": "Nobody is set up to follow up contacts. In Admin, tick Can shepherd others on an account whose role can work on newcomers."}
    before = contact_load(people)
    load = dict.fromkeys(before, 0) if everyone else dict(before)
    qs = active_contacts().select_related("assigned_to", "assigned_to__member").order_by("name", "id")
    if not everyone:
        qs = qs.filter(assigned_to__isnull=True)
    names = {p.id: display_name(p) for p in people}
    by_id = {p.id: p for p in people}
    order = [p.id for p in people]
    rows = []
    for e in qs:
        pick, reason, warn = choose(e.gender, load, order, by_id)
        if not pick and e.assigned_to_id:
            # Nobody suitable: never strip someone of the person they have.
            pick, reason = e.assigned_to_id, reason.replace("Left unassigned.", "Left as it is.")
        if pick in load:
            load[pick] += 1
        rows.append({"enquiry": e.id, "name": e.name, "gender": e.gender,
                     "current": display_name(e.assigned_to) if e.assigned_to else "",
                     "proposed": pick, "proposed_name": names.get(pick, "") or (display_name(e.assigned_to) if pick and e.assigned_to else ""), "reason": reason, "warn": warn})
    people_rows = [{"id": pid, "name": names[pid], "gender": shepherd_gender(by_id[pid]),
                    "now": before[pid], "after": load[pid]} for pid in order]
    return {"people": people_rows, "rows": rows, "notice": skipped_notice(people)}
