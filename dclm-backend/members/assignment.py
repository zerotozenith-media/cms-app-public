"""
Shepherd assignment rules, kept separate from the views so the logic can
be tested on its own and reused by any caller.

Confirmed design:
  1. Only members in the Worker category can be shepherds.
  2. Household first, so families are not split across different workers.
  3. Then load balancing, by how many people a worker already carries.
     Deliberately counts people shepherded rather than open tasks, since
     open task counts fluctuate week to week and would cause churn.
  4. Only fills people with no shepherd unless reassign_everyone is set,
     so pairings someone chose on purpose are not silently overwritten.
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
    A shepherd is a User account, not a bare Member record, since tasks
    are assigned to whoever logs in. "Worker only" is therefore checked
    through the member record that user is linked to: an active account
    whose linked member sits in the Worker category.
    """
    qs = User.objects.filter(
        is_active=True,
        member__isnull=False,
        member__category=Member.Category.WORKER,
    ).select_related("member")
    if location:
        qs = qs.filter(member__location=location)
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
            "No Workers available to act as shepherds. Set at least one member "
            "to the Worker category first."
        )

    by_id = {s.id: s for s in shepherds}
    load = current_load(shepherds)
    changes = []
    household_choice = {}  # household_id -> shepherd chosen during this run

    member_qs = Member.objects.select_related("assigned_to", "household")
    if location:
        member_qs = member_qs.filter(location=location)
    if not reassign_everyone:
        member_qs = member_qs.filter(assigned_to__isnull=True)

    for m in member_qs:
        chosen_id = None
        reason = "Balanced load"

        # Household first: keep families with the same shepherd. Checks
        # both people already assigned in the database AND people given a
        # shepherd earlier in this same preview run, otherwise a household
        # where nobody is assigned yet would never pair up: the first
        # member would fall through to load balancing and the second
        # would find no saved housemate to match.
        if m.household_id:
            chosen_id = household_choice.get(m.household_id)
            if chosen_id:
                reason = "Household"
            else:
                housemate = (
                    Member.objects.filter(household_id=m.household_id, assigned_to__isnull=False)
                    .exclude(id=m.id)
                    .first()
                )
                if housemate and housemate.assigned_to_id in by_id:
                    chosen_id = housemate.assigned_to_id
                    reason = "Household"

        if chosen_id is None:
            # A person must never be their own shepherd. Exclude any
            # shepherd account linked to this same member record before
            # picking the least loaded. Found when a worker with no
            # shepherd was proposed as her own.
            candidates = {sid: n for sid, n in load.items() if by_id[sid].member_id != m.id}
            chosen_id = _least_loaded(candidates)
        elif by_id.get(chosen_id) and by_id[chosen_id].member_id == m.id:
            candidates = {sid: n for sid, n in load.items() if by_id[sid].member_id != m.id}
            chosen_id = _least_loaded(candidates)
            reason = "Balanced load"

        if chosen_id and chosen_id != m.assigned_to_id:
            changes.append({
                "kind": "member",
                "id": m.id,
                "name": m.full_name,
                "from_name": _shepherd_name(m.assigned_to) if m.assigned_to else None,
                "to_id": chosen_id,
                "to_name": _shepherd_name(by_id[chosen_id]),
                "reason": reason,
            })
            load[chosen_id] = load.get(chosen_id, 0) + 1
            if m.household_id and m.household_id not in household_choice:
                household_choice[m.household_id] = chosen_id

    if AppSetting.get_bool(SETTING_AUTO_ASSIGN_NEWCOMERS, default=True):
        newcomer_qs = Newcomer.objects.select_related("assigned_to").exclude(stage="not-interested")
        if location:
            newcomer_qs = newcomer_qs.filter(location=location)
        if not reassign_everyone:
            newcomer_qs = newcomer_qs.filter(assigned_to__isnull=True)

        for n in newcomer_qs:
            chosen_id = _least_loaded(load)
            if chosen_id and chosen_id != n.assigned_to_id:
                changes.append({
                    "kind": "newcomer",
                    "id": n.id,
                    "name": n.name,
                    "from_name": _shepherd_name(n.assigned_to) if n.assigned_to else None,
                    "to_id": chosen_id,
                    "to_name": _shepherd_name(by_id[chosen_id]),
                    "reason": "Balanced load",
                })
                load[chosen_id] = load.get(chosen_id, 0) + 1

    return changes, None


def apply_assignment_changes(changes):
    """Commits a previously previewed set of changes. Returns how many
    of each kind were applied."""
    member_ids = {c["id"]: c["to_id"] for c in changes if c["kind"] == "member"}
    newcomer_ids = {c["id"]: c["to_id"] for c in changes if c["kind"] == "newcomer"}

    applied_members = 0
    for mid, sid in member_ids.items():
        applied_members += Member.objects.filter(id=mid).update(assigned_to_id=sid)

    applied_newcomers = 0
    for nid, sid in newcomer_ids.items():
        applied_newcomers += Newcomer.objects.filter(id=nid).update(assigned_to_id=sid)

    return applied_members, applied_newcomers
