from django.db import models


class NewcomerSource(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class MilestoneType(models.Model):
    """Admin-configurable , Batch 0.3, Finding: was a fixed 4-value enum in the demo."""
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Newcomer(models.Model):
    class Stage(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        VISITING = "visiting", "Visiting"
        INTEGRATED = "integrated", "Integrated"
        NOT_INTERESTED = "not-interested", "Not Interested"

    class Gender(models.TextChoices):
        MALE = "Male", "Male"
        FEMALE = "Female", "Female"

    class AgeGroup(models.TextChoices):
        UNDER_20 = "under_20", "Under 20"
        OVER_20 = "20_and_above", "20 and above"

    name = models.CharField(max_length=150)
    source = models.ForeignKey("newcomers.NewcomerSource", on_delete=models.PROTECT, related_name="newcomers")
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.NEW)
    assigned_to = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="newcomers_assigned",
    )
    location = models.ForeignKey("core.Location", on_delete=models.PROTECT, related_name="newcomers")
    created_at = models.DateField(help_text="First-contact date, set once and never changed.")
    stage_since = models.DateField(help_text="Updates every time stage changes.")
    not_interested_note = models.TextField(blank=True, default="")

    # Fields added to match the real DCLM Bahrain intake slip (both the
    # paper form used for manual entry and the QR self-registration form
    # must capture the same fields, for consistency).
    address = models.CharField(max_length=300, blank=True, default="")
    city_governorate = models.CharField(max_length=150, blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")  # not unique , may share a household's phone
    email = models.EmailField(blank=True, default="")
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True, default="")
    age_group = models.CharField(max_length=15, choices=AgeGroup.choices, blank=True, default="")
    prayer_request = models.TextField(blank=True, default="")
    meeting_attended = models.ForeignKey(
        "attendance.MeetingType", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="newcomer_intakes",
    )
    is_first_timer = models.BooleanField(default=False)
    is_new_resident = models.BooleanField(default=False)  # independent of is_first_timer , can both be true
    wants_visit = models.BooleanField(default=False)
    wants_to_know_more = models.BooleanField(default=False)
    wants_salvation_info = models.BooleanField(default=False)
    invited_by_member = models.ForeignKey(
        "members.Member", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="newcomers_invited",
        help_text="Auto-matched by exact name at creation time if unambiguous; invited_by_name is the durable record either way.",
    )
    invited_by_name = models.CharField(max_length=150, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class NewcomerStatusHistory(models.Model):
    """
    New table (Batch 0.3, Finding 1): preserves a Not Interested -> Reactivated
    episode visibly on the newcomer's own profile, not only in the audit log.
    """
    newcomer = models.ForeignKey("newcomers.Newcomer", on_delete=models.CASCADE, related_name="status_history")
    stage = models.CharField(max_length=20, choices=Newcomer.Stage.choices)
    note = models.TextField(blank=True, default="")
    date = models.DateField()

    class Meta:
        ordering = ["-date"]
        verbose_name_plural = "Newcomer status history"

    def __str__(self):
        return f"{self.newcomer}: {self.stage} on {self.date}"


class NewcomerMilestone(models.Model):
    newcomer = models.ForeignKey("newcomers.Newcomer", on_delete=models.CASCADE, related_name="milestones")
    milestone_type = models.ForeignKey("newcomers.MilestoneType", on_delete=models.PROTECT, related_name="records")
    achieved_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ("newcomer", "milestone_type")

    def __str__(self):
        return f"{self.newcomer}: {self.milestone_type}"


class NewcomerTask(models.Model):
    class Method(models.TextChoices):
        HOME_VISIT = "Home visit", "Home visit"
        PHONE_CALL = "Phone call", "Phone call"
        TEXT_MESSAGE = "Text message", "Text message"
        AFTER_SERVICE = "Spoke after service", "Spoke after service"
        OTHER = "Other", "Other"

    newcomer = models.ForeignKey("newcomers.Newcomer", on_delete=models.CASCADE, related_name="tasks")
    text = models.CharField(max_length=300)
    due_date = models.DateField()
    done = models.BooleanField(default=False)
    assigned_to = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="newcomer_tasks_assigned",
        help_text="Batch 0.3, Finding 3: independent of the newcomer's primary leader; "
                   "defaults to it if left blank at the application layer.",
    )
    # A checked box with no record of what was discussed isn't useful to a
    # leader reviewing history later , confirmed real gap, fixed here and
    # on MemberFollowUpTask together, not just one of the two.
    contact_date = models.DateField(null=True, blank=True)
    contact_method = models.CharField(max_length=30, choices=Method.choices, blank=True, default="")
    # Four structured fields rather than one free-text note. A completed
    # task with no record of what happened is not useful to whoever reads
    # it months later, so completion captures the goal, the scripture
    # shared, the root cause found, and the next step agreed. All four
    # are required at the API layer (see the complete() action), not at
    # the model layer, so historical rows created before this change
    # remain valid.
    contact_goal = models.TextField(blank=True, default="")
    contact_scripture = models.CharField(max_length=300, blank=True, default="")
    contact_root_cause = models.TextField(blank=True, default="")
    contact_next_step = models.TextField(blank=True, default="")
    contact_notes = models.TextField(
        blank=True, default="",
        help_text="Legacy single-note field, kept so records created before "
                  "the four structured fields existed still display correctly.",
    )

    class Meta:
        ordering = ["due_date"]

    def __str__(self):
        return self.text


class FollowUpUrgencySetting(models.Model):
    """Admin-adjustable thresholds (Batch 0.3, Finding 4) , no longer hardcoded."""
    stage = models.CharField(max_length=20, choices=Newcomer.Stage.choices, unique=True)
    amber_days = models.PositiveIntegerField()
    red_days = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.stage}: amber {self.amber_days}d / red {self.red_days}d"


class PublicRegistrationAttempt(models.Model):
    """
    Security/rate-limiting log for the public QR self-registration
    endpoint , same design as accounts.LoginAttempt (Batch 1.4): a real
    unauthenticated write endpoint is a genuine attack surface, and this
    is the record an Administrator can review if abuse is suspected.
    """
    class Reason(models.TextChoices):
        SUCCESS = "success", "Success"
        HONEYPOT = "honeypot", "Honeypot field triggered"
        TOO_FAST = "too_fast", "Submitted faster than humanly possible"
        RATE_LIMITED = "rate_limited", "Too many submissions from this IP"
        INVALID_DATA = "invalid_data", "Failed normal field validation"

    ip_address = models.GenericIPAddressField()
    successful = models.BooleanField()
    reason = models.CharField(max_length=20, choices=Reason.choices)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        status = "OK" if self.successful else f"FAILED ({self.reason})"
        return f"{self.timestamp} , {self.ip_address} , {status}"
