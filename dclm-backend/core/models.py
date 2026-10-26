import datetime

from django.db import models


class Location(models.Model):
    """
    Per Batch 0.1/0.7: Bahrain is a protected core location and cannot
    be deleted. Every other location is fully Admin-manageable.
    id is a slug (not an auto integer) to match the approved schema and
    keep it human-readable in every other table that references it.
    """
    id = models.SlugField(primary_key=True, max_length=50)
    name = models.CharField(max_length=100)
    note = models.CharField(max_length=200, blank=True, default="")
    is_core = models.BooleanField(
        default=False,
        help_text="True only for Bahrain. Prevents deletion.",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.note})" if self.note else self.name

    def delete(self, *args, **kwargs):
        if self.is_core:
            raise models.ProtectedError(
                f"'{self.name}' is a core location and cannot be deleted.", [self]
            )
        return super().delete(*args, **kwargs)


class AppSetting(models.Model):
    """
    Small key/value store for church-wide switches an administrator can
    change from the UI. Deliberately not a settings.py constant: these
    are operational choices the church owns, not deployment config.
    """
    key = models.CharField(max_length=100, primary_key=True)
    value = models.CharField(max_length=255)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return f"{self.key}={self.value}"

    @classmethod
    def get_bool(cls, key, default=False):
        row = cls.objects.filter(key=key).first()
        if not row:
            return default
        return row.value.lower() in ("true", "1", "yes")

    @classmethod
    def set_bool(cls, key, value):
        cls.objects.update_or_create(key=key, defaults={"value": "true" if value else "false"})


class FollowUpRules(models.Model):
    """
    The follow-up rules Kay decided on 26 October 2026, kept as settings an
    administrator covering every location can change in Admin, Follow-up
    Rules, so no number needs a developer. There is only ever one row;
    FollowUpRules.get() returns it, made with the decided values the first
    time it is asked for.
    """
    STAGE_CHOICES = ["new", "contacted", "attending"]

    # Time limits. Every clock starts at clock_start on the service day,
    # or when the task is made if names were ticked after the absence
    # check had run.
    clock_start = models.TimeField(default=datetime.time(18, 0))
    due_hours = models.PositiveSmallIntegerField(default=24)
    reason_hours = models.PositiveSmallIntegerField(default=48)
    review_days = models.PositiveSmallIntegerField(default=3)
    decide_days = models.PositiveSmallIntegerField(default=5)
    max_new_date_days = models.PositiveSmallIntegerField(default=7)

    # Repeated absences, counted for the same meeting each time.
    alert_from_miss = models.PositiveSmallIntegerField(default=2)
    alert_repeat = models.CharField(
        max_length=20, default="every",
        choices=[("every", "every further miss"), ("every-second", "every 2nd miss")])
    visit_task_at_miss = models.PositiveSmallIntegerField(default=3)
    attempts_before_coordinator = models.PositiveSmallIntegerField(default=3)
    falling_percent = models.PositiveSmallIntegerField(default=50)
    falling_window = models.PositiveSmallIntegerField(default=8)

    # Shepherds and newcomers.
    shepherd_limit = models.PositiveSmallIntegerField(default=6)
    newcomer_stages = models.CharField(max_length=60, default="new,contacted,attending")

    # Reminders and alerts.
    check_hours_after_start = models.PositiveSmallIntegerField(default=3)
    remind_administrators = models.BooleanField(default=True)
    remind_location_coordinators = models.BooleanField(default=False)
    morning_alert_time = models.TimeField(default=datetime.time(7, 0))

    # Targets, shown on the Follow-up Review page and in the Overseer report.
    target_on_time = models.PositiveSmallIntegerField(default=90)
    target_first_contact_hours = models.PositiveSmallIntegerField(default=24)
    target_reached = models.PositiveSmallIntegerField(default=80)

    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        verbose_name = "follow-up rules"
        verbose_name_plural = "follow-up rules"

    def __str__(self):
        return "Follow-up rules"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def stages(self):
        return [s for s in (self.newcomer_stages or "").split(",") if s]


class FollowUpReview(models.Model):
    """
    One round of a late task on the Follow-up Coordinator's Review list
    (Kay, 26 October 2026): the shepherd's reason and new date, then the
    Follow-up Coordinator's choice. A task can have several rounds, for
    example when an accepted new date passes and it is late again. Every
    round is kept, so the record can be read later.
    """
    REASONS = [
        ("tried", "Tried but could not reach"),
        ("person-away", "Person travelling or sick"),
        ("i-was-away", "I was away or unwell"),
        ("too-many", "Too many people to follow up"),
        ("forgot", "Forgot"),
        ("other", "Other"),
    ]
    CHOICES = [
        ("accept", "Accept"),
        ("hand-on", "Hand to another shepherd"),
        ("take", "Take it myself"),
        ("ask", "Ask the shepherd"),
    ]

    member_task = models.ForeignKey("members.MemberFollowUpTask", on_delete=models.CASCADE, null=True, blank=True,
                                    related_name="reviews")
    newcomer_task = models.ForeignKey("newcomers.NewcomerTask", on_delete=models.CASCADE, null=True, blank=True,
                                      related_name="reviews")
    reason = models.CharField(max_length=20, choices=REASONS, blank=True, default="")
    reason_note = models.CharField(max_length=500, blank=True, default="")
    new_date = models.DateField(null=True, blank=True)
    given_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    given_at = models.DateTimeField(null=True, blank=True)
    choice = models.CharField(max_length=10, choices=CHOICES, blank=True, default="")
    choice_note = models.CharField(max_length=500, blank=True, default="")
    handed_to = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    decided_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    decided_at = models.DateTimeField(null=True, blank=True)
    # So the administrators are told once when a decision is late.
    admins_alerted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    @property
    def task(self):
        return self.member_task or self.newcomer_task
