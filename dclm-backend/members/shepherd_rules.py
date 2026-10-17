"""
The two rules every member's shepherd must keep (Kay, 17 October 2026):

  1. Men shepherd men, and women shepherd women.
  2. Nobody shepherds themselves.

Shepherds given before the gender rule existed, or while a gender was
blank, were kept as they were, and nothing ever looked at them again. On
the live system this left a woman with a man as shepherd, a man with a
woman, and a man shepherding himself. This module finds those, so the
Members page can flag them and Auto-assign can propose a correct shepherd.

"Themselves" needs to know which member record a login account belongs
to. That link is the account's Member record in Admin. Where an account
has no link, the same full name counts as the same person, so an unlinked
account still never gets itself.
"""
from accounts.gender import shepherd_gender


def _norm(*parts):
    return " ".join(" ".join(p or "" for p in parts).split()).lower()


def same_name(user, member):
    a = _norm(user.first_name, user.last_name)
    return bool(a) and a == _norm(member.first_name, member.surname)


def is_self(user, member):
    """True when this account is this member."""
    if user is None or member is None:
        return False
    if user.member_id:
        return user.member_id == member.id
    return same_name(user, member)


def _self_words(gender):
    return {"Male": ("He shepherds himself", "Shepherds himself"),
            "Female": ("She shepherds herself", "Shepherds herself")}.get(
        gender, ("They shepherd themselves", "Shepherds themselves"))


def problem(member, user=None):
    """
    What is wrong with this member's shepherd, or None.
    Returns (reason, tag): the reason reads in Auto-assign ("Her shepherd
    is a man"), the tag under the shepherd's name in the list ("A man
    shepherds her").
    """
    user = user if user is not None else member.assigned_to
    if user is None:
        return None
    if is_self(user, member):
        return _self_words(member.gender)
    sg = shepherd_gender(user)
    if member.gender and sg and member.gender != sg:
        if member.gender == "Female":
            return "Her shepherd is a man", "A man shepherds her"
        return "His shepherd is a woman", "A woman shepherds him"
    return None


def rule_breaks(qs):
    """[(member, reason, tag)] for every member in qs whose shepherd breaks a rule."""
    out = []
    for m in qs.filter(assigned_to__isnull=False).select_related("assigned_to", "assigned_to__member"):
        p = problem(m)
        if p:
            out.append((m, p[0], p[1]))
    return out
