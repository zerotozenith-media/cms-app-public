"""
One place that decides how a user's name is displayed.

A shepherd or staff member is always linked to a Member record, and that
record reliably carries a real name. The User account's first_name and
last_name are often left blank when accounts are created quickly, so
falling straight through to email showed "sarah@dclm-bh.org" on screens
where a person's name was expected. Preferring the linked member fixes
that everywhere at once rather than in each serializer separately.
"""


def display_name(user):
    if user is None:
        return None
    member = getattr(user, "member", None)
    if member is not None:
        full = (member.full_name or "").strip()
        if full:
            return full
    return user.get_full_name() or user.email
