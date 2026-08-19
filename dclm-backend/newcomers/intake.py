"""
Shared intake logic used by both the authenticated Newcomer creation
path (NewcomerViewSet) and the public QR self-registration endpoint ,
factored out so both paths are guaranteed to behave identically, not
just similarly, for the parts of the process (invited-by matching,
auto-task creation) common to both.
"""
from datetime import timedelta

from django.utils import timezone

from .models import NewcomerTask


def match_invited_by_member(invited_by_name):
    """
    Exact case-insensitive match on a Member's computed full name.
    full_name is a Python property, not a DB field, so this can't be a
    queryset filter , fetching all members and matching in Python is
    fine at this project's real scale (a single church's membership).
    Only links if unambiguous: two members sharing the exact name are
    left unlinked, text-only, rather than guessing.
    """
    invited_by_name = (invited_by_name or "").strip()
    if not invited_by_name:
        return None
    from members.models import Member
    candidates = [m for m in Member.objects.all() if m.full_name.lower() == invited_by_name.lower()]
    return candidates[0] if len(candidates) == 1 else None


def create_auto_tasks(newcomer):
    """
    Auto-created follow-up tasks from the intake slip's request
    checkboxes , real tasks a leader sees in their Follow-ups list, not
    an automated send. Nothing is emailed or messaged by the system
    itself; a human still does the actual visit/conversation.
    """
    task_specs = []
    if newcomer.wants_visit:
        task_specs.append(("Schedule a home visit", 5))
    if newcomer.wants_to_know_more:
        task_specs.append(("Share more about the church", 5))
    if newcomer.wants_salvation_info:
        task_specs.append(("Have a salvation conversation", 2))  # sooner , real pastoral urgency
    for text, days_out in task_specs:
        NewcomerTask.objects.create(
            newcomer=newcomer, text=text,
            due_date=timezone.localdate() + timedelta(days=days_out),
            assigned_to=newcomer.assigned_to,
        )
