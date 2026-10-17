"""
Shepherd assignment rules, kept separate from the views so the logic can
be tested on its own and reused by any caller.

Confirmed design:
  1. Only accounts ticked "Can shepherd others" in Admin can be shepherds.
  2. Household first, so families are not split across different workers.
  3. Then load balancing, by how many people a worker already carries.
     Deliberately counts people shepherded rather than open tasks, since
     open task counts fluctuate week to week and would cause churn.
  4. Only fills people with no shepherd unless reassign_everyone is set,
     so pairings someone chose on purpose are not silently overwritten.
     The exception is a shepherd who breaks a rule: a man shepherding a
     woman, a woman shepherding a man, or someone shepherding themselves.
     Those are always proposed for correction (members/shepherd_rules.py).
  5. Nothing is saved until the caller applies the proposed changes.
"""
from accounts.models import User
from core.models import AppSetting
from members.models import Member
from newcomers.models import Newcomer
from accounts.names import display_name

SETTING_AUTO_ASSIGN_NEWCOMERS = "auto_assign_newcomers"


def eligible_shepherds(location=None):
    """
    Who people can be assigned to: active accounts ticked "Can shepherd
    others" in Admin (F7). This used to follow the Worker member category,
    but a shepherd need not be an approved Worker, and a Worker need not
    shepherd.

    An account limited to one location shepherds there, whatever location
    its member record shows: it cannot even see people elsewhere (found in
    the manual check). An account covering every location shepherds at its
    member record's location, or anywhere if it has none.
    """
    from django.db.models import Q
    qs = User.objects.filter(is_active=True, can_shepherd=True).select_related("member")
    if location:
        loc = getattr(location, "pk", location)
        qs = qs.filter(
            Q(location_id=loc)
            | Q(location__isnull=True, member__location_id=loc)
            | Q(location__isnull=True, member__isnull=True)
        )
    return list(qs)


def _shepherd_name(u):
    # Thin alias so this module reads naturally; the rule itself lives in
    # accounts.names so every screen shows the same name for a person.
    return display_name(u)


def current_load(shepherds):
    """How many people each shepherd already carries, members and
    newcomers combined, since both draw on the same person's time."""
    load = {s.id: 0 for s in shepherds}
    for m in Member.objects.filter(assigned_to_id__in=load.keys()):
        load[m.assigned_to_id] += 1
    for n in Newcomer.objects.filter(assigned_to_id__in=load.keys()):
        load[n.assigned_to_id] += 1
    return load


def _least_loaded(load):
    if not load:
        return None
    return min(load, key=lambda k: load[k])


def build_assignment_preview(location=None, reassign_everyone=False):
    """
    Returns (changes, error). Never writes anything.
    Each change is a dict the API can serialise directly and the UI can
    show for review before anything is committed.
    """
    shepherds = eligible_shepherds(location)
    if not shepherds:
        return [], (
            "Nobody is set up to shepherd here yet. In Admin, tick Can shepherd "
            "others on at least one account first."
        )

    from accounts.gender import can_pair, choose, shepherd_gender
    by_id = {s.id: s for s in shepherds}
    load = current_load(shepherds)
    order = [s.id for s in shepherds]
    changes = []
    household_choice = {}  # household_id -> shepherd chosen during this run

    def add(kind, obj, name, chosen_id, reason, warn, correction=False, never=()):
        changes.append({
            "kind": kind, "id": obj.id, "name": name, "gender": obj.gender or "",
            "from_id": obj.assigned_to_id,
            "from_name": _shepherd_name(obj.assigned_to) if obj.assigned_to else None,
            "to_id": chosen_id,
            "to_name": _shepherd_name(by_id[chosen_id]) if chosen_id else None,
            "reason": reason, "warn": warn, "correction": correction,
            # Shepherds the reviewer must not pick: the person themselves,
            # and a shepherd being replaced for breaking a rule.
            "never": sorted(never),
        })
        if chosen_id:
            load[chosen_id] = load.get(chosen_id, 0) + 1
            if obj.assigned_to_id in load:
                load[obj.assigned_to_id] -= 1

    from django.db.models import Q
    from .shepherd_rules import is_self, problem, rule_breaks
    member_qs = Member.objects.select_related("assigned_to", "assigned_to__member", "household")
    if location:
        member_qs = member_qs.filter(location=location)
    if not reassign_everyone:
        broken = [m.id for m, _, _ in rule_breaks(member_qs)]
        member_qs = member_qs.filter(Q(assigned_to__isnull=True) | Q(id__in=broken))

    for m in member_qs:
        chosen_id, reason, warn = None, "", False
        # A person must never be their own shepherd, and a shepherd who
        # breaks a rule is never proposed again for the same person.
        me = {sid for sid in by_id if is_self(by_id[sid], m)}
        wrong = problem(m) if m.assigned_to_id else None
        if wrong:
            me.add(m.assigned_to_id)

        # Household first: keep families with the same shepherd, but only
        # where the gender matches (Kay). Checks people already assigned in
        # the database AND people given a shepherd earlier in this run.
        if m.household_id:
            ok = lambda sid: sid in by_id and sid not in me and shepherd_gender(by_id[sid]) and can_pair(m.gender, by_id[sid])
            hid = household_choice.get((m.household_id, m.gender))
            if not ok(hid):
                hid = next((sid for sid in (Member.objects.filter(household_id=m.household_id, assigned_to__isnull=False)
                                            .exclude(id=m.id).values_list("assigned_to_id", flat=True)) if ok(sid)), None)
            if hid:
                chosen_id, warn = hid, not m.gender
                reason = "Household, same gender" if m.gender else "Household. Gender not known. Check before you apply."

        if chosen_id is None:
            chosen_id, reason, warn = choose(m.gender, load, order, by_id, exclude=me)

        if wrong:
            # Say what is wrong rather than how the new shepherd was picked.
            reason = wrong[0] if chosen_id else f"{wrong[0]}. {reason}"
            warn = True
        if chosen_id is None:
            # Nobody suitable: listed so the reviewer sees why, never applied.
            add("member", m, m.full_name, None, reason, True, bool(wrong), me)
            continue
        if chosen_id != m.assigned_to_id:
            add("member", m, m.full_name, chosen_id, reason, warn, bool(wrong), me)
            if m.household_id and (m.household_id, m.gender) not in household_choice:
                household_choice[(m.household_id, m.gender)] = chosen_id

    if AppSetting.get_bool(SETTING_AUTO_ASSIGN_NEWCOMERS, default=True):
        newcomer_qs = Newcomer.objects.select_related("assigned_to").exclude(stage="not-interested")
        if location:
            newcomer_qs = newcomer_qs.filter(location=location)
        if not reassign_everyone:
            newcomer_qs = newcomer_qs.filter(assigned_to__isnull=True)

        for n in newcomer_qs:
            chosen_id, reason, warn = choose(n.gender, load, order, by_id)
            if chosen_id is None:
                add("newcomer", n, n.name, None, reason, True)
            elif chosen_id != n.assigned_to_id:
                add("newcomer", n, n.name, chosen_id, reason, warn)

    return changes, None


