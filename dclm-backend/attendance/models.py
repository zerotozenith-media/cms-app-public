from django.db import models
from django.utils import timezone


class MeetingType(models.Model):
    class Audience(models.TextChoices):
        EVERYONE = "everyone", "Everyone"
        WORKERS = "workers", "Workers"
        LEADERSHIP = "leadership", "Leadership"

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

    # Who is expected. Without this, switching absence follow-up on for a
    # workers meeting would create a task for every general member who was
    # never expected there, and workers would learn to ignore the list.
    audience = models.CharField(
        max_length=20, choices=Audience.choices, default=Audience.EVERYONE,
        help_text="Who is expected at this meeting, and so who is followed up when absent.",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Fellowship(models.Model):
    """
    A house caring fellowship.

    Kept as a configurable list rather than a fixed number, because the
    number changes: the church runs two today, one for the women and one
    for the men, and adding a third should be an administrator's job.

    The leader is NOT held here. It is recorded per session, since it
    changes week to week, and fixing it here would silently rewrite
    history every time somebody stood in.
    """
    name = models.CharField(max_length=100, unique=True)
    area = models.CharField(max_length=100, blank=True, default="")
    is_active = models.BooleanField(default=True)

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

    # Online attendance, counted separately rather than folded into the
    # figures above. Any meeting can be hybrid, and a report showing only
    # the people in the room would understate the month.
    online_men = models.PositiveIntegerField(default=0)
    online_women = models.PositiveIntegerField(default=0)
    online_youth_boys = models.PositiveIntegerField(default=0)
    online_youth_girls = models.PositiveIntegerField(default=0)
    online_children_boys = models.PositiveIntegerField(default=0)
    online_children_girls = models.PositiveIntegerField(default=0)

    # A headcount of who was new, which answers a different question from
    # the newcomer records: how many were new tonight, rather than who.
    new_comers = models.PositiveIntegerField(default=0)
    new_converts = models.PositiveIntegerField(
        default=0, help_text="Gave their life to Christ at this meeting.")

    # Only used when the meeting is a house fellowship.
    fellowship = models.ForeignKey(
        "attendance.Fellowship", on_delete=models.PROTECT,
        related_name="sessions", null=True, blank=True)
    led_by = models.ForeignKey(
        "members.Member", on_delete=models.SET_NULL,
        related_name="led_sessions", null=True, blank=True)
    lesson = models.CharField(
        max_length=60, blank=True, default="",
        help_text='Which study was covered, for example "BTB 15".')

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.meeting_type} , {self.date}"

    @property
    def online_total(self):
        return (self.online_men + self.online_women
                + self.online_youth_boys + self.online_youth_girls
                + self.online_children_boys + self.online_children_girls)

    @property
    def in_person_total(self):
        return (self.men + self.women + self.youth_boys + self.youth_girls
                + self.children_boys + self.children_girls)

    @property
    def total(self):
        """Everyone present, in the room and online."""
        return self.in_person_total + self.online_total


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
    # Exactly one of member or newcomer is set. A newcomer who is
    # attending is a real person in the room, and the membership rule
    # cannot work without knowing when they came.
    member = models.ForeignKey(
        "members.Member", on_delete=models.CASCADE, related_name="attendance_records",
        null=True, blank=True,
    )
    newcomer = models.ForeignKey(
        "newcomers.Newcomer", on_delete=models.CASCADE, related_name="attendances",
        null=True, blank=True,
    )
    mode = models.CharField(
        max_length=20, choices=Mode.choices, default=Mode.IN_PERSON,
        help_text="Per-attendee, not per-session , a single hybrid service can "
                   "correctly have some members in-person and others online.",
    )
    checked_in_at = models.DateTimeField(default=timezone.now)

    class Meta:
        # Two separate pairs rather than one across three columns: a row
        # holds a member or a newcomer, never both, and NULL would defeat
        # a combined constraint.
        unique_together = [("session", "member"), ("session", "newcomer")]

    @property
    def person(self):
        return self.member or self.newcomer

    def __str__(self):
        return f"{self.person} @ {self.session}"
