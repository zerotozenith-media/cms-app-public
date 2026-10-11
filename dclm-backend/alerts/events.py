"""
The alerts the system sends by itself when something happens. Each is
called from the place the change is made, and sends only after it is saved.
"""
from collections import defaultdict

from accounts.names import display_name

from .push import send_later

LINKS = {"member": "/members/{}", "newcomer": "/newcomers/{}", "contact": "/enquiries/{}"}


def _names(names):
    names = list(names)
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return f"{names[0]}, {names[1]} and {len(names) - 2} more"


def given(pairs, by=None):
    """People newly given to a shepherd or follow-up person.
    pairs: (kind, id, name, new_assignee_id) for each person whose assignee
    changed to someone. Nobody is told about people they gave themselves."""
    if by is None:
        from core.audit_context import current_user_var
        by = current_user_var.get()
    per = defaultdict(list)
    for kind, pk, name, to in pairs:
        if to and (by is None or to != by.pk):
            per[to].append((kind, pk, name))
    for to, people in per.items():
        n = len(people)
        title = f"{n} {'person' if n == 1 else 'people'} given to you"
        body = f"{_names(p[2] for p in people)} {'is' if n == 1 else 'are'} yours to follow up."
        kind, pk, _ = people[0]
        url = LINKS[kind].format(pk) if n == 1 else {"member": "/members", "newcomer": "/newcomers", "contact": "/enquiries"}[kind]
        send_later(to, "assigned", title, body, url, tag=f"given-{kind}-{pk}" if n == 1 else "given")


def arrival(kind, obj, by=None):
    """Someone contacted the church online, or registered as a newcomer.
    Goes to people who look after arrivals there: roles that can change
    newcomers and see the whole picture (Admin access), at that location
    or covering every location."""
    from accounts.models import User
    from accounts.permissions import user_has
    loc = getattr(obj, "location_id", None)
    ids = []
    for u in User.objects.filter(is_active=True).select_related("role"):
        if by is not None and u.pk == by.pk:
            continue
        if not (user_has(u, "newcomers", "can_edit") and user_has(u, "admin", "can_view")):
            continue
        if loc and u.location_id and u.location_id != loc:
            continue
        ids.append(u.pk)
    if kind == "contact":
        src = getattr(getattr(obj, "source", None), "name", "") or "online"
        title, body, url = f"New contact from {src}", f"{obj.name} is waiting for a reply.", f"/enquiries/{obj.pk}"
    else:
        where = getattr(getattr(obj, "location", None), "name", "") or ""
        who = f" and was given to {display_name(obj.assigned_to)}" if getattr(obj, "assigned_to_id", None) else ""
        title = "New newcomer registered"
        body = f"{obj.name} registered{' at ' + where if where else ''}{who}."
        url = f"/newcomers/{obj.pk}"
    send_later(ids, "arrivals", title, body, url, tag=f"{kind}-{obj.pk}")
