"""
Who may do what with follow-up tasks beyond their role's module rights,
and who a task or an alert goes to (Kay, 26 October 2026).

A Follow-up Coordinator is an account with the Follow-up Coordinator tick,
for its chosen location or All locations, or an account whose role has
Follow-up review edit, for its own location. Tasks and alerts go to the
Follow-up Coordinator for the person's location first, then one covering
All locations, then the administrators.
"""
from accounts.permissions import user_has


def is_administrator(user):
    return bool(user and user.is_authenticated and (user.is_superuser or user_has(user, "admin", "can_edit")))


def _covers(scope_id, location_id):
    """Blank scope covers every location."""
    return scope_id is None or location_id is None or scope_id == location_id


def coordinates(user, location_id=None):
    """Whether this account is a Follow-up Coordinator for a location
    (for any location when location_id is None)."""
    if not (user and user.is_authenticated and user.is_active):
        return False
    if user.is_followup_coordinator and _covers(user.coordinates_location_id, location_id):
        return True
    return user_has(user, "followup-review", "can_edit") and _covers(user.location_id, location_id)


def coverage(user):
    """The location a coordinator's Review list covers: an id, or None for
    every location. Administrators cover their own account's location."""
    if user.is_followup_coordinator:
        return user.coordinates_location_id
    return user.location_id


def can_review(user, location_id=None):
    return coordinates(user, location_id) or is_administrator(user)


def can_cancel(user, location_id=None):
    """Cancelling a task made in error: only a Follow-up Coordinator or an
    administrator, because a cancelled task never reaches the shepherd's
    record."""
    return can_review(user, location_id)


def can_manage_task(user, location_id=None):
    """Changing a task's due time, or marking someone away for another
    shepherd's person: the same people."""
    return can_review(user, location_id)


def coordinators_for(location_id):
    """The Follow-up Coordinators for a location, nearest first: those for
    that location, else those for All locations, else the administrators
    covering every location."""
    from accounts.models import User
    active = User.objects.filter(is_active=True).select_related("role")
    here, everywhere = [], []
    for u in active:
        if u.is_followup_coordinator:
            if u.coordinates_location_id == location_id:
                here.append(u)
            elif u.coordinates_location_id is None:
                everywhere.append(u)
        elif user_has(u, "followup-review", "can_edit") and not is_administrator(u):
            if u.location_id == location_id:
                here.append(u)
            elif u.location_id is None:
                everywhere.append(u)
    return here or everywhere or administrators()


def administrators():
    from accounts.models import User
    return [u for u in User.objects.filter(is_active=True, location__isnull=True).select_related("role")
            if is_administrator(u)]
