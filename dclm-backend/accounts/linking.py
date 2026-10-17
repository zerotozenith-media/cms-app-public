"""
Which member record a login account belongs to (Kay, 17 October 2026).

Without this link the app cannot tell that the account "Kwabena Afari"
and the member "Kwabena Afari" are one person, so Auto-assign could give
him himself to shepherd. Admin had no way to set the link, so on the live
system no account was linked. Accounts are now linked by name where that
is certain: exactly one member with the same full name, not already the
record of another account. Anything less certain is left for an
administrator to choose in Admin, Users, Member record.
"""


def _norm(*parts):
    return " ".join(" ".join(p or "" for p in parts).split()).lower()


def find_member(user, member_model, user_model=None):
    """The one member with this account's full name, or None."""
    name = _norm(user.first_name, user.last_name)
    if not name:
        return None
    taken = set()
    if user_model is not None:
        taken = set(user_model.objects.exclude(member=None).exclude(pk=user.pk)
                    .values_list("member_id", flat=True))
    found = [m for m in member_model.objects.all().only("id", "first_name", "surname", "location_id")
             if _norm(m.first_name, m.surname) == name and m.id not in taken]
    if len(found) > 1 and user.location_id:
        found = [m for m in found if m.location_id == user.location_id]
    return found[0] if len(found) == 1 else None
