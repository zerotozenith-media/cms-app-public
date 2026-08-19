import datetime
from django.core.exceptions import ValidationError
from django.db import models


def validate_not_future(value):
    if value and value > datetime.date.today():
        raise ValidationError("Date of birth cannot be in the future.")


def validate_not_implausibly_old(value):
    if value and value < datetime.date.today().replace(year=datetime.date.today().year - 110):
        raise ValidationError("Date of birth is implausibly far in the past (over 110 years).")


class Household(models.Model):
    name = models.CharField(max_length=150)
    address = models.CharField(max_length=300, blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Member(models.Model):
    class Category(models.TextChoices):
        GENERAL = "General Member", "General Member"
        IN_TRAINING = "Worker in Training", "Worker in Training"
        WORKER = "Worker", "Worker"

    class Gender(models.TextChoices):
        MALE = "Male", "Male"
        FEMALE = "Female", "Female"

    surname = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    other_names = models.CharField(max_length=150, blank=True, default="")
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True, default="")
    date_of_birth = models.DateField(
        null=True, blank=True,
        validators=[validate_not_future, validate_not_implausibly_old],
    )
    # Full international format support (not restricted to Bahrain) per Batch 0.1.
    # Real format validation (not just uniqueness) is enforced at the Phase 2
    # serializer layer, where a proper phonenumbers-based validator is used.
    phone = models.CharField(max_length=30, unique=True, null=True, blank=True)
    email = models.EmailField(blank=True, default="")  # intentionally not unique , Batch 0.1
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.GENERAL)
    location = models.ForeignKey("core.Location", on_delete=models.PROTECT, related_name="members")
    joined_date = models.DateField()
    household = models.ForeignKey(
        "members.Household", on_delete=models.SET_NULL, null=True, blank=True, related_name="members"
    )
    assigned_to = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="members_shepherded",
        help_text="The worker responsible for this member's pastoral follow-up "
                   "if they miss a tracked service. Same pattern as Newcomer.assigned_to.",
    )

    class Meta:
        ordering = ["surname", "first_name"]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.surname}".strip()


class MemberCategoryHistory(models.Model):
    member = models.ForeignKey("members.Member", on_delete=models.CASCADE, related_name="category_history")
    from_category = models.CharField(max_length=30, choices=Member.Category.choices)
    to_category = models.CharField(max_length=30, choices=Member.Category.choices)
    changed_date = models.DateField()

    class Meta:
        ordering = ["-changed_date"]
        verbose_name_plural = "Member category history"

    def __str__(self):
        return f"{self.member}: {self.from_category} -> {self.to_category}"


class MemberFollowUpTask(models.Model):
    """
    Real member-absence follow-up, confirmed design: a member who isn't
    checked into a meeting flagged as counts_for_absence gets exactly one
    open task at a time (a second miss while one is already open does not
    stack a duplicate , enforced at creation time in the check command,
    not here). Mirrors NewcomerTask's shape deliberately, including the
    same visitation-outcome logging fields.
    """
    class Method(models.TextChoices):
        HOME_VISIT = "Home visit", "Home visit"
        PHONE_CALL = "Phone call", "Phone call"
        TEXT_MESSAGE = "Text message", "Text message"
        AFTER_SERVICE = "Spoke after service", "Spoke after service"
        OTHER = "Other", "Other"

    member = models.ForeignKey("members.Member", on_delete=models.CASCADE, related_name="followup_tasks")
    text = models.CharField(max_length=300)
    due_date = models.DateField()
    done = models.BooleanField(default=False)
    assigned_to = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="member_followups_assigned",
        help_text="Copied from the member's assigned shepherd at creation time , "
                   "independent afterward, same pattern as NewcomerTask.assigned_to.",
    )
    # What actually triggered this , a real link where possible, plus a
    # durable text snapshot so the task stays meaningful even if the
    # underlying session is later deleted (same snapshot principle as
    # AuditLog.entity_name).
    missed_session = models.ForeignKey(
        "attendance.AttendanceSession", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="generated_followups",
    )
    missed_meeting_name = models.CharField(max_length=150)
    missed_date = models.DateField()
    # Visitation-outcome logging , the same real gap fixed on NewcomerTask,
    # fixed here too rather than only on one of the two.
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
        return f"{self.member}: {self.text}"
