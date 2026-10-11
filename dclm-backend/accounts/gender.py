"""
Gender matching (Kay, 10 October 2026): men follow up men, and women
follow up women.

  1. A person whose gender is known only goes to a shepherd of the same
     gender, by auto-assign or by hand.
  2. A person whose gender is not known may go to anyone, with a warning,
     and keeps the "Gender not known" tag until someone sets it.
  3. A shepherd with no gender set is given nobody by auto-assign. By hand
     they can only take people whose gender is not known.

A shepherd's gender is set on their account in Admin. Accounts are often
not linked to a member record, so the member record is only a fallback.
"""
from accounts.names import display_name

WORD = {"Male": "a man", "Female": "a woman"}
GROUP = {"Male": "men", "Female": "women"}


def shepherd_gender(user):
    if user is None:
        return ""
    g = getattr(user, "gender", "") or ""
    if not g and getattr(user, "member_id", None) and user.member:
        g = user.member.gender or ""
    return g


def can_pair(person_gender, shepherd):
    """True when this shepherd may follow up someone of this gender."""
    return not person_gender or shepherd_gender(shepherd) == person_gender


def mismatch_message(person_gender, who="person"):
    return (f"This {who} is {WORD[person_gender]}, so choose one of the {GROUP[person_gender]}. "
            "If the right person is missing, set their gender in Admin.")


def without_gender(shepherds):
    """Shepherds auto-assign will skip, for the warning above the proposal."""
    return [s for s in shepherds if not shepherd_gender(s)]


def skipped_notice(shepherds):
    names = [display_name(s) for s in without_gender(shepherds)]
    if not names:
        return ""
    who = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
    return (f"{who} {'has' if len(names) == 1 else 'have'} no gender set, so auto-assign "
            "gives them nobody. Set it in Admin, Users.")


def choose(person_gender, load, order, by_id, exclude=()):
    """
    Pick the shepherd with the fewest people for someone of this gender.
    Returns (shepherd id or None, reason, warn).
    """
    pool = [sid for sid in order if sid not in exclude and shepherd_gender(by_id[sid])]
    if person_gender:
        pool = [sid for sid in pool if shepherd_gender(by_id[sid]) == person_gender]
        if not pool:
            return None, f"No shepherd who is {WORD[person_gender]} yet. Left unassigned.", True
        best = min(pool, key=lambda sid: (load.get(sid, 0), order.index(sid)))
        return best, "Same gender, fewest", False
    if not pool:
        return None, "Gender not known, and no shepherd has a gender set. Left unassigned.", True
    best = min(pool, key=lambda sid: (load.get(sid, 0), order.index(sid)))
    return best, "Gender not known. Fewest overall. Check before you apply.", True
