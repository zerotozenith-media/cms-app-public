"""
What every follow-up task records so it can be accounted for (Kay, 26
October 2026): what kind of task it is, when its clock started, its exact
due time, how it ended, who closed it, and how many times in a row the
person had missed. Shared by member and newcomer tasks, so both follow the
same rules and appear in one list.
"""
from django.db import models


class TaskKind(models.TextChoices):
    ABSENCE = "absence", "Missed a service"
    FIRST_VISIT = "first-visit", "First visit"
    NEXT_STEP = "next-step", "Next step"
    COORDINATOR_VISIT = "coordinator-visit", "Follow-up Coordinator visit"
    FALLING = "attendance-falling", "Attendance falling"
    MANUAL = "manual", "Added by hand"


class TaskResult(models.TextChoices):
    REACHED = "reached", "Reached"
    KNOWN_REASON = "known-reason", "Known reason"
    MOVED_AWAY = "moved-away", "Moved away or left"
    WAS_PRESENT = "was-present", "Was present"
    CANCELLED = "cancelled", "Cancelled"


class Escalation(models.TextChoices):
    NEEDS_COORDINATOR = "needs-coordinator", "Needs the Follow-up Coordinator"
    ATTEMPTS = "attempts", "Could not reach after several attempts"
    NO_SHEPHERD = "no-shepherd", "No shepherd"
    LATE = "late", "Still open after the Review list time"


class AccountableTask(models.Model):
    kind = models.CharField(max_length=24, choices=TaskKind.choices, default=TaskKind.MANUAL)
    # Blank on tasks made before 26 October 2026.
    created_at = models.DateTimeField(null=True, blank=True)
    clock_start = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(
        null=True, blank=True,
        help_text="The exact due time. due_date stays as its date, for lists and older screens.")
    result = models.CharField(max_length=20, choices=TaskResult.choices, blank=True, default="")
    result_note = models.TextField(blank=True, default="")
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    # One visit closes every open absence task for the person; the others
    # point to the task the visit was recorded on.
    covered_by = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="covers")
    missed_in_row = models.PositiveSmallIntegerField(
        default=0, help_text="How many times in a row the person had missed this meeting.")
    # Set when the task goes to the Follow-up Coordinator (build 3).
    escalation = models.CharField(max_length=20, choices=Escalation.choices, blank=True, default="")
    escalated_at = models.DateTimeField(null=True, blank=True)
    # When a Follow-up Coordinator hands this one task to someone else,
    # the shepherd it came from.
    handed_from = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    # So each alert about this task goes once, however often the clock runs.
    reason_alerted_at = models.DateTimeField(null=True, blank=True)
    review_alerted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