def apply_assignment_changes(changes, by=None):
    """
    Commit a reviewed set of changes, all or nothing. Returns how many of
    each kind were applied.

    One transaction, so a failure part way can never leave half a batch
    saved. The newcomers' open tasks move with them in the same step.
    """
    from django.db import transaction
    from newcomers.models import Newcomer as NewcomerModel

    member_ids = {c["id"]: c["to_id"] for c in changes if c["kind"] == "member" and c.get("to_id")}
    newcomer_ids = {c["id"]: c["to_id"] for c in changes if c["kind"] == "newcomer" and c.get("to_id")}

    from alerts.events import given
    before_m = dict(Member.objects.filter(id__in=member_ids).values_list("id", "assigned_to_id"))
    before_n = dict(NewcomerModel.objects.filter(id__in=newcomer_ids).values_list("id", "assigned_to_id"))
    names = {("member", c["id"]): c["name"] for c in changes} | {("newcomer", c["id"]): c["name"] for c in changes}
    newly = ([("member", i, names.get(("member", i), ""), sid) for i, sid in member_ids.items() if before_m.get(i) != sid]
             + [("newcomer", i, names.get(("newcomer", i), ""), sid) for i, sid in newcomer_ids.items() if before_n.get(i) != sid])

    with transaction.atomic():
        # Sent only once everything here is saved.
        given(newly, by=by)
        applied_members = 0
        for mid, sid in member_ids.items():
            applied_members += Member.objects.filter(id=mid).update(assigned_to_id=sid)

        applied_newcomers = 0
        for nid, sid in newcomer_ids.items():
            applied_newcomers += NewcomerModel.objects.filter(id=nid).update(assigned_to_id=sid)
            # Tasks follow their person. Assigning a shepherd and leaving
            # their open tasks unowned is how a task ends up with nobody.
            n = NewcomerModel.objects.filter(id=nid).first()
            if n:
                carry_tasks_to_shepherd(n)

    return applied_members, applied_newcomers


def assign_on_registration(newcomer):
    """
    Give a newcomer a shepherd the moment they register.

    Without this, a newcomer who ticks "would like a visit" gets a task
    with nobody's name on it. The task is visible but unowned, and auto
    assign never picks it up afterwards because it assigns people, not
    tasks.

    Respects the setting: when an administrator turns newcomers off in
    auto assign they are saying they want them assigned by hand, usually
    so whoever met the person keeps them. That is a decision, not an
    oversight, so this does nothing in that case.
    """
    from core.models import AppSetting

    if not AppSetting.get_bool(SETTING_AUTO_ASSIGN_NEWCOMERS, default=True):
        return None
    if newcomer.assigned_to_id:
        return newcomer.assigned_to

    shepherds = eligible_shepherds(location=newcomer.location)
    if not shepherds:
        return None

    from accounts.gender import choose
    by_id = {s.id: s for s in shepherds}
    order = [s.id for s in shepherds]
    chosen_id, _, _ = choose(newcomer.gender, current_load(shepherds), order, by_id)
    if chosen_id is None:
        return None

    newcomer.assigned_to_id = chosen_id
    newcomer.save(update_fields=["assigned_to"])
    from alerts.events import given
    given([("newcomer", newcomer.pk, newcomer.name, chosen_id)])
    return newcomer.assigned_to


def carry_tasks_to_shepherd(newcomer):
    """
    Point a newcomer's open unowned tasks at whoever now shepherds them.

    Assigning the person and leaving their tasks behind is how a task
    ends up belonging to nobody: visible in the list, owned by no one,
    and never picked up.
    """
    if not newcomer.assigned_to_id:
        return 0
    return newcomer.tasks.filter(done=False, assigned_to__isnull=True).update(
        assigned_to=newcomer.assigned_to)
