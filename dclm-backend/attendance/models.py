from django.db import models
from django.utils import timezone


class MeetingType(models.Model):
    class Frequency(models.TextChoices):
        WEEKLY = "weekly", "Weekly"
        OCCASIONAL = "occasional", "Occasional"

    class DetailLevel(models.TextChoices):
        DETAILED = "detailed", "Detailed (Men/Women/Youth/Children)"
        SIMPLE = "simple", "Simple (Men/Women only)"

    id = models.SlugField(primary_key=True, max_length=50)
    name = models.CharField(max_length=150)
    day = models.CharField(max_length=20, blank=True, default="")
    start_time = models.TimeField(
        null=True, blank=True,
        help_text="Used only for absence follow-up timing (counts_for_absence) , "
                   "how the system knows a service has actually started and enough "
                   "time has passed to treat an unchecked member as absent, not just "
                   "not-arrived-yet. Optional: a meeting with counts_for_absence on "
                   "but no start_time is simply never auto-checked until one is set.",
    )
    frequency = models.CharField(max_length=20, choices=Frequency.choices)
    detail_level = models.CharField(max_length=20, choices=DetailLevel.choices)
    monthly_target = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Applies regardless of frequency , Batch 0.2 decision.",
    )
    counts_for_absence = models.BooleanField(
        default=False,
        help_text="If true, a member not checked into this meeting gets a real "
                   "follow-up task created for their shepherd. Admin-configurable, "
                   "not every meeting carries equal attendance expectation , "
                   "confirmed design decision, defaults off except where explicitly enabled.",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class AttendanceSession(models.Model):
    class Mode(models.TextChoices):
        IN_PERSON = "in-person", "In person"
        ONLINE = "online", "Online"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        FILLED = "filled", "Filled"

    meeting_type = models.ForeignKey("attendance.MeetingType", on_delete=models.PROTECT, related_name="sessions")
    date = models.DateField()
    location = models.ForeignKey("core.Location", on_delete=models.PROTECT, related_name="attendance_sessions")
    mode = models.CharField(max_length=10, choices=Mode.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    track_named = models.BooleanField(default=False)

    # Headcount is always the source of truth (Batch 0.2). One column per
    # category; a "simple" meeting only ever populates men/women.
    men = models.PositiveIntegerField(default=0)
    women = models.PositiveIntegerField(default=0)
    youth_boys = models.PositiveIntegerField(default=0)
    youth_girls = models.PositiveIntegerField(default=0)
    children_boys = models.PositiveIntegerField(default=0)
    children_girls = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.meeting_type} , {self.date}"

    @property
    def total(self):
        return (
            self.men + self.women + self.youth_boys
            + self.youth_girls + self.children_boys + self.children_girls
        )


class AttendanceSessionMember(models.Model):
    """
    Named attendance , no location restriction (Batch 0.2 decision):
    any member can be checked into any session.
    """
    class Mode(models.TextChoices):
        IN_PERSON = "in-person", "In person"
        ONLINE = "online", "Online"

    session = models.ForeignKey(
        "attendance.AttendanceSession", on_delete=models.CASCADE, related_name="attendees"
    )
    member = models.ForeignKey(
        "members.Member", on_delete=models.CASCADE, related_name="attendance_records"
    )
    mode = models.CharField(
        max_length=20, choices=Mode.choices, default=Mode.IN_PERSON,
        help_text="Per-attendee, not per-session , a single hybrid service can "
                   "correctly have some members in-person and others online.",
    )
    checked_in_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("session", "member")

    def __str__(self):
        return f"{self.member} @ {self.session}"
