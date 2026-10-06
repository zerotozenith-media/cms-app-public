"""
Follow-up journeys (F19, F20).

Three journeys share one engine: online contacts, newcomers and new
converts. Each has a plan of messages by day, drawn from a message bank
that leadership approves and administrators edit. Messages are sent by the
person following up, from their own WhatsApp, so the system records what
was sent rather than sending it.
"""
from django.conf import settings
from django.db import models

JOURNEYS = [
    ("online", "Online contacts"),
    ("newcomers", "Newcomers"),
    ("converts", "New converts"),
]
BANK_GROUPS = JOURNEYS + [("any", "Any journey")]


class MessageTemplate(models.Model):
    """One message in the bank. Verses are King James, quoted exactly."""
    journey = models.CharField(max_length=12, choices=BANK_GROUPS)
    theme = models.CharField(max_length=60)
    number = models.PositiveIntegerField(help_text="Its number within the theme, from 1.")
    verse = models.TextField(blank=True, default="")
    reference = models.CharField(max_length=60, blank=True, default="")
    body = models.TextField()
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["journey", "theme", "number"]
        constraints = [models.UniqueConstraint(fields=["journey", "theme", "number"], name="unique_message_number")]

    def __str__(self):
        return f"{self.get_journey_display()}, {self.theme} {self.number}"


class PlanStep(models.Model):
    """The Standard plan: which message on which day of a journey."""
    journey = models.CharField(max_length=12, choices=JOURNEYS)
    day = models.PositiveIntegerField()
    template = models.ForeignKey(MessageTemplate, on_delete=models.PROTECT, related_name="plan_steps")

    class Meta:
        ordering = ["journey", "day"]
        constraints = [models.UniqueConstraint(fields=["journey", "day"], name="unique_plan_day")]


class Enrolment(models.Model):
    """A person on a journey. Exactly one of newcomer, member or enquiry is set."""

    class Plan(models.TextChoices):
        STANDARD = "standard", "Standard"
        DAILY = "daily", "Daily"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        STOPPED = "stopped", "Stopped"
        ENDED = "ended", "Ended"
        MOVED = "moved", "Moved to another journey"

    journey = models.CharField(max_length=12, choices=JOURNEYS)
    newcomer = models.ForeignKey("newcomers.Newcomer", null=True, blank=True, on_delete=models.CASCADE, related_name="enrolments")
    member = models.ForeignKey("members.Member", null=True, blank=True, on_delete=models.CASCADE, related_name="enrolments")
    enquiry = models.ForeignKey("enquiries.Enquiry", null=True, blank=True, on_delete=models.CASCADE, related_name="enrolments")
    started = models.DateField()
    plan = models.CharField(max_length=10, choices=Plan.choices, default=Plan.STANDARD)
    shift = models.PositiveIntegerField(default=0, help_text="Days added when a personal reply took a planned day.")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    ended_on = models.DateField(null=True, blank=True)
    ended_reason = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-started", "-id"]
        constraints = [models.CheckConstraint(
            name="enrolment_one_person",
            check=(models.Q(newcomer__isnull=False, member__isnull=True, enquiry__isnull=True)
                       | models.Q(newcomer__isnull=True, member__isnull=False, enquiry__isnull=True)
                       | models.Q(newcomer__isnull=True, member__isnull=True, enquiry__isnull=False)))]

    @property
    def person(self):
        return self.newcomer or self.member or self.enquiry


class MessageLog(models.Model):
    """Each message sent, personal reply, own message or skipped day."""

    class Kind(models.TextChoices):
        PLANNED = "planned", "Planned message"
        OWN = "own", "Own message"
        REPLY = "reply", "Personal reply"
        SKIPPED = "skipped", "Skipped"

    enrolment = models.ForeignKey(Enrolment, on_delete=models.CASCADE, related_name="log")
    day = models.PositiveIntegerField()
    kind = models.CharField(max_length=10, choices=Kind.choices)
    template = models.ForeignKey(MessageTemplate, null=True, blank=True, on_delete=models.SET_NULL)
    theme = models.CharField(max_length=60, blank=True, default="")
    text = models.TextField(blank=True, default="", help_text="Exactly what was sent, with WhatsApp's marks.")
    sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    on_date = models.DateField()
    # Kay: a message chosen or written on any day, besides the plan. It never
    # takes the place of that day's planned message.
    extra = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-on_date", "-id"]


class SavedMessage(models.Model):
    """A sender's own drafts, visible only to them."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_messages")
    html = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class StepDone(models.Model):
    """A discipler's in-person step completed for a new convert."""
    enrolment = models.ForeignKey(Enrolment, on_delete=models.CASCADE, related_name="steps_done")
    step = models.PositiveIntegerField()
    done_on = models.DateField()
    by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["enrolment", "step"], name="unique_step_done")]


# The discipler's in-person steps for new converts (F20).
DISCIPLER_STEPS = [
    ("Within 48 hours", "Call or meet them, pray together, and give them a Bible if they need one."),
    ("Week 1", "Explain who they now are in Christ, and invite them to the Discipleship Class."),
    ("Week 2", "Invite them to the Baptism Class."),
    ("Week 4 to 6", "Water baptism, when ready."),
    ("Week 6 to 12", "Pray with them for the baptism of the Holy Ghost, and teach on sanctification."),
]
